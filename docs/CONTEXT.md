# Anki Flashcard Skill

An agent skill that extracts textbook chapters and generates Anki-ready flashcards (cloze and basic) as CSV files for import.

## Language

**Cloze card**:
A fill-in-the-blank card where one or more key terms are hidden with `{{c1::term}}` markers in a sentence.
_Avoid_: Fill-in-the-blank, cloze deletion card (redundant)

**Basic card**:
A front/back question-and-answer card.
_Avoid_: Q&A card, standard card

**CSV output**:
A tab-separated file with Anki-compatible header directives (`#separator:Tab`, `#notetype:`, `#deck:`) ready for direct import on Anki or AnkiDroid without manual cleanup.
_Avoid_: Just "a file"

**Chunk**:
A contiguous section of the textbook (usually one heading-based subsection) sent as a single prompt to the LLM, with breadcrumb context prepended.
_Avoid_: Page, document segment

**Breadcrumb**:
The hierarchical section path prepended to each chunk (e.g., "Chapter 3 > Acute Pancreatitis > Imaging Findings") so the LLM retains structural context without seeing the full document.

**Extraction pipeline**:
Phase A: Python script reads PDF via pymupdf4llm → heading-based chunking → LLM prompt per chunk. Phase B: Python validates LLM output → splits into cloze/basic CSVs → applies Anki headers.
_Avoid_: Just "the script"

**Validation gate**:
Python-side checks each LLM-generated row for word count ≤40, well-formed cloze syntax (`{{c1::...}}`), and non-duplicate content. Malformed rows are written to a separate error file.
_Avoid_: Quality check

**Skip log**:
A file listing non-text content (figures, diagrams, math blocks) that the pipeline could not process. Written during Phase A extraction, surfaced to the user after completion.

## Invocation

Formal slash command:
- `/anki textbook.pdf` — processes full book, both cloze and basic cards
- `/anki textbook.pdf "Ch 3"` — processes only that chapter, both card types

## Pipeline

Phase A (Python): pymupdf4llm → heading-based chunking (one section = one LLM call) → write skip log for non-text content.

Phase B (Python): validate LLM output → split cloze/basic → apply Anki headers → `cloze_cards.csv` + `basic_cards.csv` + `errors.csv` + `skipped.log`
