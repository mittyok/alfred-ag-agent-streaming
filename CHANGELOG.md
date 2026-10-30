# Changelog

## v2.2.1

- Add clipboard image support via `image:clip`, `image:clipboard`, and `image:pasteboard`.
- Add image path support via `image:"/path/with spaces/a.png"`.
- Support multiple images in one prompt.
- Keep streaming Text View interaction with follow-up input.

## v2.0.4

- Fix repeated Text View input reruns restarting the same follow-up request.
- Add stable inline request IDs and request placeholders.

## v1.9.0

- Add clearer startup/generating/completed/stopped/error states.

## v1.7.0

- Add streaming Text View implementation via background SSE worker and Text View `rerun`.
