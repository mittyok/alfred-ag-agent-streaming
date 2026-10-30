#!/usr/bin/env python3
import json
import shutil
import subprocess
import sys
from pathlib import Path

def cache_dir():
    return Path.home() / "Library" / "Caches" / "com.codex.ag-agent-chat"

def notify(text):
    script = "\n".join(["on run argv", "display notification (item 1 of argv) with title \"AG Agent\"", "end run"])
    subprocess.run(["/usr/bin/osascript", "-e", script, text], check=False)

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "stop"
    root = cache_dir()
    cur = root / "current_session"
    if action == "clear":
        if root.exists():
            shutil.rmtree(root)
        notify("AG 当前会话已清空")
        print("AG 当前会话已清空")
        return
    if not cur.exists():
        notify("没有正在进行的 AG 会话")
        print("没有正在进行的 AG 会话")
        return
    session = cur.read_text(encoding="utf-8").strip()
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in session)[:100]
    (root / f"{safe}.stop").write_text("1", encoding="utf-8")
    notify("已请求停止当前 AG 生成")
    print("已请求停止当前 AG 生成")

if __name__ == "__main__":
    main()
