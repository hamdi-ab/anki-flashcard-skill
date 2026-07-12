## Problem Statement

Creating high-quality Anki flashcards from medical textbooks is manual and time-consuming. A medical student reads a chapter, identifies key facts, writes cloze deletions and question-answer pairs, formats them for Anki, and hand-checks imports. The bottleneck is the extraction-to-formatting pipeline: the textbook is a PDF, Anki wants structured CSV files, and the transformation in between requires both domain understanding (what's flashcard-worthy) and strict formatting (word limits, cloze syntax, import headers). Current workarounds dump the full PDF text into ChatGPT and hope for the best — which loses structure, misses content in the middle, and produces output that needs manual cleanup before import.

## Solution

A firstmate agent skill that takes a PDF textbook path and optional chapter name, then produces two Anki-ready CSV files — one for cloze cards, one for basic cards — that import cleanly into Anki or AnkiDroid with no manual post-processing.

The skill uses a two-phase pipeline: Python extracts the PDF into heading-aligned chunks, the LLM transforms each chunk into flashcards using domain-tuned prompts, and Python validates and formats the output into tab-separated CSVs with Anki header directives. Non-text content (figures, diagrams, math blocks) is logged rather than silently dropped.

## User Stories

1. As a medical student, I want to run `/anki textbook.pdf` to process a full textbook, so that I get all flashcards in one pass.
2. As a medical student, I want to run `/anki textbook.pdf "Acute Pancreatitis"` to process only one chapter, so that I focus on my current study topic.
3. As a medical student, I want the output split into `cloze_cards.csv` and `basic_cards.csv`, so that I can import them into different Anki note types.
4. As a medical student, I want each CSV to import directly into AnkiDroid without manual editing, so that I save setup time.
5. As a medical student, I want cloze cards to follow my prompt's imaging-focus criteria (1-2 cloze deletions, ≤40 words, standalone), so that the cards are high-quality for board exam review.
6. As a medical student, I want basic cards to follow my prompt's single-concept criteria (≤40 words per question, standalone), so that each card tests exactly one fact.
7. As a medical student, I want a `skipped.log` file listing figures, diagrams, and math blocks that couldn't be extracted, so that I know what content needs manual handling.
8. As a medical student, I want malformed rows written to `errors.csv` instead of silently dropped, so that I can review and fix them.
9. As a medical student, I want the skill to handle multi-column textbook PDFs, so that reading order is preserved in the extracted text.
10. As a medical student, I want the heading hierarchy (chapter → section → subsection) preserved as breadcrumb context in each LLM prompt, so that cards reference their source location.
11. As a medical student, I want the skill to work on a radiology textbook specifically, so that imaging features, differentials, and contrast-enhancement patterns are prioritized in the generated cards.
12. As a medical student, I want the ability to get only cloze cards or only basic cards (not always both), so that I can fill gaps in a specific deck type.

## Implementation Decisions

### Two-phase pipeline

The pipeline splits into a deterministic extraction phase (Python) and a semantic transformation phase (LLM), so that retries, cost, and validation each apply to the right layer.

### Extraction phase

Tool: `pymupdf4llm` with `page_chunks=True` and `hdr_info=None` for auto heading detection by font size.

Chunking strategy: heading-based with breadcrumb context. Each heading-aligned section becomes one chunk. The breadcrumb (e.g., "Chapter 3 > Acute Pancreatitis > Imaging Findings") is prepended to the chunk text before sending to the LLM. This avoids "lost in the middle" degradation and keeps each LLM call within the attention sweet spot.

Non-text detection: figures, diagrams, and embedded math blocks that `pymupdf4llm` cannot extract are written to `skipped.log` with page number and bounding-box coordinates where available.

### Transformation phase

Two prompt templates are built into the skill — one for cloze cards, one for basic cards. Both are tuned for medical/radiology content: prioritize imaging features, unique findings, and differentiating similar entities.

Constraints enforced by prompt:
- ≤40 words per statement/question
- 1-2 cloze deletions per cloze card
- Single concept per basic card
- Standalone (subject included in text)
- Cloze deletions limited to 1-2 key words each

### Validation phase (Python post-processing)

Each row from the LLM is checked before writing to CSV:
- Word count ≤40 → fail rows go to `errors.csv`
- Cloze syntax `{{c1::...}}` must be well-formed (balanced braces) → fail to `errors.csv`
- Duplicate content (exact text match within the same file) → deduplicated, logged
- Row must have the right number of columns for its type (2 for cloze: Text+Extra; 2 for basic: Front+Back) → fail to `errors.csv`

### CSV format

Separator: Tab (avoids colon conflict with `{{c1::}}` cloze syntax).

Headers:
- `#separator:Tab`
- `#html:true` (to support bold, italic, line breaks in cards)
- `#notetype column:1` (first column declares the note type per row)
- `#tags column:3`

Canonical row format:
- Cloze: `Cloze<TAB>{{c1::finding}} is seen in condition<TAB><extra notes><TAB>radiology::pancreas`
- Basic: `Basic<TAB>How is necrotic tissue identified?<TAB>Lack of contrast enhancement<TAB>radiology::pancreas`

### Output files

All written to the PDF's parent directory:
- `cloze_cards.csv` — Cloze note type cards
- `basic_cards.csv` — Basic note type cards
- `errors.csv` — Rows that failed validation (with reason column)
- `skipped.log` — Non-text content that was skipped during extraction

## Testing Decisions

A good test validates external behavior — correct CSV output from known input — without depending on the LLM. The LLM's output quality is governed by the prompt, not by unit tests.

### Post-processing tests (unit, highest seam)

File: `tests/test_postprocess.py`

Fixtures: hand-crafted JSON arrays simulating LLM output (valid rows, over-length rows, malformed cloze syntax, duplicate content, wrong column count).

Tests:
- Valid rows produce correctly formatted CSV with Anki headers
- Over-length rows routed to `errors.csv` with reason "word_count_exceeded"
- Malformed cloze routed to `errors.csv` with reason "invalid_cloze_syntax"
- Duplicates deduplicated and logged
- Empty LLM output produces empty CSV with correct headers
- Mixed valid/invalid rows: valid go to CSV, invalid go to errors

### Extraction tests (unit)

File: `tests/test_extract.py`

Fixtures: small known PDFs (single page, multi-section, with/without headings, with an embedded figure).

Tests:
- Single-section PDF produces exactly one chunk
- Multi-heading PDF produces correct chunk count with breadcrumbs
- Figure on a page is recorded in the skip log (not silently dropped)
- No-heading PDF produces a single preamble chunk

### Integration tests (end-to-end, one smoke test)

File: `tests/test_pipeline.py`

Fixture: a 3-page PDF with two sections and one figure.

Test:
- Full pipeline produces four output files
- Cloze CSV has valid Anki headers
- Basic CSV has valid Anki headers
- Figure is listed in `skipped.log`

## Out of Scope

- Flashcards for non-medical domains (the prompts are tuned for imaging-finding content)
- Image occlusion card generation (diagrams and figures are logged, not turned into cards)
- Anki deck/note type creation (user must have Cloze and Basic note types configured)
- Batch processing multiple textbooks in one invocation
- Support for scanned (non-OCR) PDFs — requires the PDF to have extractable text
- Automated card review or quality scoring beyond syntactic validation
- Generating cards from non-PDF sources (web pages, Word docs, lecture videos)
- AnkiConnect API integration (CSV import is the delivery mechanism)

## Further Notes

- The skill's two prompt templates are embedded in the skill file as markdown blocks so they can be edited without touching Python code.
- The `pymupdf4llm` dependency must be installed in the agent's environment. The skill should check for it at load time and prompt the user to install if missing.
- The post-processing script is designed to be reusable: it takes JSON lines on stdin and writes CSV files, so it can be used outside the skill context for manual LLM-output cleanup.
- Future consideration: adding a `--deck-name` parameter to set the Anki deck header in the CSV, so cards land in the right deck on import.
