import json, os, sys, tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.extract import _clean, _detect_no_text, _extract_images_for_pages, extract_chunks


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


def test_clean_leaves_non_hyphenated_breaks():
    assert _clean("regular word\nwrapping") == "regular word\nwrapping"


def test_clean_empty():
    assert _clean("") == ""


def test_clean_whitespace_only():
    assert _clean("   ") == "   "


def test_clean_leading_trailing_spaces():
    assert _clean("  nec-\nrosis  ") == "  necrosis  "


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


def test_detect_no_text_boundary():
    text = " ".join(["word"] * 50)
    pdf = _make_pdf([text] * 5)
    try:
        import pymupdf
        doc = pymupdf.open(pdf)
        assert _detect_no_text(doc) is False
        doc.close()
    finally:
        os.unlink(pdf)


def test_detect_no_text_figure_heavy():
    pdf = _make_pdf(["Fig 1.", "Fig 2.", "Caption short"] * 5)
    try:
        import pymupdf
        doc = pymupdf.open(pdf)
        assert _detect_no_text(doc) is True
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


def test_extract_chunks_special_chars():
    text = "élévation des niveaux de créatinine sérique"
    pdf = _make_pdf([text] * 4)
    try:
        chunks = extract_chunks(pdf, pages_per_chunk=4)
        assert len(chunks) == 1
        assert "élévation" in chunks[0]["text"]
        assert chunks[0]["pages"] == [1, 2, 3, 4]
    finally:
        os.unlink(pdf)


def test_extract_chunks_all_text_no_skip():
    pdf = _make_pdf(["Page A", "Page B", "Page C"])
    try:
        chunks = extract_chunks(pdf, pages_per_chunk=2)
        assert len(chunks) == 2
        assert chunks[0]["pages"] == [1, 2]
        assert chunks[1]["pages"] == [3]
    finally:
        os.unlink(pdf)


def test_extract_chunks_uneven_one_per_page():
    pdf = _make_pdf(["one", "two", "three", "four", "five"])
    try:
        chunks = extract_chunks(pdf, pages_per_chunk=1)
        assert len(chunks) == 5
        assert chunks[0]["pages"] == [1]
        assert chunks[4]["pages"] == [5]
        assert "five" in chunks[4]["text"]
    finally:
        os.unlink(pdf)


def test_extract_chunks_large_grouping():
    pdf = _make_pdf([f"page {i+1}" for i in range(3)])
    try:
        chunks = extract_chunks(pdf, pages_per_chunk=100)
        assert len(chunks) == 1
        assert chunks[0]["pages"] == [1, 2, 3]
    finally:
        os.unlink(pdf)


def test_extract_chunks_single_page():
    pdf = _make_pdf(["only one page"])
    try:
        chunks = extract_chunks(pdf, pages_per_chunk=4)
        assert len(chunks) == 1
        assert chunks[0]["pages"] == [1]
    finally:
        os.unlink(pdf)


# -- image extraction --

def _make_png_pixel(w: int, h: int, r: int, g: int, b: int) -> bytes:
    import struct, zlib
    def chunk(ctype, data):
        c = ctype + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
    raw = b""
    for _ in range(h):
        raw += b"\x00" + bytes([r, g, b]) * w
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _make_pdf_with_images(pages: list[list[bytes]]) -> str:
    import pymupdf
    doc = pymupdf.open()
    for imgs in pages:
        page = doc.new_page()
        page.insert_text((50, 50), "text with image", fontsize=12)
        for n, img_data in enumerate(imgs):
            x = 100 + n * 80
            page.insert_image(pymupdf.Rect(x, 100, x + 50, 150), stream=img_data)
    path = os.path.join(tempfile.gettempdir(), f"test_{os.urandom(4).hex()}.pdf")
    doc.save(path)
    doc.close()
    return path


def test_extract_images_from_chunk():
    red = _make_png_pixel(10, 10, 255, 0, 0)
    blue = _make_png_pixel(10, 10, 0, 0, 255)
    pdf = _make_pdf_with_images([[red], [blue]])
    try:
        chunks = extract_chunks(pdf, pages_per_chunk=1, extract_images=True)
        assert len(chunks) == 2
        assert "images" in chunks[0]
        assert "images" in chunks[1]
        assert len(chunks[0]["images"]) == 1
        assert len(chunks[1]["images"]) == 1
        assert chunks[0]["images"][0].endswith(".png")
        for c in chunks:
            for img_name in c["images"]:
                img_path = Path(pdf).parent / img_name
                assert img_path.exists()
                img_path.unlink()
    finally:
        os.unlink(pdf)


def test_extract_images_no_images_flag():
    pdf = _make_pdf(["just text", "more text"])
    try:
        chunks = extract_chunks(pdf, pages_per_chunk=1)
        assert len(chunks) == 2
        assert "images" not in chunks[0]
    finally:
        os.unlink(pdf)


def test_extract_images_no_embedded_images():
    pdf = _make_pdf(["page with no images", "also none"])
    try:
        chunks = extract_chunks(pdf, pages_per_chunk=1, extract_images=True)
        assert len(chunks) == 2
        for c in chunks:
            imgs = c.get("images", [])
            assert len(imgs) == 0
    finally:
        os.unlink(pdf)


def test_extract_images_multiple_per_page():
    red = _make_png_pixel(10, 10, 255, 0, 0)
    green = _make_png_pixel(10, 10, 0, 255, 0)
    blue = _make_png_pixel(10, 10, 0, 0, 255)
    pdf = _make_pdf_with_images([[red, green, blue]])
    try:
        chunks = extract_chunks(pdf, pages_per_chunk=1, extract_images=True)
        assert len(chunks) == 1
        assert len(chunks[0]["images"]) == 3
        for img_name in chunks[0]["images"]:
            img_path = Path(pdf).parent / img_name
            assert img_path.exists()
            img_path.unlink()
    finally:
        os.unlink(pdf)


def test_extract_images_with_main_flag():
    red = _make_png_pixel(10, 10, 255, 0, 0)
    pdf = _make_pdf_with_images([[red]])
    try:
        sys.argv = ["extract.py", pdf, "--extract-images"]
        from scripts.extract import main
        main()
        chunks = list(Path(pdf).parent.glob("chunk_*.json"))
        assert len(chunks) == 1
        data = json.loads(chunks[0].read_text(encoding="utf-8"))
        assert "images" in data
        assert len(data["images"]) == 1
        for cf in chunks:
            cf.unlink()
        for img_name in data["images"]:
            (Path(pdf).parent / img_name).unlink()
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


def test_main_with_real_pdf():
    pages = ["Page one content", "Page two content", "Page three content"]
    pdf = _make_pdf(pages)
    try:
        sys.argv = ["extract.py", pdf, "--pages-per-chunk", "2"]
        from scripts.extract import main
        main()
        parent = Path(pdf).parent
        chunk_files = list(parent.glob("chunk_*.json"))
        assert len(chunk_files) == 2
        for cf in chunk_files:
            cf.unlink()
    finally:
        os.unlink(pdf)
