# v2.2.3

## Fixes

- Fix `agc <follow-up>` getting stuck at “continuing conversation…” after pressing Enter.
- The bug was caused by a request-id mismatch: external `agc` supplied `ag_request`, but the worker stored a different inline-style request id, so every Text View rerun restarted the same follow-up.

## Download

Use `AG-Agent-Chat-Streaming.alfredworkflow` from this release.
