#!/usr/bin/env python3
import subprocess
import sys

SERVICE = "com.codex.ag-agent-chat"
ACCOUNT = "OPENAI_API_KEY"


def notify(text):
    script = "\n".join([
        "on run argv",
        "display notification (item 1 of argv) with title \"AG Agent\"",
        "end run",
    ])
    subprocess.run(["/usr/bin/osascript", "-e", script, text], check=False)


def main():
    key = " ".join(sys.argv[1:]).strip()
    if not key:
        message = "请这样设置：agkey sk-你的-key"
        notify(message)
        print(message)
        return
    subprocess.run([
        "/usr/bin/security",
        "add-generic-password",
        "-U",
        "-s",
        SERVICE,
        "-a",
        ACCOUNT,
        "-w",
        key,
    ], check=True)
    message = "AG API Key 已保存到 macOS Keychain"
    notify(message)
    print(message)


if __name__ == "__main__":
    main()
