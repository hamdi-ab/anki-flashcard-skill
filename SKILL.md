---
name: anki-flashcard
description: Dissects a textbook PDF into Anki-ready flashcards. Use when the user invokes /anki or asks to turn a textbook into Anki cards.
disable-model-invocation: true
---

# Anki Flashcard

User-invoked via `/anki`. Dissects a textbook PDF into Anki-ready flashcards.

## Dissect

Dissect is the leading word. The agent dissects the textbook: slices it along natural section boundaries, examines each section for high-yield facts, and plates those facts onto flashcards. Every pass is a dissection pass — deliberate, focused, leaving nothing that belongs on a card behind.

## Steps

### 1. Ready the specimen

Check that the PDF path exists. Check that `pymupdf4llm` is importable. If a chapter name was given, confirm it appears in the PDF's table of contents.

_Completion criterion_: PDF exists, dependency is importable, and the chapter is locatable (or omitted for full-book mode). Stop with a clear error if any check fails.

### 2. Slice

Run `scripts/extract.py <pdf-path> [--chapter "<title>"]`. This produces one `.chunk` file per heading-aligned section and a `skipped.log` for non-text content.

Read `skipped.log`. If non-empty, tell the user which pages had figures, diagrams, or math blocks that were skipped.

_Completion criterion_: Chunk files and `skipped.log` exist. User knows about skipped content.

### 3. Examine

For each chunk file, load the prompt template from [`CLOZE-PROMPT.md`](./CLOZE-PROMPT.md) or [`BASIC-PROMPT.md`](./BASIC-PROMPT.md), inject the chunk text into the `{TEXT}` placeholder, and send to the LLM. Collect all responses into a single JSON-lines file.

_Completion criterion_: Every chunk produced a response. No chunk was skipped.

### 4. Plate

Run `scripts/postprocess.py <responses.jsonl> --output-dir <pdf-dir>`. This validates each row (word count, cloze syntax, duplicates), splits cloze from basic cards, and writes `cloze_cards.csv`, `basic_cards.csv`, `errors.csv`.

Check `errors.csv`. If non-empty, tell the user how many rows failed and why.

_Completion criterion_: All four output files exist. User knows how many rows passed and failed.

### 5. Present

Report to the user:
- Cloze card count
- Basic card count
- Error count
- Paths to all output files
- Path to `skipped.log` (if non-empty)

_Completion criterion_: User has everything they need to import into Anki.
