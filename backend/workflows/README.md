# ComfyUI workflows

Workflow graphs exported from ComfyUI, used by
`src/services/video_providers/comfyui_provider.py`.

A video catalog entry's `model` names the file stem here — e.g.
`comfyui/ltx-video` loads `ltx-video.json`.

## Why these aren't checked in

An exported graph embeds absolute model paths and settings tuned to one
machine's VRAM, so it is not portable. `*.json` in this directory is
gitignored; each developer exports their own.

## Exporting one

1. Build a text-to-video workflow in ComfyUI and **confirm it generates in the
   GUI first**. If it can't render there, nothing in this app can help.
2. Set the positive prompt node's text to exactly `{prompt}`.
3. Workflow -> **Export (API)** — not the plain "Export", which saves the
   editor format the `/prompt` endpoint does not accept.
4. Save it here as `<name>.json` and make sure a catalog entry in
   `src/config.py::_default_video_catalog()` points at that stem.

Seeds need no placeholder — ComfyUI's seed widgets are numeric, so one cannot
be typed in. The provider randomises every `seed`/`noise_seed` input instead,
which matters because ComfyUI caches by graph hash and would otherwise replay
the previous video for a repeated prompt.

Beyond the prompt, the provider is agnostic to model, workflow and ComfyUI
version — any graph ending in a save node works.
