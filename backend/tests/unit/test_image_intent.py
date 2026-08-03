"""Unit tests for `detect_image_prompt`'s keyword/regex trigger detection."""

from src.services.image_intent import detect_image_prompt


def test_detects_draw_me_phrasing() -> None:
    assert detect_image_prompt("draw me a sunset over the ocean") == "a sunset over the ocean"


def test_detects_generate_an_image_phrasing() -> None:
    assert detect_image_prompt("generate an image of a red fox") == "a red fox"


def test_detects_send_me_a_picture_phrasing() -> None:
    assert detect_image_prompt("send me a picture of a cat") == "a cat"


def test_falls_back_to_full_message_when_nothing_left_after_trigger() -> None:
    assert detect_image_prompt("draw me") == "draw me"


def test_ordinary_message_has_no_image_intent() -> None:
    assert detect_image_prompt("how was your day?") is None


def test_word_boundary_avoids_false_positive_inside_another_word() -> None:
    assert detect_image_prompt("I need to withdraw money from my account") is None


def test_detects_noun_without_a_leading_article() -> None:
    # Regression: "generate porno picture" has an adjective, not an article,
    # between the verb and the noun — must still be detected.
    assert detect_image_prompt("generate porno picture") == "generate porno picture"


def test_detects_show_me_without_article() -> None:
    assert detect_image_prompt("show me nude picture") == "show me nude picture"


def test_does_not_match_verb_and_noun_in_different_sentences() -> None:
    assert detect_image_prompt("generate a report. by the way here's a nice picture") is None


def test_does_not_match_send_without_a_following_image_noun() -> None:
    assert detect_image_prompt("send me the file when you get a chance") is None
