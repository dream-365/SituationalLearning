from __future__ import annotations

from situlearn.dictionary import parse_entry


def test_parse_entry_extracts_phonetic_and_audio() -> None:
    data = [
        {
            "word": "cherub",
            "phonetic": "/ˈtʃer.əb/",
            "phonetics": [
                {"text": "/ˈtʃer.əb/", "audio": "https://example.com/cherub.mp3"},
            ],
            "meanings": [
                {
                    "partOfSpeech": "noun",
                    "definitions": [{"definition": "a winged angelic being"}],
                }
            ],
        }
    ]

    entry = parse_entry(data, "cherub")

    assert entry is not None
    assert entry.word == "cherub"
    assert entry.phonetic == "/ˈtʃer.əb/"
    assert entry.audio_url == "https://example.com/cherub.mp3"
    assert entry.part_of_speech == "noun"
    assert entry.definition_en == "a winged angelic being"


def test_parse_entry_handles_missing_audio() -> None:
    data = [{"word": "Renaissance", "meanings": []}]

    entry = parse_entry(data, "Renaissance")

    assert entry is not None
    assert entry.audio_url is None
    assert entry.part_of_speech == "unknown"


def test_parse_entry_rejects_empty_payload() -> None:
    assert parse_entry({}, "x") is None
    assert parse_entry([], "x") is None
