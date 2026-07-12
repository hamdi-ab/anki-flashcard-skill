import sys
import csv
import re
import json
from pathlib import Path
from typing import Optional


CLOZE_RE = re.compile(r"\{\{c\d+::.+?\}\}")


def parse_llm_response(jsonl_path: str) -> list[dict]:
    rows = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                rows.append({"raw": line})
    return rows


def validate_cloze(text: str) -> Optional[str]:
    if not CLOZE_RE.search(text):
        return "missing_cloze_syntax"
    for m in CLOZE_RE.finditer(text):
        content = m.group()[len("{{c1::"):-len("}}")]
        if len(content.split()) > 3:
            return "cloze_too_many_words"
    return None


def validate_basic(front: str) -> Optional[str]:
    if len(front.split()) > 40:
        return "word_count_exceeded"
    return None


def word_count(text: str) -> int:
    return len(text.split())


def process_rows(
    rows: list[dict],
    output_dir: Path,
) -> tuple[list[list[str]], list[list[str]], list[list[str]]]:
    cloze_rows: list[list[str]] = []
    basic_rows: list[list[str]] = []
    error_rows: list[list[str]] = []
    seen_texts: set[str] = set()

    for row in rows:
        if "Statements" in row:
            text = row["Statements"]
            card_type = "Cloze"
            issue = validate_cloze(text)
            wc = word_count(text)
        elif "Front" in row and "Back" in row:
            text = row["Front"]
            back = row["Back"]
            card_type = "Basic"
            issue = validate_basic(text)
            wc = word_count(text)
        else:
            error_rows.append([json.dumps(row, ensure_ascii=False), "", "unknown_format"])
            continue

        if issue:
            error_rows.append([card_type, text, issue])
            continue

        if wc > 40:
            error_rows.append([card_type, text, "word_count_exceeded"])
            continue

        dedup_key = text.strip().lower()
        if dedup_key in seen_texts:
            continue
        seen_texts.add(dedup_key)

        if card_type == "Cloze":
            cloze_rows.append([card_type, text, ""])
        else:
            basic_rows.append([card_type, text, back])

    return cloze_rows, basic_rows, error_rows


def write_csv(rows: list[list[str]], path: Path, headers: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        f.write("#separator:Tab\n")
        f.write("#html:true\n")
        f.write("#notetype column:1\n")
        f.write("#tags column:3\n")
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl_path")
    parser.add_argument("--output-dir", default=".")
    args = parser.parse_args()

    rows = parse_llm_response(args.jsonl_path)
    output_dir = Path(args.output_dir)
    cloze, basic, errors = process_rows(rows, output_dir)

    write_csv(cloze, output_dir / "cloze_cards.csv", ["Notetype", "Text", "Tags"])
    write_csv(basic, output_dir / "basic_cards.csv", ["Notetype", "Front", "Back", "Tags"])

    if errors:
        with open(output_dir / "errors.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Type", "Content", "Reason"])
            writer.writerows(errors)

    print(f"Cloze cards: {len(cloze)}")
    print(f"Basic cards: {len(basic)}")
    print(f"Errors: {len(errors)}")


if __name__ == "__main__":
    main()
