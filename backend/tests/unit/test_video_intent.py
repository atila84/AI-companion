"""Unit tests for `detect_video_prompt`'s keyword/regex trigger detection."""

from src.services.video_intent import detect_video_prompt


def test_detects_animate_me_phrasing() -> None:
    assert detect_video_prompt("animate me a sunset over the ocean") == "a sunset over the ocean"


def test_detects_generate_a_video_phrasing() -> None:
    assert detect_video_prompt("generate a video of a red fox running") == "a red fox running"


def test_detects_send_me_a_clip_phrasing() -> None:
    assert detect_video_prompt("send me a clip of a cat") == "a cat"


def test_falls_back_to_full_message_when_nothing_left_after_trigger() -> None:
    assert detect_video_prompt("animate me") == "animate me"


def test_ordinary_message_has_no_video_intent() -> None:
    assert detect_video_prompt("how was your day?") is None


def test_does_not_match_verb_and_noun_in_different_sentences() -> None:
    assert detect_video_prompt("generate a report. by the way here's a nice video") is None


def test_does_not_match_send_without_a_following_video_noun() -> None:
    assert detect_video_prompt("send me the file when you get a chance") is None


def test_image_request_is_not_mistaken_for_video_intent() -> None:
    # "draw"/"sketch" image triggers have no video-noun counterpart here, so
    # a plain image request must not also fire video intent.
    assert detect_video_prompt("draw me a sunset") is None
    assert detect_video_prompt("generate an image of a red fox") is None
