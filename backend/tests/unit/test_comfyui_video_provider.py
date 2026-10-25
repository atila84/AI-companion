"""Unit tests for `ComfyUIVideoProvider`.

ComfyUI is mocked at the transport layer with `httpx.MockTransport`, so these
run without a ComfyUI server and without adding a mocking dependency.
"""

import base64
import json
from functools import partial
from pathlib import Path
from typing import Any

import httpx
import pytest

from src.services.providers.exceptions import ProviderAPIError, ProviderConfigError
from src.services.video_providers.base import VideoGenerationConfig
from src.services.video_providers.comfyui_provider import (
    ComfyUIVideoProvider,
    _find_output_file,
    _randomize_seeds,
)

BASE_URL = "http://127.0.0.1:8188"
VIDEO_BYTES = b"\x00\x01fake-mp4-bytes"


def _workflow_text(prompt_placeholder: str = "{prompt}") -> str:
    """A minimal graph shaped like a ComfyUI API-format export.

    The seed is a plain number, as a GUI export produces — ComfyUI's seed
    widget is numeric, so a placeholder cannot be typed into it.
    """
    return json.dumps(
        {
            "3": {"class_type": "KSampler", "inputs": {"seed": 12345, "steps": 20}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt_placeholder}},
            "9": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "out"}},
        }
    )


@pytest.fixture
def workflow_dir(tmp_path: Path) -> Path:
    (tmp_path / "ltx-video.json").write_text(_workflow_text())
    return tmp_path


def _make_handler(
    history_responses: list[dict[str, Any]],
    filename: str = "out_00001.mp4",
) -> tuple[Any, dict[str, Any]]:
    """Build a MockTransport handler plus a dict recording what was submitted."""
    recorded: dict[str, Any] = {"submitted": None, "history_calls": 0, "view_params": None}
    pending = list(history_responses)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/prompt":
            recorded["submitted"] = json.loads(request.content)
            return httpx.Response(200, json={"prompt_id": "pid-1"})
        if request.url.path.startswith("/history/"):
            recorded["history_calls"] += 1
            body = pending.pop(0) if pending else {}
            return httpx.Response(200, json=body)
        if request.url.path == "/view":
            recorded["view_params"] = dict(request.url.params)
            return httpx.Response(200, content=VIDEO_BYTES)
        return httpx.Response(404)

    return handler, recorded


def _patch_client(monkeypatch: pytest.MonkeyPatch, handler: Any) -> None:
    """Force the provider's internally-constructed client onto a mock transport."""
    monkeypatch.setattr(
        httpx, "AsyncClient", partial(httpx.AsyncClient, transport=httpx.MockTransport(handler))
    )


def _completed(filename: str = "out_00001.mp4", key: str = "images") -> dict[str, Any]:
    return {"pid-1": {"status": {"status_str": "success"}, "outputs": {"9": {key: [{"filename": filename, "subfolder": "", "type": "output"}]}}}}


@pytest.fixture
def provider(workflow_dir: Path) -> ComfyUIVideoProvider:
    return ComfyUIVideoProvider(BASE_URL, workflow_dir, timeout_seconds=30)


# --- workflow loading / placeholder substitution -------------------------------


async def test_prompt_placeholder_is_substituted(
    provider: ComfyUIVideoProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler, recorded = _make_handler([_completed()])
    _patch_client(monkeypatch, handler)

    await provider.generate_video("a sunset over the ocean", VideoGenerationConfig(model="ltx-video"))

    assert recorded["submitted"]["prompt"]["6"]["inputs"]["text"] == "a sunset over the ocean"


async def test_prompt_with_quotes_and_newlines_keeps_workflow_valid_json(
    provider: ComfyUIVideoProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A naive string replace would produce invalid JSON here."""
    handler, recorded = _make_handler([_completed()])
    _patch_client(monkeypatch, handler)
    nasty = 'a "quoted" prompt\nwith a newline and a \\ backslash'

    await provider.generate_video(nasty, VideoGenerationConfig(model="ltx-video"))

    assert recorded["submitted"]["prompt"]["6"]["inputs"]["text"] == nasty


async def test_seed_is_randomized_between_runs(
    provider: ComfyUIVideoProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without a fresh seed ComfyUI returns its cached video for a repeated prompt."""
    seeds = set()
    for _ in range(5):
        handler, recorded = _make_handler([_completed()])
        _patch_client(monkeypatch, handler)
        await provider.generate_video("same prompt", VideoGenerationConfig(model="ltx-video"))
        seeds.add(recorded["submitted"]["prompt"]["3"]["inputs"]["seed"])

    assert len(seeds) > 1
    assert 12345 not in seeds  # the exported literal must not survive


async def test_missing_workflow_file_raises_config_error(
    provider: ComfyUIVideoProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler, _ = _make_handler([_completed()])
    _patch_client(monkeypatch, handler)

    with pytest.raises(ProviderConfigError, match="workflow not found"):
        await provider.generate_video("x", VideoGenerationConfig(model="does-not-exist"))


async def test_workflow_without_prompt_placeholder_raises_config_error(
    workflow_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (workflow_dir / "no-placeholder.json").write_text(_workflow_text(prompt_placeholder="hardcoded"))
    provider = ComfyUIVideoProvider(BASE_URL, workflow_dir, timeout_seconds=30)
    handler, _ = _make_handler([_completed()])
    _patch_client(monkeypatch, handler)

    with pytest.raises(ProviderConfigError, match="no {prompt} placeholder"):
        await provider.generate_video("x", VideoGenerationConfig(model="no-placeholder"))


# --- submit / poll / download --------------------------------------------------


async def test_polls_until_outputs_appear(
    provider: ComfyUIVideoProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty /history body means still running, not failed."""
    handler, recorded = _make_handler([{}, {}, _completed()])
    _patch_client(monkeypatch, handler)
    monkeypatch.setattr("src.services.video_providers.comfyui_provider._POLL_INTERVAL_SECONDS", 0)

    result = await provider.generate_video("x", VideoGenerationConfig(model="ltx-video"))

    assert recorded["history_calls"] == 3
    assert result.startswith("data:video/mp4;base64,")


async def test_returns_data_uri_with_the_downloaded_bytes(
    provider: ComfyUIVideoProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler, recorded = _make_handler([_completed()])
    _patch_client(monkeypatch, handler)

    result = await provider.generate_video("x", VideoGenerationConfig(model="ltx-video"))

    assert result == f"data:video/mp4;base64,{base64.b64encode(VIDEO_BYTES).decode()}"
    assert recorded["view_params"]["filename"] == "out_00001.mp4"
    assert recorded["view_params"]["type"] == "output"


async def test_webm_output_gets_the_right_mime(
    provider: ComfyUIVideoProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler, _ = _make_handler([_completed(filename="out.webm")])
    _patch_client(monkeypatch, handler)

    result = await provider.generate_video("x", VideoGenerationConfig(model="ltx-video"))

    assert result.startswith("data:video/webm;base64,")


async def test_rejected_workflow_surfaces_comfyui_validation_error(
    provider: ComfyUIVideoProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text='{"error": "required input is missing: vae"}')

    _patch_client(monkeypatch, handler)

    with pytest.raises(ProviderAPIError, match="required input is missing"):
        await provider.generate_video("x", VideoGenerationConfig(model="ltx-video"))


async def test_execution_error_is_reported(
    provider: ComfyUIVideoProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    failed = {"pid-1": {"status": {"status_str": "error", "messages": ["OOM"]}}}
    handler, _ = _make_handler([failed])
    _patch_client(monkeypatch, handler)

    with pytest.raises(ProviderAPIError, match="failed to execute"):
        await provider.generate_video("x", VideoGenerationConfig(model="ltx-video"))


async def test_timeout_raises_with_actionable_message(
    workflow_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = ComfyUIVideoProvider(BASE_URL, workflow_dir, timeout_seconds=0)
    handler, _ = _make_handler([{}])
    _patch_client(monkeypatch, handler)
    monkeypatch.setattr("src.services.video_providers.comfyui_provider._POLL_INTERVAL_SECONDS", 0)

    with pytest.raises(ProviderAPIError, match="did not finish within"):
        await provider.generate_video("x", VideoGenerationConfig(model="ltx-video"))


async def test_completed_run_with_no_file_raises(
    provider: ComfyUIVideoProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    no_file = {"pid-1": {"status": {"status_str": "success"}, "outputs": {"9": {"text": ["nope"]}}}}
    handler, _ = _make_handler([no_file])
    _patch_client(monkeypatch, handler)

    with pytest.raises(ProviderAPIError, match="produced no output file"):
        await provider.generate_video("x", VideoGenerationConfig(model="ltx-video"))


# --- generic output parsing ----------------------------------------------------


@pytest.mark.parametrize("key", ["images", "gifs", "videos"])
def test_output_file_is_found_under_any_save_node_key(key: str) -> None:
    """Which key a save node uses varies by ComfyUI/model version."""
    outputs = {"9": {key: [{"filename": "out.mp4", "subfolder": "", "type": "output"}]}}

    found = _find_output_file(outputs)

    assert found is not None and found["filename"] == "out.mp4"


def test_video_is_preferred_over_a_preview_still() -> None:
    """Some workflows emit both a preview image and the real video."""
    outputs = {
        "8": {"images": [{"filename": "preview.png"}]},
        "9": {"gifs": [{"filename": "out.mp4"}]},
    }

    found = _find_output_file(outputs)

    assert found is not None and found["filename"] == "out.mp4"


def test_no_outputs_returns_none() -> None:
    assert _find_output_file({}) is None


# --- seed randomisation --------------------------------------------------------


def test_randomize_seeds_covers_both_sampler_input_names() -> None:
    graph = {
        "3": {"class_type": "KSampler", "inputs": {"seed": 1, "steps": 20}},
        "7": {"class_type": "SamplerCustom", "inputs": {"noise_seed": 2}},
    }

    _randomize_seeds(graph)

    assert graph["3"]["inputs"]["seed"] != 1
    assert graph["7"]["inputs"]["noise_seed"] != 2
    assert graph["3"]["inputs"]["steps"] == 20  # untouched


def test_randomize_seeds_leaves_linked_inputs_alone() -> None:
    """A seed wired from another node is a [node_id, slot] link, not a value."""
    graph = {"3": {"class_type": "KSampler", "inputs": {"seed": ["10", 0]}}}

    _randomize_seeds(graph)

    assert graph["3"]["inputs"]["seed"] == ["10", 0]


async def test_still_image_output_raises_instead_of_mislabelling_it(
    provider: ComfyUIVideoProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: a PNG was being returned as `data:video/mp4`, which the
    frontend's <video> tag silently fails to play. Found by running against a
    real ComfyUI whose workflow ended in SaveImage."""
    handler, _ = _make_handler([_completed(filename="ComfyUI_00001_.png")])
    _patch_client(monkeypatch, handler)

    with pytest.raises(ProviderAPIError, match="not a video"):
        await provider.generate_video("x", VideoGenerationConfig(model="ltx-video"))
