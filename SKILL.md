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

Check that the PDF path exists. Check that `pymupdf` is importable. If a chapter name was given, note that the script searches for it in the page text (some PDFs lack a table of contents).

**Edge cases the script handles automatically:**
- **Corrupted PDF** — prints an error and exits; relay the error verbatim.
- **Password-protected PDF** — prints an error asking the user to open and save without the password first; relay the instruction.
- **Scanned / image-only PDF** — prints a warning that no text layer was found and suggests OCR; relay the suggestion. The script continues in case some pages have text, but expect few or no cards.
- **Chapter not found** — prints an error listing available chapter-like headings found in the text (up to 10), so the user can pick the right one.

_Completion criterion_: PDF exists and dependency is importable. Stop with a clear error if either check fails. Relay edge-case messages to the user.

### 2. Slice

Run `scripts/extract.py <pdf-path> [--chapter "<title>"] [--pages-per-chunk <N>]`. This groups consecutive pages into chunk files and cleans hyphenated line breaks common in PDF text extraction.

Default grouping is 4 pages per chunk. Smaller numbers (1-2) give the LLM less context per pass but finer granularity for noise-skipping. Larger numbers (6-10) give more context and can produce more cards per chunk. When the user specified a card count, you may adjust `--pages-per-chunk` to roughly hit the total: e.g. for 50 cards with default 10-20 per chunk, aim for 3-5 chunks → `--pages-per-chunk ceil(total_pages / 4)`.

Read the chunks quickly. If a chunk contains mostly sidebar noise (a repeated outline, advertisement, blank page), skip it in step 3.

_Completion criterion_: Chunk files exist.

### 3. Examine

**Resolve the card count target.** Decide `TARGET`:

- If the user specified a number of cards (e.g. `/anki book.pdf 50 cards` or `--cards 50`), compute:  
  `target_per_chunk = ceil(N / num_chunks)`.  
  Clamp to a reasonable range (min 5, max 40).
- If the user did not specify a count, use `"10-20"` as the default.

**For each chunk file:**
1. **Inventory topics.** Read the chunk text and list 3-8 key concepts/findings in it (e.g. for a radiology page about pancreatitis: necrosis, fluid collections, pseudocysts, abscess, calcifications, ductal dilation). This inventory is your coverage checklist.
2. **Generate cards.** Load the prompt template from [`references/CLOZE-PROMPT.md`](./references/CLOZE-PROMPT.md) or [`references/BASIC-PROMPT.md`](./references/BASIC-PROMPT.md). Replace `{TEXT}` with the chunk text and `{TARGET}` with the resolved target (e.g. `12` or `10-20`). Send to the LLM.
3. **Check coverage.** Compare the generated cards against your topic inventory. If an entire topic is missing, send a targeted follow-up to the LLM: `"You covered X and Y but missed Z. Generate cards for Z."`
4. **Reject trivial clozes.** If a cloze hides a generic word (not, is, most, first, common) or a term obvious from surrounding context, reject that card and ask the LLM to replace the target with a discriminating term.

Collect all responses into a single JSON-lines file.

Some chunks contain sidebar noise (a repeated chapter outline, page numbers, headers or footers). The LLM handles this naturally — it will extract real facts and ignore boilerplate. No need to strip it manually.

_Completion criterion_: Every chunk produced a response. No chunk was skipped. No trivial clozes survived to output. Every topic identified in the inventory has at least one card.

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

_Completion criterion_: User has everything they need to import into Anki.
