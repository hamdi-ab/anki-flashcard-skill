import sys, json, re
from pathlib import Path
from typing import Optional

try:
    import pymupdf
except ImportError:
    print("pymupdf is required. Install with: pip install pymupdf")
    sys.exit(1)

HYPHEN_RE = re.compile(r"(\w+)-\n(\w+)")


def _clean(text: str) -> str:
    while True:
        new = HYPHEN_RE.sub(r"\1\2", text)
        if new == text:
            break
        text = new
    return text


def _detect_no_text(doc) -> bool:
    SAMPLE_PAGES = min(5, doc.page_count)
    total_chars = 0
    for i in range(SAMPLE_PAGES):
        total_chars += len(doc.load_page(i).get_text().strip())
    avg = total_chars / SAMPLE_PAGES
    return avg < 50


COLUMN_GAP = 60  # minimum gap (points) between columns


def _arrange_by_columns(page) -> str:
    text_dict = page.get_text("dict")
    spans: list[tuple[float, float, str]] = []
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                txt = span.get("text", "").strip()
                if txt:
                    bbox = span["bbox"]
                    spans.append((bbox[0], bbox[1], txt))

    if not spans:
        return ""

    x0s = sorted(set(s[0] for s in spans))
    if len(x0s) < 2:
        spans.sort(key=lambda s: (s[1], s[0]))
        return "\n".join(s[2] for s in spans)

    gaps = [x0s[i + 1] - x0s[i] for i in range(len(x0s) - 1)]
    if max(gaps) < COLUMN_GAP:
        spans.sort(key=lambda s: (s[1], s[0]))
        return "\n".join(s[2] for s in spans)

    split = (x0s[0] + x0s[-1]) / 2
    cols: list[list] = [[], []]
    for s in spans:
        cols[0 if s[0] < split else 1].append(s)
    for col in cols:
        col.sort(key=lambda s: (s[1], s[0]))

    return "\n\n".join(
        "\n".join(s[2] for s in col)
        for col in cols if col
    )


def _extract_images_for_pages(
    doc, pages: list[int], output_dir: Path, chunk_id: str
) -> list[str]:
    filenames: list[str] = []
    for page_num in pages:
        page = doc.load_page(page_num - 1)
        img_list = page.get_images(full=True)
        for n, img in enumerate(img_list):
            xref = img[0]
            base = doc.extract_image(xref)
            ext = base["ext"]
            filename = f"{chunk_id}_p{page_num}_img{n}.{ext}"
            img_path = output_dir / filename
            with open(img_path, "wb") as f:
                f.write(base["image"])
            filenames.append(filename)
    return filenames


def extract_chunks(
    pdf_path: str,
    chapter: Optional[str] = None,
    pages_per_chunk: int = 4,
    extract_images: bool = False,
    detect_columns: bool = False,
) -> list[dict]:
    try:
        doc = pymupdf.open(pdf_path)
    except Exception as e:
        print(f"Error: Cannot open PDF — {e}")
        print("The file may be corrupted or not a valid PDF.")
        sys.exit(1)

    if doc.is_encrypted:
        print("Error: PDF is password-protected.")
        print("Open it in a PDF viewer first to remove the password, then retry.")
        sys.exit(1)

    if _detect_no_text(doc):
        print("Warning: The PDF appears to be a scanned document or image-only PDF.")
        print("pymupdf extracts text layer content only. Try OCR tools")
        print("(e.g. OCRmyPDF, Adobe Acrobat OCR) first, then retry.")

    chunks = []
    chapter_started = chapter is None
    current_pages: list[int] = []
    current_texts: list[str] = []
    output_dir = Path(pdf_path).parent

    for i in range(doc.page_count):
        page = doc.load_page(i)
        if detect_columns:
            raw = _arrange_by_columns(page)
        else:
            raw = page.get_text()
        text = _clean(raw).strip()
        if not text:
            continue

        if chapter and not chapter_started:
            if chapter.lower() in text.lower():
                chapter_started = True
            else:
                continue

        current_pages.append(i + 1)
        current_texts.append(text)

        if len(current_pages) >= pages_per_chunk:
            chunk = {
                "breadcrumb": "",
                "text": "\n\n".join(current_texts),
                "pages": list(current_pages),
            }
            chunks.append(chunk)
            current_pages.clear()
            current_texts.clear()

    if current_pages:
        chunk = {
            "breadcrumb": "",
            "text": "\n\n".join(current_texts),
            "pages": list(current_pages),
        }
        chunks.append(chunk)

    if extract_images:
        for n, chunk in enumerate(chunks):
            chunk_id = f"chunk_{n:04d}"
            images = _extract_images_for_pages(doc, chunk["pages"], output_dir, chunk_id)
            if images:
                chunk["images"] = images

    doc.close()

    if chapter and not chapter_started:
        print(f"Chapter '{chapter}' not found in PDF text.")
        # Suggest matching lines from the document
        probe = pymupdf.open(pdf_path)
        candidates: list[str] = []
        seen = set()
        for i in range(probe.page_count):
            for line in probe.load_page(i).get_text().split("\n"):
                stripped = line.strip()
                if not stripped or len(stripped) < 3:
                    continue
                lower = stripped.lower()
                if any(kw in lower for kw in ["chapter", "section", "part "]):
                    key = stripped[:80]
                    if key not in seen:
                        seen.add(key)
                        candidates.append(stripped)
            if len(candidates) >= 10:
                break
        probe.close()
        if candidates:
            print("\nMatching headings found in the document (try one of these):")
            for c in candidates:
                print(f"  --chapter \"{c}\"")
        sys.exit(1)

    if not chunks:
        print("Error: No extractable text found in the PDF.")
        print("The file may be a scanned document (image-only) with no text layer.")
        sys.exit(1)

    return chunks


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path")
    parser.add_argument("--chapter", default=None)
    parser.add_argument("--pages-per-chunk", type=int, default=4)
    parser.add_argument("--extract-images", action="store_true",
                        help="Extract embedded images (figures, diagrams) per page")
    parser.add_argument("--detect-columns", action="store_true",
                        help="Detect multi-column layout and read column by column")
    args = parser.parse_args()

    if args.pages_per_chunk < 1:
        print("--pages-per-chunk must be >= 1")
        sys.exit(1)

    chunks = extract_chunks(
        args.pdf_path, args.chapter, args.pages_per_chunk, args.extract_images,
        args.detect_columns,
    )
    out_dir = Path(args.pdf_path).parent

    for i, chunk in enumerate(chunks):
        chunk_path = out_dir / f"chunk_{i:04d}.json"
        with open(chunk_path, "w", encoding="utf-8") as f:
            json.dump(chunk, f, ensure_ascii=False)
        p = chunk["pages"]
        imgs = chunk.get("images", [])
        img_info = f", {len(imgs)} images" if imgs else ""
        print(f"Wrote {chunk_path} — pages: {p[0]}-{p[-1]} ({len(p)} pp{img_info})")

    print(f"Total chunks: {len(chunks)}")
    print(f"Pages per chunk: {args.pages_per_chunk}")
    if args.extract_images:
        total_images = sum(len(c.get("images", [])) for c in chunks)
        print(f"Total images extracted: {total_images}")


if __name__ == "__main__":
    main()
