import json, os, sys, tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.extract import _clean, _detect_no_text, extract_chunks


def _make_pdf(pages: list[str]) -> str:
    import pymupdf
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((50, 50), text, fontsize=12)
    path = os.path.join(tempfile.gettempdir(), f"test_{os.urandom(4).hex()}.pdf")
    doc.save(path)
    doc.close()
    return path


# -- _clean --

def test_clean_joins_hyphenated_line_breaks():
    assert _clean("nec-\nrosis") == "necrosis"


def test_clean_skips_normal_text():
    assert _clean("acute pancreatitis") == "acute pancreatitis"


def test_clean_multi_hyphenations():
    assert _clean("pancre-\nati-\ntis") == "pancreatitis"


# -- _detect_no_text --

def test_detect_no_text_true():
    pdf = _make_pdf(["a", "", "bc"])
    try:
        import pymupdf
        doc = pymupdf.open(pdf)
        assert _detect_no_text(doc) is True
        doc.close()
    finally:
        os.unlink(pdf)


def test_detect_no_text_false():
    pdf = _make_pdf(["pancreatitis is inflammation of the pancreas requiring urgent imaging and clinical evaluation"] * 5)
    try:
        import pymupdf
        doc = pymupdf.open(pdf)
        assert _detect_no_text(doc) is False
        doc.close()
    finally:
        os.unlink(pdf)


# -- extract_chunks --

def test_extract_chunks_simple():
    pdf = _make_pdf(["page one", "page two", "page three", "page four", "page five"])
    try:
        chunks = extract_chunks(pdf, pages_per_chunk=2)
        assert len(chunks) == 3
        assert chunks[0]["pages"] == [1, 2]
        assert "page one" in chunks[0]["text"]
        assert "page two" in chunks[0]["text"]
        assert chunks[2]["pages"] == [5]
    finally:
        os.unlink(pdf)


def test_extract_chunks_default_grouping():
    pdf = _make_pdf([f"page {i+1}" for i in range(10)])
    try:
        chunks = extract_chunks(pdf)
        assert len(chunks) == 3  # 10 pages / 4 = 3 chunks (4+4+2)
        assert len(chunks[0]["pages"]) == 4
        assert len(chunks[1]["pages"]) == 4
        assert len(chunks[2]["pages"]) == 2
    finally:
        os.unlink(pdf)


def test_extract_chunks_one_per_page():
    pdf = _make_pdf(["alpha", "beta", "gamma"])
    try:
        chunks = extract_chunks(pdf, pages_per_chunk=1)
        assert len(chunks) == 3
        assert chunks[0]["pages"] == [1]
        assert chunks[1]["pages"] == [2]
        assert chunks[2]["pages"] == [3]
    finally:
        os.unlink(pdf)


def test_extract_chunks_skips_empty_pages():
    pdf = _make_pdf(["page one", "", "page three", "", "page five"])
    try:
        chunks = extract_chunks(pdf, pages_per_chunk=2)
        assert len(chunks) == 2
        assert chunks[0]["pages"] == [1, 3]
        assert chunks[1]["pages"] == [5]
    finally:
        os.unlink(pdf)


def test_extract_chunks_with_chapter():
    pages = ["intro text", "more intro", "Chapter 1 begins", "content 1", "content 2"]
    pdf = _make_pdf(pages)
    try:
        chunks = extract_chunks(pdf, chapter="Chapter 1", pages_per_chunk=1)
        assert len(chunks) == 3
        assert chunks[0]["pages"] == [3]
        assert "Chapter 1 begins" in chunks[0]["text"]
    finally:
        os.unlink(pdf)


def test_extract_chunks_chapter_not_found():
    pdf = _make_pdf(["just some text", "nothing here"])
    try:
        with pytest.raises(SystemExit):
            extract_chunks(pdf, chapter="Nonexistent")
    finally:
        os.unlink(pdf)


def test_extract_chunks_invalid_path():
    with pytest.raises(SystemExit):
        extract_chunks("/nonexistent/file.pdf")


def test_extract_chunks_all_empty():
    pdf = _make_pdf(["", "", ""])
    try:
        with pytest.raises(SystemExit):
            extract_chunks(pdf)
    finally:
        os.unlink(pdf)


# -- main() integration smoke --

def test_main_help():
    with pytest.raises(SystemExit):
        sys.argv = ["extract.py", "--help"]
        from scripts.extract import main
        main()


def test_main_no_args():
    with pytest.raises(SystemExit):
        sys.argv = ["extract.py"]
        from scripts.extract import main
        main()
