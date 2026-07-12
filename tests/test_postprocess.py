import json, os, sys, tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.postprocess import (
    parse_llm_response,
    validate_cloze,
    validate_basic,
    process_rows,
    word_count,
)


# -- parse_llm_response --

def test_parse_valid_jsonl():
    lines = [
        json.dumps({"Statements": "test"}),
        json.dumps({"Front": "q", "Back": "a"}),
    ]
    tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl")
    tmp.write("\n".join(lines) + "\n")
    tmp.close()
    try:
        rows = parse_llm_response(tmp.name)
        assert len(rows) == 2
        assert rows[0]["Statements"] == "test"
    finally:
        os.unlink(tmp.name)


def test_parse_invalid_jsonl():
    lines = ["not json", json.dumps({"Statements": "valid"})]
    tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl")
    tmp.write("\n".join(lines) + "\n")
    tmp.close()
    try:
        rows = parse_llm_response(tmp.name)
        assert len(rows) == 2
        assert "raw" in rows[0]
        assert rows[0]["raw"] == "not json"
        assert rows[1]["Statements"] == "valid"
    finally:
        os.unlink(tmp.name)


def test_parse_empty_jsonl():
    tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl")
    tmp.write("")
    tmp.close()
    try:
        rows = parse_llm_response(tmp.name)
        assert rows == []
    finally:
        os.unlink(tmp.name)


# -- validate_cloze --

def test_cloze_valid_simple():
    assert validate_cloze("Necrosis shows {{c1::lack of enhancement}}") is None


def test_cloze_valid_multi():
    assert validate_cloze("{{c1::Finding A}} vs {{c2::Finding B}}") is None


def test_cloze_missing():
    assert validate_cloze("No cloze here") == "missing_cloze_syntax"


def test_cloze_too_many_words():
    assert validate_cloze("{{c1::one two three four five}}") == "cloze_too_many_words"


def test_cloze_empty():
    assert validate_cloze("") == "missing_cloze_syntax"


# -- validate_basic --

def test_basic_valid():
    assert validate_basic("What is pancreatitis?") is None


def test_basic_too_long():
    long_q = " ".join(["word"] * 45)
    assert validate_basic(long_q) == "word_count_exceeded"


def test_basic_boundary():
    q = " ".join(["word"] * 40)
    assert validate_basic(q) is None


# -- word_count --

def test_word_count_normal():
    assert word_count("one two three") == 3


def test_word_count_empty():
    assert word_count("") == 0


def test_word_count_whitespace():
    assert word_count("  ") == 0


# -- process_rows --

def test_process_cloze_rows():
    rows = [
        {"Statements": "{{c1::enhancement}} is key"},
        {"Statements": "{{c1::calcification}} seen"},
    ]
    cloze, basic, errors = process_rows(rows, Path("."))
    assert len(cloze) == 2
    assert len(basic) == 0
    assert len(errors) == 0


def test_process_basic_rows():
    rows = [
        {"Front": "What finds A?", "Back": "Finding A"},
        {"Front": "What finds B?", "Back": "Finding B"},
    ]
    cloze, basic, errors = process_rows(rows, Path("."))
    assert len(cloze) == 0
    assert len(basic) == 2
    assert len(errors) == 0


def test_process_dedup():
    rows = [
        {"Statements": "{{c1::enhancement}} key"},
        {"Statements": "{{c1::enhancement}} key"},
    ]
    cloze, basic, errors = process_rows(rows, Path("."))
    assert len(cloze) == 1  # second should be deduped


def test_process_catches_missing_cloze():
    rows = [{"Statements": "no cloze here"}]
    cloze, basic, errors = process_rows(rows, Path("."))
    assert len(cloze) == 0
    assert len(errors) == 1
    assert errors[0][0] == "Cloze"
    assert errors[0][2] == "missing_cloze_syntax"


def test_process_catches_word_count():
    rows = [{"Statements": " ".join(["word"] * 50) + " {{c1::term}}"}]
    cloze, basic, errors = process_rows(rows, Path("."))
    assert len(cloze) == 0
    assert len(errors) == 1
    assert errors[0][2] == "word_count_exceeded"


def test_process_unknown_format():
    rows = [{"UnknownKey": "value"}]
    cloze, basic, errors = process_rows(rows, Path("."))
    assert len(cloze) == 0
    assert len(basic) == 0
    assert len(errors) == 1
    assert errors[0][2] == "unknown_format"


def test_process_mixed_rows():
    rows = [
        {"Statements": "{{c1::enhancement}} key"},
        {"Front": "What is it?", "Back": "Enhancement"},
        {"Statements": "bad"},
        {"Front": " ".join(["word"] * 50), "Back": "long"},
    ]
    cloze, basic, errors = process_rows(rows, Path("."))
    assert len(cloze) == 1
    assert len(basic) == 1
    assert len(errors) == 2


# -- CSV output (integration) --

def test_write_csv_output(tmp_path):
    rows = [
        {"Statements": "{{c1::enhancement}} is key"},
    ]
    cloze, basic, errors = process_rows(rows, tmp_path)
    from scripts.postprocess import write_csv
    write_csv(cloze, tmp_path / "cloze_cards.csv", ["Notetype", "Text", "Tags"])
    assert (tmp_path / "cloze_cards.csv").exists()
    content = (tmp_path / "cloze_cards.csv").read_text(encoding="utf-8")
    assert "#separator:Tab" in content
    assert "enhancement" in content
