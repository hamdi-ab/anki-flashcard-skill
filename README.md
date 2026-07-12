# Anki Flashcard

A firstmate skill that dissects textbook PDFs into Anki-ready flashcards. Supports both cloze deletion and basic (front/back) card types, with output CSVs that import directly into Anki or AnkiDroid.

## Usage

```
/anki textbook.pdf
/anki textbook.pdf "Chapter 3 - Acute Pancreatitis"
```

## Output

| File | Description |
|---|---|
| `cloze_cards.csv` | Cloze deletion cards for the Cloze note type |
| `basic_cards.csv` | Basic front/back cards for the Basic note type |
| `errors.csv` | Rows that failed validation (word count, syntax, duplicates) |
| `skipped.log` | Non-text content skipped during extraction (figures, diagrams) |

All CSVs use tab separators with Anki-compatible headers — import directly with no editing.

## Structure

```
anki-flashcard-skill/
├── SKILL.md               # skill file
├── CLOZE-PROMPT.md        # cloze card prompt template
├── BASIC-PROMPT.md        # basic card prompt template
├── scripts/
│   ├── extract.py         # Phase A: PDF → heading-aligned chunks
│   └── postprocess.py     # Phase B: validate LLM output → CSVs
└── docs/
    ├── CONTEXT.md          # domain glossary
    ├── spec.md             # full spec
    └── adr/
        └── 0001-two-phase-pipeline-with-heading-chunking.md
```

## Dependencies

- `pymupdf4llm` — PDF extraction with heading preservation

## Domain

This skill is tuned for medical/radiology content: it prioritizes imaging features, unique findings, and methods of differentiating similar disease entities. The prompt templates in `CLOZE-PROMPT.md` and `BASIC-PROMPT.md` encode those criteria and can be edited for other domains.
