import sys, json, re
from pathlib import Path

try:
    import pymupdf
except ImportError:
    print("pymupdf is required. Install with: pip install pymupdf")
    sys.exit(1)

HYPHEN_RE = re.compile(r"(\w+)-\n(\w+)")


def _clean(text: str) -> str:
    return HYPHEN_RE.sub(r"\1\2", text)


def _detect_no_text(doc) -> bool:
    SAMPLE_PAGES = min(5, doc.page_count)
    total_chars = 0
    for i in range(SAMPLE_PAGES):
        total_chars += len(doc.load_page(i).get_text().strip())
    avg = total_chars / SAMPLE_PAGES
    return avg < 50


def extract_chunks(
    pdf_path: str,
    chapter: str | None = None,
    pages_per_chunk: int = 4,
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

    for i in range(doc.page_count):
        page = doc.load_page(i)
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
            chunks.append({
                "breadcrumb": "",
                "text": "\n\n".join(current_texts),
                "pages": list(current_pages),
            })
            current_pages.clear()
            current_texts.clear()

    if current_pages:
        chunks.append({
            "breadcrumb": "",
            "text": "\n\n".join(current_texts),
            "pages": list(current_pages),
        })

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
    args = parser.parse_args()

    if args.pages_per_chunk < 1:
        print("--pages-per-chunk must be >= 1")
        sys.exit(1)

    chunks = extract_chunks(
        args.pdf_path, args.chapter, args.pages_per_chunk
    )
    out_dir = Path(args.pdf_path).parent

    for i, chunk in enumerate(chunks):
        chunk_path = out_dir / f"chunk_{i:04d}.json"
        with open(chunk_path, "w", encoding="utf-8") as f:
            json.dump(chunk, f, ensure_ascii=False)
        p = chunk["pages"]
        print(f"Wrote {chunk_path} — pages: {p[0]}-{p[-1]} ({len(p)} pp)")

    print(f"Total chunks: {len(chunks)}")
    print(f"Pages per chunk: {args.pages_per_chunk}")


if __name__ == "__main__":
    main()
