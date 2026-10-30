#!/usr/bin/env python3
import base64
import hashlib
import mimetypes
import re
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

SERVICE = "com.codex.ag-agent-chat"
ACCOUNT = "OPENAI_API_KEY"


def workflow_cache_dir():
    base = os.environ.get("alfred_workflow_cache")
    path = Path(base) if base else Path.home() / "Library" / "Caches" / "com.codex.ag-agent-chat"
    path.mkdir(parents=True, exist_ok=True)
    return path


def current_session_path():
    return workflow_cache_dir() / "current_session"


def make_session_id(prompt):
    requested = os.environ.get("ag_session", "").strip()
    if requested:
        return requested
    digest = hashlib.sha256(f"{time.time()}:{prompt}".encode("utf-8")).hexdigest()[:16]
    return time.strftime("%Y%m%d%H%M%S") + "-" + digest


def safe_session(session):
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in session)[:100]


def paths_for(session):
    base = workflow_cache_dir() / safe_session(session)
    return {
        "txt": base.with_suffix(".txt"),
        "done": base.with_suffix(".done"),
        "stop": base.with_suffix(".stop"),
        "history": base.with_suffix(".jsonl"),
        "request": base.with_suffix(".request"),
    }


def get_session(prompt, mode):
    cur = current_session_path()
    if mode == "continue":
        if cur.exists():
            return cur.read_text(encoding="utf-8").strip()
        session = make_session_id(prompt)
        cur.write_text(session, encoding="utf-8")
        return session
    session = make_session_id(prompt)
    cur.write_text(session, encoding="utf-8")
    return session


def read_keychain_key():
    result = subprocess.run(["/usr/bin/security", "find-generic-password", "-s", SERVICE, "-a", ACCOUNT, "-w"], capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def textview(response, footer, rerun=None):
    payload = {"response": response, "footer": footer, "behaviour": {"response": "replace", "scroll": "end", "inputfield": "clear"}}
    if rerun is not None:
        payload["rerun"] = rerun
    print(json.dumps(payload, ensure_ascii=False))


def read_history(path):
    messages = []
    if not path.exists():
        return messages
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("role") in {"user", "assistant"} and item.get("content"):
            messages.append({"role": item["role"], "content": item["content"]})
    return messages[-12:]


def append_history(path, role, content):
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"role": role, "content": content}, ensure_ascii=False) + "\n")


def parse_image_prompt(prompt):
    image_paths = []
    text_parts = []
    index = 0
    marker = 'image:'
    lower_prompt = prompt.lower()

    while True:
        start = lower_prompt.find(marker, index)
        if start == -1:
            text_parts.append(prompt[index:])
            break
        text_parts.append(prompt[index:start])
        cursor = start + len(marker)
        while cursor < len(prompt) and prompt[cursor].isspace():
            cursor += 1
        if cursor >= len(prompt):
            index = cursor
            break

        quote = prompt[cursor] if prompt[cursor] in {'"', "'"} else ''
        if quote:
            cursor += 1
            path_start = cursor
            escaped = False
            chars = []
            while cursor < len(prompt):
                char = prompt[cursor]
                if escaped:
                    chars.append(char)
                    escaped = False
                elif char == '\\':
                    escaped = True
                elif char == quote:
                    break
                else:
                    chars.append(char)
                cursor += 1
            image_paths.append(''.join(chars).strip())
            index = cursor + 1 if cursor < len(prompt) else cursor
        else:
            chars = []
            escaped = False
            while cursor < len(prompt):
                char = prompt[cursor]
                if escaped:
                    chars.append(char)
                    escaped = False
                elif char == '\\':
                    escaped = True
                elif char.isspace():
                    break
                else:
                    chars.append(char)
                cursor += 1
            raw = ''.join(chars).strip()
            if raw:
                image_paths.append(raw)
            index = cursor

    text = re.sub(r'\s+', ' ', ''.join(text_parts)).strip()
    image_paths = [item for item in image_paths if item]
    return text, image_paths


def save_clipboard_image():
    out_path = workflow_cache_dir() / f"clipboard-{int(time.time() * 1000)}.png"
    script = """
ObjC.import('AppKit')
ObjC.import('Foundation')
const out = $.NSProcessInfo.processInfo.environment.objectForKey('AG_CLIP_OUT').js
const pb = $.NSPasteboard.generalPasteboard
const png = pb.dataForType('public.png') || pb.dataForType('Apple PNG pasteboard type')
if (png) {
  png.writeToFileAtomically(out, true)
  console.log(out)
} else {
  const tiff = pb.dataForType('public.tiff') || pb.dataForType('NeXT TIFF v4.0 pasteboard type')
  if (!tiff) throw new Error('clipboard has no image data')
  const bitmap = $.NSBitmapImageRep.alloc.initWithData(tiff)
  if (!bitmap) throw new Error('failed to decode clipboard image')
  const props = $.NSDictionary.dictionary
  const pngData = bitmap.representationUsingTypeProperties($.NSBitmapImageFileTypePNG, props)
  pngData.writeToFileAtomically(out, true)
  console.log(out)
}
"""
    env = os.environ.copy()
    env["AG_CLIP_OUT"] = str(out_path)
    result = subprocess.run(
        ["/usr/bin/osascript", "-l", "JavaScript", "-e", script],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("剪贴板里没有可读取的图片。请先复制图片或截图到剪贴板。")
    return str(out_path)


def resolve_image_path(path_text):
    token = path_text.strip().lower()
    if token in {"clip", "clipboard", "pasteboard"}:
        return save_clipboard_image()
    return path_text


def image_to_content_part(path_text):
    path_text = resolve_image_path(path_text)
    expanded = Path(path_text).expanduser()
    if not expanded.exists() or not expanded.is_file():
        raise FileNotFoundError(f"图片不存在：{path_text}")
    mime_type, _ = mimetypes.guess_type(str(expanded))
    if not mime_type or not mime_type.startswith('image/'):
        suffix = expanded.suffix.lower()
        if suffix in {'.jpg', '.jpeg'}:
            mime_type = 'image/jpeg'
        elif suffix == '.png':
            mime_type = 'image/png'
        elif suffix == '.gif':
            mime_type = 'image/gif'
        elif suffix == '.webp':
            mime_type = 'image/webp'
        else:
            raise ValueError(f"不是支持的图片格式：{path_text}")
    image_bytes = expanded.read_bytes()
    if expanded.parent == workflow_cache_dir() and expanded.name.startswith("clipboard-"):
        try:
            expanded.unlink()
        except OSError:
            pass
    encoded = base64.b64encode(image_bytes).decode('ascii')
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
    }


def build_user_message(prompt):
    text, image_paths = parse_image_prompt(prompt)
    if not image_paths:
        return {"role": "user", "content": prompt}, prompt, []
    content = [{"type": "text", "text": text or "请分析这些图片。"}]
    for image_path in image_paths:
        content.append(image_to_content_part(image_path))
    history_text = (text or "请分析这些图片。") + "\n\n" + "\n".join(f"[image: {item}]" for item in image_paths)
    return {"role": "user", "content": content}, history_text, image_paths


def start_worker(prompt, mode, session, paths):
    if mode == "continue":
        paths["stop"].write_text("1", encoding="utf-8")
        time.sleep(0.15)
    for key in ("txt", "done", "stop"):
        try:
            paths[key].unlink()
        except FileNotFoundError:
            pass
    paths["txt"].write_text("", encoding="utf-8")
    active_request = os.environ.get("ag_request", "")
    if prompt and mode == "continue":
        active_request = "inline-" + hashlib.sha256(f"{session}:{prompt}".encode("utf-8")).hexdigest()[:16]
    paths["request"].write_text(active_request, encoding="utf-8")
    env = os.environ.copy()
    env.update({
        "AG_STREAM_WORKER": "1",
        "AG_STREAM_PROMPT": prompt,
        "AG_STREAM_SESSION": session,
        "AG_STREAM_TXT": str(paths["txt"]),
        "AG_STREAM_DONE": str(paths["done"]),
        "AG_STREAM_STOP": str(paths["stop"]),
        "AG_STREAM_HISTORY": str(paths["history"]),
    })
    subprocess.Popen(["/usr/bin/python3", __file__], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def stream_worker():
    prompt = os.environ["AG_STREAM_PROMPT"]
    txt_path = Path(os.environ["AG_STREAM_TXT"])
    done_path = Path(os.environ["AG_STREAM_DONE"])
    stop_path = Path(os.environ["AG_STREAM_STOP"])
    history_path = Path(os.environ["AG_STREAM_HISTORY"])
    txt_path.write_text("", encoding="utf-8")

    base_url = os.environ.get("AG_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
    model = os.environ.get("AG_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    system_prompt = os.environ.get("AG_SYSTEM_PROMPT", "你是一个高效、准确的桌面助手。优先用中文简洁回答；必要时给出步骤、命令或代码。")
    api_key = os.environ.get("OPENAI_API_KEY", "").strip() or read_keychain_key()
    local_proxy = base_url.startswith("http://127.0.0.1") or base_url.startswith("http://localhost")
    if not api_key and not local_proxy:
        txt_path.write_text("❌ Agent 调用失败：还没有设置 API Key。\n\n请在 Alfred 输入：agkey sk-你的-key", encoding="utf-8")
        done_path.write_text("1", encoding="utf-8")
        return

    history = read_history(history_path)
    try:
        user_message, history_prompt, image_paths = build_user_message(prompt)
    except Exception as error:
        txt_path.write_text(f'❌ 图片解析失败：{error}\n\n用法示例：请分析 image:"/path/with spaces/a.png"', encoding="utf-8")
        done_path.write_text("1", encoding="utf-8")
        return
    if image_paths:
        txt_path.write_text(f"🖼️ 已识别 {len(image_paths)} 张图片，正在发送给 Agent…", encoding="utf-8")
    messages = [{"role": "system", "content": system_prompt}] + history + [user_message]
    payload = {"model": model, "messages": messages, "stream": True}
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(f"{base_url}/chat/completions", data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")

    answer_parts = []
    interrupted = False
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            for raw_line in response:
                if stop_path.exists():
                    interrupted = True
                    break
                line = raw_line.decode("utf-8", "replace").strip()
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                for choice in event.get("choices", []):
                    delta = choice.get("delta") or {}
                    content = delta.get("content") or ""
                    if content:
                        answer_parts.append(content)
                        txt_path.write_text("".join(answer_parts), encoding="utf-8")
        answer = "".join(answer_parts)
        if answer:
            append_history(history_path, "user", history_prompt)
            append_history(history_path, "assistant", answer + ("\n\n[interrupted]" if interrupted else ""))
        if interrupted:
            txt_path.write_text((answer or "") + "\n\n⏹ 已停止", encoding="utf-8")
        elif not answer:
            txt_path.write_text("⚠️ Agent 没有返回内容。", encoding="utf-8")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")
        txt_path.write_text(f"❌ Agent 调用失败：HTTP {error.code}\n\n当前 Base URL: {base_url}\n当前 Model: {model}\n\n原始错误：\n{body[:2000]}", encoding="utf-8")
    except Exception as error:
        txt_path.write_text(f"❌ Agent 调用失败：{error}", encoding="utf-8")
    finally:
        try:
            stop_path.unlink()
        except FileNotFoundError:
            pass
        done_path.write_text("1", encoding="utf-8")


def spinner():
    frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    return frames[int(time.time() * 4) % len(frames)]


def script_input_prompt():
    import select
    import sys
    candidates = []
    candidates.append(" ".join(sys.argv[1:]).strip())
    for key in ("query", "alfred_query", "alfred_textview_input", "input"):
        candidates.append(os.environ.get(key, "").strip())
    try:
        if select.select([sys.stdin], [], [], 0)[0]:
            candidates.append(sys.stdin.read().strip())
    except Exception:
        pass
    for candidate in candidates:
        if candidate:
            return candidate
    return ""


def main_view():
    inline_prompt = script_input_prompt()
    env_prompt = os.environ.get("ag_prompt", "").strip()
    prompt = inline_prompt or env_prompt
    mode = "continue" if inline_prompt else (os.environ.get("ag_mode", "new").strip() or "new")
    if not prompt:
        textview("请输入问题，例如：ag 帮我写一封请假邮件", "等待输入")
        return
    session = get_session(prompt, mode)
    paths = paths_for(session)
    request_id = os.environ.get("ag_request", "")
    previous_request = paths["request"].read_text(encoding="utf-8") if paths["request"].exists() else ""
    if inline_prompt:
        inline_request_id = "inline-" + hashlib.sha256(f"{session}:{inline_prompt}".encode("utf-8")).hexdigest()[:16]
        if inline_request_id == previous_request:
            request_id = previous_request
            should_start = False
        else:
            request_id = inline_request_id
            should_start = True
    elif request_id:
        should_start = request_id != previous_request
    else:
        should_start = not paths["request"].exists() and not paths["txt"].exists() and not paths["done"].exists()
    if should_start:
        start_worker(prompt, mode, session, paths)
        label = "继续会话，正在中断上一轮并追加引导…" if mode == "continue" else "Agent 正在启动…"
        textview(f"⏳ {label}", "启动中… 可按 Esc 关闭", rerun=0.2)
        return
    response = paths["txt"].read_text(encoding="utf-8") if paths["txt"].exists() else ""
    if paths["done"].exists():
        if "⏹ 已停止" in response:
            textview(response, "已停止。可用 agc 继续；agclear 清空；Esc 关闭")
        elif response.startswith("❌") or response.startswith("⚠️"):
            textview(response, "出错。检查 AG_BASE_URL / AG_MODEL / Key；可用 agc 重试")
        else:
            textview(response or "⚠️ Agent 没有返回内容。", "✅ 完成。可用 agc 继续；↵ 复制全文；Esc 关闭")
    else:
        mark = spinner()
        if response:
            shown = f"{response}\n\n{mark} 生成中…"
        else:
            shown = f"{mark} 正在连接 Agent…"
        textview(shown, "生成中… 可用 agc 追加引导，ags 停止", rerun=0.25)


if __name__ == "__main__":
    if os.environ.get("AG_STREAM_WORKER") == "1":
        stream_worker()
    else:
        main_view()
