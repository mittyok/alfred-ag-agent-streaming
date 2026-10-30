# v2.2.1

## Highlights

- Streaming agent responses in Alfred Text View
- Continue, stop, and clear conversation commands
- OpenAI-compatible `/chat/completions` support
- Local proxy support through `AG_BASE_URL`
- Clipboard image support via `image:clip`
- Image path support via `image:"/path with spaces/a.png"`

## Commands

- `ag <question>` starts a new chat
- `agc <follow-up>` continues the current chat
- `ags` stops generation
- `agclear` clears the current session
- `agkey <key>` saves an API key to macOS Keychain

## Notes

If your local proxy returns HTTP 400, check whether it supports the request payload and vision content. The workflow intentionally sends a minimal request body for better compatibility.
