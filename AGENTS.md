# Rules for agents

- Read FACTS.md first and keep it true. If it and the code disagree, the code wins; fix the file.
- Check TODO.md before and after work. Move finished items to docs/done.md with the date.
- Log every simplification or judgement call about the numbers in METHOD.md (what is left out, how things are grouped, what a calculation assumes).
- Each fact lives in one file; the others link to it. Do not copy sections between files.

## Numbers

- Every number shown to users comes from a source document, never from memory. Cite the URL and, for PDFs, the page.
- New facts for the "For deg" section go in data/persona/*.json with a verbatim quote. `uv run python viz/verify_persona.py` must pass; the build refuses to run otherwise.
- User-facing text is plain bokmål for a general audience. No "kap./post" jargon in headlines.

## Code

- Python 3.14 with uv. Data work in polars, not pandas.
- Plain `python3` is a rye shim that fails here; always use `uv run python`.
- Outputs must be deterministic: sort group_by results and round float sums (viz/build.py:139).
- Charts follow the dataviz skill: validated palette, thin marks, legend plus direct labels, hover, table view, light and dark.
- Before commit: `uvx ruff check .` and `uv run python viz/verify_persona.py`, then rebuild and look at the page.

## Git and hosting

- The repo is public. No references to the author's employer, its products or customers, or other private projects: not in code, docs, data, commit messages or author metadata.

- Commit to `main`. No force-push.
- `site/` is the deployable output and is committed; rebuild it before committing changes to viz/.
- Deploying to Fly makes the page public. Ask jb first, every time.
