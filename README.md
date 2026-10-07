# Statsbudsjettet 2027, forklart

A public explainer of Norway's 2027 state budget proposal. You can see where the money comes from and goes to, what the budget means for you, the numbers for your kommune, and every post in the budget. Built from the government's own published data.

Live at https://budsjettlupa.no. The same data is open as JSON under `/api` (OpenAPI at `/api/openapi.json`), and `/llms.txt` describes the site for AI tools.

Python 3.14, FastAPI, Jinja and HTMX, with d3 only for the charts.

Found a mistake? [Open an issue](https://github.com/janbjorge/statsbudsjett/issues). The page explains how in plain Norwegian (section "Fant du en feil?").

## Run it

```sh
uv run uvicorn adapters.web.main:app --reload     # http://localhost:8000
docker build -t statsbudsjett . && docker run --rm -p 8080:8080 statsbudsjett
```

## Check it

```sh
uvx ruff check .
uv run ty check src tests
uv run pytest -q
uv run python -m pipeline.verify     # needs the sources in data/, so local only
```

## Rebuild the data

```sh
uv run python -m pipeline.download   # fetch sources into data/ (about 140 MB, gitignored)
uv run python -m pipeline.datasets   # verify every fact, then write datasets/
```

## Deploy

Every push to `main` is checked and deployed to Fly by [.github/workflows/deploy.yml](.github/workflows/deploy.yml).

## Docs

- [FACTS.md](FACTS.md): sources, layout, data and numbers. Read first.
- [METHOD.md](METHOD.md): what is left out, how things are grouped, and what calculations assume.
- [TODO.md](TODO.md): open work. Finished work is in [docs/done.md](docs/done.md).
- [AGENTS.md](AGENTS.md): rules for working on the code.
