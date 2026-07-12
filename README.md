# Anki Flashcard

A firstmate skill that dissects textbook PDFs into Anki-ready flashcards. Supports both cloze deletion and basic (front/back) card types, with output CSVs that import directly into Anki or AnkiDroid.

## Install

```sh
npx skills add hamdi-ab/anki-flashcard-skill
pip install pymupdf
```

The repo is public — no GitHub credentials needed beyond what `npx skills` already uses.

For manual install: clone the repo, then symlink or copy the directory into your agent's skill directory (e.g. `~/.agents/skills/`).

## Usage

```
/anki textbook.pdf
/anki textbook.pdf "Acute Pancreatitis"
```

The optional chapter name searches page text — works with or without a table of contents.

## Output

| File | Description |
|---|---|
| `cloze_cards.csv` | Cloze deletion cards for the Cloze note type |
| `basic_cards.csv` | Basic front/back cards for the Basic note type |
| `errors.csv` | Rows that failed validation (word count, syntax, duplicates) |

All CSVs use tab separators with Anki-compatible headers — import directly with no editing.

## Structure

```
anki-flashcard-skill/
├── SKILL.md               # skill file (invoked by /anki)
├── references/
│   ├── CLOZE-PROMPT.md    # cloze card prompt template
│   └── BASIC-PROMPT.md    # basic card prompt template
├── scripts/
│   ├── extract.py         # Phase A: PDF → page chunks
│   └── postprocess.py     # Phase B: validate LLM output → CSVs
└── anki-flashcard-workspace/   # evals, test inputs, iteration results
    ├── evals/inputs/      # test passages and real PDF extracts
    ├── docs/              # domain glossary, spec, ADRs
    └── iteration-*/       # benchmark results
```

## Dependencies

- `pymupdf` — fast, no-OCR PDF text extraction

## Domain

Tuned for medical/radiology content: prioritizes imaging features, unique findings, and methods of differentiating similar disease entities. The prompt templates in `references/` encode those criteria and can be edited for other domains.
