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


def extract_chunks(
    pdf_path: str,
    chapter: str | None = None,
    pages_per_chunk: int = 4,
) -> list[dict]:
    doc = pymupdf.open(pdf_path)
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
