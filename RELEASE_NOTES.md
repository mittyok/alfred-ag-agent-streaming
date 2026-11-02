# v2.2.4

## Fixes

- Improve scroll stability during streaming output.
- Text View no longer replaces the entire response on every rerun once content is visible.
- Streaming updates now append only the newly generated delta and keep `scroll: end`.

This prevents the view/scrollbar from jumping back toward the top while long answers are still streaming.
