"""`VideoGenerationProvider` implementation backed by a local ComfyUI server.

Free and fully uncensored since it's self-hosted — the same "local, no API
key, base_url-configured" shape as
`services/image_providers/automatic1111_provider.py`.

Unlike Automatic1111, ComfyUI has no single txt2vid endpoint. Its API is a
three-step dance:

1. `POST /prompt` with a complete workflow graph; returns a `prompt_id`.
2. Poll `GET /history/{prompt_id}` until the execution appears.
3. `GET /view?filename=…` to fetch the rendered file's bytes.

**The workflow graph is supplied by the user, not hardcoded here.** LTX-Video,
Wan and Hunyuan workflows differ substantially — and even one model's graph
changes between versions (LTX 2.5, 2.3 and 0.9.5 use different node sets and
different save nodes). A workflow baked into this repo would break on whatever
version is actually installed. Instead the user exports a graph they have
already confirmed works in the ComfyUI GUI (Workflow -> Export (API)) and
leaves two placeholders in it, which this provider substitutes per request:

- `{prompt}` — the generation prompt. Required; a text widget accepts it.

Seeds are *not* a placeholder: ComfyUI's seed widgets are numeric, so there is
no way to type one into the GUI before exporting. Instead the provider
randomises every `seed`/`noise_seed` input in the parsed graph. This is not
cosmetic — ComfyUI caches by graph hash, so a fixed seed makes a repeated
prompt return the *same* cached video instead of generating a new one.

This keeps the provider agnostic to model, workflow and ComfyUI version: any
graph that renders a video works, as long as it carries the prompt placeholder.
"""

import asyncio
import base64
import json
import random
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from src.services.providers.exceptions import ProviderAPIError, ProviderConfigError
from src.services.video_providers.base import VideoGenerationConfig, VideoGenerationProvider

PROMPT_PLACEHOLDER = "{prompt}"

# Input names ComfyUI's samplers use for their seed.
_SEED_INPUT_NAMES = ("seed", "noise_seed")

_POLL_INTERVAL_SECONDS = 2.0

# ComfyUI save nodes report their outputs under different keys depending on
# which one the workflow ends with (`SaveVideo`, `SaveAnimatedWEBP`,
# VideoHelperSuite's `VHS_VideoCombine`, …), so the file is located by shape
# rather than by key — see `_find_output_file`.
_MIME_BY_SUFFIX = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".webp": "image/webp",
    ".gif": "image/gif",
}
_DEFAULT_MIME = "video/mp4"


class ComfyUIVideoProvider(VideoGenerationProvider):
    """Runs a user-exported ComfyUI workflow and returns the rendered video."""

    def __init__(self, base_url: str, workflow_dir: Path, timeout_seconds: int) -> None:
        """Initialize the provider.

        Args:
            base_url: Base URL of the local ComfyUI server, e.g.
                `"http://127.0.0.1:8188"`.
            workflow_dir: Directory holding exported workflow JSON files. The
                file used for a request is `<workflow_dir>/<config.model>.json`.
            timeout_seconds: Overall budget for one generation, covering
                submission, polling and download. Video generation takes
                minutes, not seconds.
        """
        self._base_url = base_url.rstrip("/")
        self._workflow_dir = workflow_dir
        self._timeout_seconds = timeout_seconds

    async def generate_video(self, prompt: str, config: VideoGenerationConfig) -> str:
        """Generate a video by running the configured ComfyUI workflow.

        Args:
            prompt: The video description to generate from.
            config: `model` names the workflow file stem, so each ComfyUI
                catalog entry maps to its own exported graph.

        Returns:
            A `data:video/...;base64,...` URI of the generated video.

        Raises:
            ProviderConfigError: The workflow file is missing, is not valid
                JSON, or lacks the `{prompt}` placeholder.
            ProviderAPIError: ComfyUI rejected the graph, produced no file, or
                did not finish within the timeout.
        """
        graph = self._load_workflow(config.model, prompt)
        deadline = time.monotonic() + self._timeout_seconds

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                prompt_id = await self._submit(client, graph)
                outputs = await self._await_outputs(client, prompt_id, deadline)
                file_ref = _find_output_file(outputs)
                if file_ref is None:
                    raise ProviderAPIError(
                        "ComfyUI finished but produced no output file — does the workflow "
                        "end in a save node?"
                    )
                payload = await self._download(client, file_ref)
        except httpx.HTTPError as exc:
            raise ProviderAPIError(f"ComfyUI request failed: {exc}") from exc

        mime = _MIME_BY_SUFFIX.get(Path(file_ref["filename"]).suffix.lower(), _DEFAULT_MIME)
        return f"data:{mime};base64,{base64.b64encode(payload).decode()}"

    def _load_workflow(self, workflow_name: str, prompt: str) -> dict[str, Any]:
        """Read the exported workflow, inject the prompt, and freshen its seeds.

        Args:
            workflow_name: Workflow file stem, from `VideoGenerationConfig.model`.
            prompt: The generation prompt to inject.

        Returns:
            The workflow graph, ready to submit.

        Raises:
            ProviderConfigError: The file is missing, is not valid JSON, or has
                no `{prompt}` placeholder.
        """
        path = self._workflow_dir / f"{workflow_name}.json"
        try:
            raw = path.read_text()
        except OSError as exc:
            raise ProviderConfigError(
                f"ComfyUI workflow not found at {path}. Export one from ComfyUI "
                f"(Workflow -> Export (API)) with {PROMPT_PLACEHOLDER} as the prompt text."
            ) from exc

        if PROMPT_PLACEHOLDER not in raw:
            raise ProviderConfigError(
                f"Workflow {path} has no {PROMPT_PLACEHOLDER} placeholder, so the prompt "
                "would be ignored. Set the positive prompt node's text to exactly "
                f"{PROMPT_PLACEHOLDER} and re-export."
            )

        # Escape via json.dumps so quotes/newlines/backslashes in the prompt
        # cannot break the surrounding JSON, then strip its outer quotes since
        # the placeholder already sits inside a JSON string.
        raw = raw.replace(PROMPT_PLACEHOLDER, json.dumps(prompt)[1:-1])

        try:
            graph: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderConfigError(f"Workflow {path} is not valid JSON after substitution: {exc}") from exc

        _randomize_seeds(graph)
        return graph

    async def _submit(self, client: httpx.AsyncClient, graph: dict[str, Any]) -> str:
        """Queue the workflow and return its `prompt_id`."""
        response = await client.post(
            f"{self._base_url}/prompt",
            json={"prompt": graph, "client_id": uuid.uuid4().hex},
        )
        if response.status_code >= 400:
            # ComfyUI returns a structured validation error for a bad graph;
            # surfacing its body is far more useful than the status alone.
            raise ProviderAPIError(f"ComfyUI rejected the workflow: {response.text}")

        prompt_id = response.json().get("prompt_id")
        if not prompt_id:
            raise ProviderAPIError("ComfyUI did not return a prompt_id.")
        return str(prompt_id)

    async def _await_outputs(
        self, client: httpx.AsyncClient, prompt_id: str, deadline: float
    ) -> dict[str, Any]:
        """Poll `/history` until the execution reports outputs, or time out."""
        while True:
            response = await client.get(f"{self._base_url}/history/{prompt_id}")
            response.raise_for_status()
            entry = response.json().get(prompt_id)
            if entry:
                status = entry.get("status", {})
                if status.get("status_str") == "error":
                    raise ProviderAPIError(f"ComfyUI failed to execute the workflow: {status}")
                outputs = entry.get("outputs")
                if outputs:
                    return outputs

            if time.monotonic() >= deadline:
                raise ProviderAPIError(
                    f"ComfyUI did not finish within {self._timeout_seconds}s. Video generation "
                    "is slow on Apple Silicon — raise COMFYUI_TIMEOUT_SECONDS or reduce the "
                    "workflow's resolution/frame count."
                )
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)

    async def _download(self, client: httpx.AsyncClient, file_ref: dict[str, Any]) -> bytes:
        """Fetch one rendered file's bytes from `/view`."""
        response = await client.get(
            f"{self._base_url}/view",
            params={
                "filename": file_ref["filename"],
                "subfolder": file_ref.get("subfolder", ""),
                "type": file_ref.get("type", "output"),
            },
        )
        response.raise_for_status()
        return response.content


def _randomize_seeds(graph: dict[str, Any]) -> None:
    """Give every sampler in the graph a fresh seed, in place.

    ComfyUI returns a cached result for a graph it has already executed, so an
    unchanged seed would make a repeated prompt replay the previous video.
    A seed input wired to another node holds a `[node_id, slot]` list rather
    than a number; those are left alone.

    Args:
        graph: A parsed API-format workflow, keyed by node id.
    """
    for node in graph.values():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            continue
        for name in _SEED_INPUT_NAMES:
            if isinstance(inputs.get(name), (int, float)):
                inputs[name] = random.randint(0, 2**32 - 1)


def _find_output_file(outputs: dict[str, Any]) -> dict[str, Any] | None:
    """Locate the rendered file in a `/history` outputs blob.

    Searches by shape rather than by key: different save nodes report under
    `images`, `gifs`, `videos` or others, and which one a workflow uses is
    exactly what varies between ComfyUI/model versions.

    Args:
        outputs: The `outputs` mapping from a `/history/{id}` entry, keyed by
            node id.

    Returns:
        The first entry carrying a `filename`, preferring video containers over
        preview stills (a workflow can emit both), or `None` if there is none.
    """
    candidates: list[dict[str, Any]] = [
        item
        for node_output in outputs.values()
        if isinstance(node_output, dict)
        for value in node_output.values()
        if isinstance(value, list)
        for item in value
        if isinstance(item, dict) and item.get("filename")
    ]
    if not candidates:
        return None

    video_suffixes = {".mp4", ".webm", ".gif"}
    for item in candidates:
        if Path(item["filename"]).suffix.lower() in video_suffixes:
            return item
    return candidates[0]
