# Usage

How to set up and run the AI Companion app locally. See `SPEC.md` for the product design and
`.claude`-tracked plan history for what's built vs. deferred — the short version: this is a
walking-skeleton increment. One hardcoded persona, one provider (Claude), no mode switching, no
accounts, no database. Enough to send a message and get a real streamed reply.

## Prerequisites

- Python 3.10+
- Node 18+
- An Anthropic API key — create one at https://console.anthropic.com/settings/keys

## One-time setup

```bash
cd "AI companion/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
# edit backend/.env and replace sk-ant-your-key-here with your real key

cd ../frontend
npm install
```

## Running it

**Option A — one command, one terminal:**

```bash
cd "AI companion"
./dev.sh
```

Starts both servers, prints their URLs, stops both on Ctrl+C. It also checks for the common
setup mistakes below before starting anything.

**Option B — manual, two terminals** (useful if you want to see each server's logs separately,
or restart one without the other):

```bash
# terminal 1 — backend
cd "AI companion/backend"
source .venv/bin/activate
python -m uvicorn src.main:app --reload --port 8000
```

```bash
# terminal 2 — frontend
cd "AI companion/frontend"
npm run dev
```

Either way: open **http://localhost:5173**, type a message, hit Send.

## Running tests

```bash
cd "AI companion/backend"
source .venv/bin/activate
pytest
```

Frontend has no test suite yet (out of scope for this increment); `npm run build` type-checks it.

## Optional: local video generation (free)

Image generation works out of the box via Pollinations. **Video generation needs a local
ComfyUI server** — there is no free hosted video API (every Pollinations video model is
paid-only, and Hugging Face retired its free serverless inference tier). Until you set this
up, the Video picker in the UI stays greyed out; everything else works normally.

Generation is slow: expect **several minutes per clip** on Apple Silicon.

### 1. Install ComfyUI

```bash
git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git ~/ComfyUI
cd ~/ComfyUI
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

On Apple Silicon, torch uses Metal (MPS) automatically — no CUDA setup.

### 2. Download the models

LTX-Video 2B is the model to use on a Mac. Wan 2.2 and HunyuanVideo have no stable Metal
path (an M1 Max took ~82 min for a 2-second clip), and Wan is reported to produce silently
corrupted output on M4 specifically (ComfyUI issue #15793).

```bash
cd ~/ComfyUI
curl -L -o models/checkpoints/ltx-video-2b-v0.9.safetensors \
  "https://huggingface.co/Lightricks/LTX-Video/resolve/main/ltx-video-2b-v0.9.safetensors"
curl -L -o models/text_encoders/t5xxl_fp16.safetensors \
  "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp16.safetensors"
```

That's ~18GB. **Use the `fp16` text encoder, not `fp8`.** Metal cannot represent float8 at
all (`RuntimeError: Undefined type Float8_e4m3fn`), and fp16 is the combination actually
verified working here.

### 3. Generate once in the GUI first

```bash
cd ~/ComfyUI && .venv/bin/python main.py --cpu-vae
```

**`--cpu-vae` is required on Apple Silicon, not optional.** PyTorch's Metal backend has a
broken `conv3d` kernel: it silently returns all zeros instead of erroring. LTX's VideoVAE is
a 3D causal VAE built on conv3d, so without this flag every frame decodes to uniform grey
while ComfyUI cheerfully reports success. Verify it yourself:

```bash
~/ComfyUI/.venv/bin/python -c "
import torch
x=torch.randn(1,4,5,16,16); w=torch.randn(8,4,3,3,3)*0.1
print('cpu  std:', torch.nn.functional.conv3d(x,w,padding=1).std().item())
print('mps  std:', torch.nn.functional.conv3d(x.to('mps'),w.to('mps'),padding=1).std().item())
"
```

A non-zero CPU std and a 0.0 MPS std confirms the bug. Sampling still runs on the GPU; only
the VAE decode moves to CPU, costing roughly 30s per clip.

Open http://127.0.0.1:8188, then **Workflow -> Browse Templates -> Video**, and pick
**LTXV Text to Video**. Before running it:

- Leave the **CLIPLoader** node on `t5xxl_fp16.safetensors` (see the fp8 warning above).
- If it runs out of memory, lower **EmptyLTXVLatentVideo**'s width/height/length
  (768x512x97 is the default; 512x320x65 is a safer starting point).

**Do not skip this step.** If it cannot generate here, nothing in the app can help — this is
where you settle on dimensions that actually fit.

### 4. Export the workflow for the app

Once it generates successfully:

1. Set the **positive** `CLIPTextEncode` node's text to exactly `{prompt}` (the one with the
   long scene description, not the one listing "low quality, worst quality, ...").
2. **Workflow -> Export (API)** — not plain "Export", which saves the editor format that the
   `/prompt` endpoint rejects.
3. Save it as `backend/workflows/ltx-video.json`.

You do not need to touch the seed: the app randomises it on every request, so a repeated
prompt generates a new video rather than replaying ComfyUI's cached one.

### 5. Point the app at ComfyUI

Add to `backend/.env`:

```
COMFYUI_BASE_URL=http://127.0.0.1:8188
```

Restart the backend. The Video picker should now offer "LTX-Video (local, uncensored)".
Leave ComfyUI running whenever you want video generation.

## Troubleshooting

**`ERROR: [Errno 48] Address already in use`**
Something is already listening on that port — usually a dev server from an earlier session that
didn't get stopped. Find and stop it:
```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN   # or :5173 for the frontend
kill <PID>
```

**`cd: no such file or directory: frontend`**
You ran `cd frontend` from inside `backend/` instead of the project root. `backend/` and
`frontend/` are siblings — `cd ..` first, or open a fresh terminal at the project root.

**Chat returns a 401 / "invalid x-api-key" error in the UI**
`backend/.env` still has the placeholder key, or an invalid one. Edit `backend/.env`, set a real
`ANTHROPIC_API_KEY`, then restart the backend (it only reads `.env` at startup, so `--reload`
picking up code changes won't pick up a `.env` edit — stop it with Ctrl+C and rerun).

**Server won't start at all, backend terminal shows a `ValidationError` about `anthropic_api_key`**
`backend/.env` is missing entirely, or missing that field. `cp backend/.env.example backend/.env`
and fill in your key. This is the app's fail-fast check — it refuses to start rather than fail
obscurely on the first chat request.
**Video picker is greyed out saying "none available — set COMFYUI_BASE_URL"**
Expected until you complete "Optional: local video generation" above. `COMFYUI_BASE_URL` is
unset, so the app hides a backend it knows would fail. Nothing is broken.

**Video request errors with "ComfyUI workflow not found at ..."**
You set `COMFYUI_BASE_URL` but never exported the workflow. Do step 4 above — the file must
land at `backend/workflows/ltx-video.json`.

**Video request errors with "has no {prompt} placeholder"**
You exported the workflow before editing the prompt node's text to `{prompt}`, so your prompt
would have been silently ignored. Fix the node, re-export.

**Video request errors with "ComfyUI rejected the workflow"**
Usually the editor format was exported instead of the API format. Re-export with
**Export (API)**. The error text quotes ComfyUI's own validation message, which names the
offending node.

**The same prompt keeps returning the identical video**
ComfyUI serves a cached result when the workflow graph is unchanged. The app randomises
`seed`/`noise_seed` inputs to prevent this, so if you still see it, your sampler names its
seed input something else — rename it or add it to `_SEED_INPUT_NAMES` in
`backend/src/services/video_providers/comfyui_provider.py`.

**The generated video is blank / uniform grey**
You started ComfyUI without `--cpu-vae`. Metal's `conv3d` returns all zeros, so the VAE
decodes nothing while ComfyUI still reports success — see step 3 above for the one-line
check. A suspiciously tiny output file (~14KB for a few seconds, versus ~100KB+ for real
content) is the tell: blank frames compress to almost nothing.

Note the sampler is *not* at fault here. If you dump the latent with a `SaveLatent` node it
will look healthy (no NaNs, std ≈ 0.9) — only the decode is broken.

**Video generation times out**
Default budget is 900s. Either lower the workflow's resolution/frame count, or raise
`COMFYUI_TIMEOUT_SECONDS` in `backend/.env`.
