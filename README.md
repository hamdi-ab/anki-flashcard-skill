# Anki Flashcard

A firstmate skill that dissects textbook PDFs into Anki-ready flashcards. Supports both cloze deletion and basic (front/back) card types, with output CSVs that import directly into Anki or AnkiDroid.

## Install

```sh
git clone https://github.com/hamdi-ab/anki-flashcard-skill.git
pip install pymupdf
```

Symlink or copy the `anki-flashcard-skill` directory into your agent's skill directory (e.g. `~/.agents/skills/` or `~/.claude/skills/`), then invoke via `/anki`.

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
