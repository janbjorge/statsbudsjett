# Rules for agents

- Read FACTS.md first and keep it true. If it and the code disagree, the code wins; fix the file.
- Check TODO.md before and after work. Move finished items to docs/done.md with the date.
- Log every simplification or judgement call about the numbers in METHOD.md (what is left out, how things are grouped, what a calculation assumes).
- Each fact lives in one file; the others link to it. Do not copy sections between files.

## Numbers

- Every number shown to users comes from a source document, never from memory. Cite the URL and, for PDFs, the page.
- New facts for the "For deg" section go in data/persona/*.json with a verbatim quote. `uv run python -m pipeline.verify` must pass; the build refuses to run otherwise.
- User-facing text is plain bokmål for a general audience. No "kap./post" jargon in headlines.

## Code

- Python 3.14 with uv: deferred annotations (no quoted forward refs), `type` aliases, frozen slotted dataclasses, StrEnum, match.
- Hexagonal layout (FACTS.md §1): `src/core/` stays pure, enforced by tests/test_boundary.py. Pages are rendered on the server with Jinja + HTMX; JavaScript only for chart islands.
- Validation uses pydantic v2 (jb 2026-10-07), in the adapters only: query strings (src/adapters/web/params.py) and API responses (src/adapters/web/api.py). `src/core/` stays standard library and keeps its dataclasses.
- Data work in the pipeline uses polars, not pandas. The app itself does not depend on polars.
- Plain `python3` is a rye shim that fails here; always use `uv run python`.
- Outputs must be deterministic: sort group_by results and round float sums (src/pipeline/flows.py:136).
- JSON goes through orjson, not the standard library `json` (jb 2026-10-08). JSON in the repo is formatted like `jq .` (2-space indent, trailing newline) so diffs show what changed. Write it with `orjson.dumps(..., option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE)`; orjson returns bytes and keeps non-ASCII as is.
- Charts follow the dataviz skill: validated palette, thin marks, legend plus direct labels, hover, table view, light and dark.
- Before commit: `uvx ruff check .`, `uv run ty check src tests`, `uv run pytest tests/<files you touched>`, and `uv run python -m pipeline.verify`. Then run the app and look at it.

## Git and hosting

- The repo is public. No references to the author's employer, its products or customers, or other private projects: not in code, docs, data, commit messages or author metadata.

- Commit to `main`. No force-push.
- `datasets/` is committed; rebuild it (`uv run python -m pipeline.datasets`) when facts or pipeline code change.
- Every push to `main` is checked and deployed to Fly by .github/workflows/deploy.yml, which makes it public. Ask jb before every push.
