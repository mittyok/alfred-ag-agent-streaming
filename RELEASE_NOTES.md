# v2.2.5

## Fixes

- Streaming output no longer forces `scroll: end` on every update by default.
- Added `AG_STREAM_SCROLL` workflow variable.
  - Default: `preserve`
  - Set to `end` to force always-follow-bottom behavior.

This makes long streaming answers less disruptive when you are reading earlier content.
