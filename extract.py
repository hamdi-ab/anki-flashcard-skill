import sys
import json
import os
from pathlib import Path

try:
    import pymupdf4llm
except ImportError:
    print("pymupdf4llm is required. Install with: pip install pymupdf4llm")
    sys.exit(1)


def extract_chunks(pdf_path: str, chapter: str | None = None) -> list[dict]:
    docs = pymupdf4llm.to_markdown(pdf_path, page_chunks=True, hdr_info=None)
    toc_items = []
    for page in docs:
        toc_items.extend(page.get("toc_items", []))

    target_pages = None
    if chapter and toc_items:
        for level, title, page_num in toc_items:
            if chapter.lower() in title.lower():
                target_pages = page_num
                break
        if target_pages is None:
            print(f"Chapter '{chapter}' not found in table of contents.")
            sys.exit(1)

    skip_log: list[dict] = []
    chunks: list[dict] = []

    for page in docs:
        page_num = page["metadata"]["page_number"]
        if target_pages and page_num != target_pages:
            continue
        text = page.get("text", "").strip()
        if not text:
            continue

        boxes = page.get("page_boxes", [])
        for box in boxes:
            if box.get("type") in ("image", "figure"):
                skip_log.append({"page": page_num, "type": box.get("type"), "bbox": box.get("bbox")})

        chunks.append({
            "page": page_num,
            "text": text,
            "breadcrumb": _breadcrumb(page_num, toc_items),
        })

    if skip_log:
        _write_skip_log(pdf_path, skip_log)

    return _merge_by_heading(chunks, toc_items)


def _breadcrumb(page_num: int, toc_items: list) -> str:
    parts = []
    for level, title, pn in toc_items:
        if pn <= page_num:
            parts.append(title)
    return " > ".join(parts)


def _write_skip_log(pdf_path: str, skip_log: list[dict]) -> None:
    out_dir = Path(pdf_path).parent
    log_path = out_dir / "skipped.log"
    with open(log_path, "w", encoding="utf-8") as f:
        for entry in skip_log:
            f.write(f"page={entry['page']} type={entry['type']} bbox={entry.get('bbox')}\n")
    print(f"Non-text content logged to {log_path}")


def _merge_by_heading(chunks: list[dict], toc_items: list) -> list[dict]:
    if not chunks:
        return chunks
    merged = []
    current = {"breadcrumb": chunks[0]["breadcrumb"], "text": chunks[0]["text"], "pages": [chunks[0]["page"]]}
    for chunk in chunks[1:]:
        if chunk["breadcrumb"] == current["breadcrumb"]:
            current["text"] += "\n\n" + chunk["text"]
            current["pages"].append(chunk["page"])
        else:
            merged.append(current)
            current = {"breadcrumb": chunk["breadcrumb"], "text": chunk["text"], "pages": [chunk["page"]]}
    merged.append(current)
    return merged


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
        print(f"Wrote {chunk_path} — breadcrumb: {chunk['breadcrumb']}, pages: {chunk['pages']}")

    print(f"Total chunks: {len(chunks)}")


if __name__ == "__main__":
    main()
