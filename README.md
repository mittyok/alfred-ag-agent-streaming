# AG Agent Chat Streaming for Alfred

A lightweight Alfred workflow for chatting with OpenAI-compatible agents with streaming output in Alfred Text View.

It turns Alfred into a fast “Agent Bar”: ask a question, stream the answer, continue the conversation, stop generation, and optionally attach images from the clipboard or file paths.

## Features

- Streaming responses in Alfred Text View
- Continue a conversation from Alfred or from the Text View input field
- Stop generation with `ags`
- Clear the current session with `agclear`
- OpenAI-compatible `/chat/completions` support
- Local proxy support, including `http://127.0.0.1:5000/v1`
- API key storage in macOS Keychain via `agkey`
- Basic vision input via `image:clip` or `image:"/path/to/image.png"`

## Installation

1. Download `AG-Agent-Chat-Streaming.alfredworkflow` from GitHub Releases.
2. Double-click it to import into Alfred.
3. Configure your provider:
   - For OpenAI: run `agkey sk-...`, or set `OPENAI_API_KEY` in Workflow Variables.
   - For a local proxy: set `AG_BASE_URL`, for example `http://127.0.0.1:5000/v1`.

Default variables:

| Variable | Default | Description |
|---|---:|---|
| `AG_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible API base URL |
| `AG_MODEL` | `gpt-4o-mini` | Model name sent to the API |
| `AG_SYSTEM_PROMPT` | Chinese concise assistant prompt | System prompt |
| `OPENAI_API_KEY` | empty | Optional for local `127.0.0.1` / `localhost` proxies |

## Commands

| Command | Description |
|---|---|
| `ag <question>` | Start a new streaming chat |
| `agc <follow-up>` | Continue the current chat |
| `ags` | Stop current generation |
| `agclear` | Clear current session and cache |
| `agkey <key>` | Save API key to macOS Keychain |

You can also continue the conversation directly from the Text View input field.

## Image Input

Clipboard image:

```text
ag explain this screenshot image:clip
```

Image file path:

```text
ag compare image:"/Users/me/Desktop/a b.png" image:"/Users/me/Desktop/c.png"
```

Notes:

- Use quotes for paths containing spaces.
- `image:clip`, `image:clipboard`, and `image:pasteboard` read image data from macOS clipboard.
- Your configured model/provider must support vision-style `image_url` message content.

## How Streaming Works

Alfred’s `Run Script -> Text View` chain does not stream: Alfred waits for the script to finish.

This workflow uses Text View Script Source and `rerun`:

1. Text View starts `stream_textview.py`.
2. A background worker reads the API’s SSE stream.
3. Tokens are written to a cache file.
4. Text View refreshes every ~0.25 seconds and renders the cached content.

## Compatibility Notes

OpenAI-compatible APIs are not always fully OpenAI-compatible. Some local proxies reject optional parameters such as `temperature`.

For better compatibility, this workflow sends a minimal request by default:

- `model`
- `messages`
- `stream`

## Privacy

See also [SECURITY.md](SECURITY.md).


- API keys saved with `agkey` are stored in macOS Keychain.
- Prompts and images are sent to the configured `AG_BASE_URL`.
- Temporary state is stored in Alfred’s workflow cache or `~/Library/Caches/com.codex.ag-agent-chat`.
- Clipboard images used with `image:clip` are saved temporarily in the workflow cache before being sent.

## Limitations

- Alfred Text View cannot intercept paste events, so pasted images cannot appear as attachment chips in the input field.
- For image input, use `image:clip` or `image:"/path/to/image.png"`.
- Text View copy behavior is controlled by Alfred; this workflow focuses on fast interaction rather than a full chat UI.

## Development

Package the workflow:

```bash
cd workflow
zip -r ../AG-Agent-Chat-Streaming.alfredworkflow .
```

Validate `info.plist`:

```bash
plutil -lint workflow/info.plist
```

## Roadmap

- Finder Universal Action for image files
- Optional auto-detect clipboard image mode
- Better session/history browser
- GitHub Actions release packaging
