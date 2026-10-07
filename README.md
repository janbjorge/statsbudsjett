# Statsbudsjettet 2027, forklart

A public explainer of Norway's 2027 state budget proposal. You can see where the money comes from and goes to, what the budget means for you, the numbers for your kommune, and every post in the budget. Built from the government's own published data.

## Run it

```sh
uv run python -m http.server 8000 --directory site    # http://localhost:8000
docker build -t statsbudsjett . && docker run --rm -p 8080:8080 statsbudsjett
```

## Rebuild it

```sh
uv run python download.py      # fetch sources into data/ (about 140 MB, gitignored)
uv run python viz/build.py     # Sankey page
uv run python viz/explorer.py  # explorer; verifies every fact first, writes site/
```

## Docs

- [FACTS.md](FACTS.md): sources, data layout and numbers. Read first.
- [METHOD.md](METHOD.md): what is left out, how things are grouped, and what calculations assume.
- [TODO.md](TODO.md): open work. Finished work is in [docs/done.md](docs/done.md).
- [AGENTS.md](AGENTS.md): rules for working on the code.
