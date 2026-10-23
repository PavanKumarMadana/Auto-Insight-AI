import pandas as pd
from src.task1 import aspects, preprocess, review_id, sentiment
from src.task2 import extract_array, issue_category, parse_date, tags_from_text


def test_task1_preprocessing_and_id_are_stable():
    assert preprocess("  It&#39;s   NOT bad! ") == "It's NOT bad!"
    row = {"Product URL": "p", "Review Text": "great"}
    assert review_id(row) == review_id(row)


def test_task1_sentiment_and_aspects():
    label, score = sentiment("Excellent sound and easy setup")
    assert label in {"Positive", "Neutral", "Negative"}
    assert -1 <= score <= 1
    assert aspects("sound and easy setup", "Positive")


def test_task2_empty_and_tags():
    assert tags_from_text(None) == []
    tags = tags_from_text("Radio lost communication and has a black screen")
    assert "radio/audio unit" in tags and "display/screen" in tags
    assert issue_category(tags) == "Connectivity / communication"


def test_task2_parsing_helpers():
    assert extract_array("['Radio', 'Display']") == ["Radio", "Display"]
    assert extract_array("bad") == []
    assert pd.isna(parse_date("invalid"))
