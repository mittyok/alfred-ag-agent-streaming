# Security Notes

## API Keys

- `agkey <key>` stores the key in macOS Keychain using `/usr/bin/security`.
- Do not share Alfred debugger logs after entering secrets.
- For public/shared machines, prefer setting `OPENAI_API_KEY` in Alfred Workflow Variables and marking it non-exported/password-protected where possible.

## Data Sent to Providers

Prompts, conversation context, and image content are sent to the configured `AG_BASE_URL`. Review your provider or local proxy before sending sensitive data.

## Local Cache

The workflow stores session state under Alfred workflow cache or `~/Library/Caches/com.codex.ag-agent-chat`.

- Text history is cached for conversation continuation.
- Clipboard images used by `image:clip` are converted to base64 and deleted after being read.
- Run `agclear` to clear the active session cache.

## Process Safety

The workflow does not use `shell=True`. Subprocess calls use fixed system binaries (`security`, `osascript`, `python3`) with argument arrays.
