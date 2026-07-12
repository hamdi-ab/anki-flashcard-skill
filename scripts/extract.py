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


def extract_chunks(pdf_path: str, chapter: str | None = None) -> list[dict]:
    doc = pymupdf.open(pdf_path)
    chunks = []
    chapter_started = chapter is None

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

        chunks.append({
            "breadcrumb": "",
            "text": text,
            "pages": [i + 1],
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
    args = parser.parse_args()

    chunks = extract_chunks(args.pdf_path, args.chapter)
    out_dir = Path(args.pdf_path).parent

    for i, chunk in enumerate(chunks):
        chunk_path = out_dir / f"chunk_{i:04d}.json"
        with open(chunk_path, "w", encoding="utf-8") as f:
            json.dump(chunk, f, ensure_ascii=False)
        print(f"Wrote {chunk_path} — pages: {chunk['pages']}")

    print(f"Total chunks: {len(chunks)}")


if __name__ == "__main__":
    main()
