# Two-phase pipeline with heading-based chunking

Textbook chapters routinely exceed 50K characters. Sending the full text as a single LLM prompt causes "lost in the middle" degradation (30%+ accuracy drop), high token cost on irrelevant sections, and no partial retry. Heading-based chunking with breadcrumb context solves all three: each section is processed independently within the LLM's attention sweet spot, failed sections can be retried in isolation, and the breadcrumb preserves structural context without exposing irrelevant content.

The pipeline splits into two phases: Python handles PDF extraction and post-processing (deterministic, low-cost), while the LLM handles the transformation task (semantic, pattern-matching). This keeps the script small and the skill prompt-driven.

Chunking decisions evaluated:

- **Fixed-size token chunking** — Rejected: cuts through section boundaries, loses topic coherence, degrades card quality because a single finding description gets split across prompts.
- **Semantic boundary detection** — Rejected: adds 6-18x preprocessing cost for marginal gain on structured textbooks; not worth it when heading hierarchy already exists.
- **Heading-based with breadcrumb** — Selected: matches how textbooks are written, gives each LLM call a coherent topic, preserves hierarchy at negligible cost.

Tool: pymupdf4llm with `page_chunks=True` and `hdr_info=None` for auto heading detection by font size.

Output: tab-separated `.csv` with `#separator:Tab` header directive (avoids colon conflict with `{{c1::}}` cloze syntax).
