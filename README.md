# The Prompt Index

A living index of **prompt-engineering resources** — curated prompt collections, leaked/published
system prompts, prompt optimizers & tooling, frameworks, and guides — ranked by **momentum**
(stars, push-recency, and how fast a repo is rising) computed from live GitHub signals.

Live: https://prompt-index.vercel.app

## How it works (self-updating)

A daily GitHub Action runs the pipeline and redeploys:

1. `build_data.py` — searches GitHub across several prompt-ecosystem queries, dedupes, filters to
   real prompt resources (precision over recall — drops terminal/shell "prompt" libraries and the
   sibling skill/agent/eval repos), categorizes, scores momentum → `data.json` + SEO files.
2. `gen_details.py` — one SEO'd landing page per resource (`p/<slug>/`) with JSON-LD + breadcrumb.
3. `gen_og.py` — renders the Open Graph card.
4. `deploy.py` — ships the static site to Vercel via the REST API (no CLI).

Static HTML/CSS/JS, no framework. Riso / zine aesthetic (Syne + Space Mono, coral + ink, flat
color blocks).

## Run locally

```bash
GITHUB_TOKEN=... python3 build_data.py
python3 gen_details.py && python3 gen_og.py
python3 -m http.server 8080
```
