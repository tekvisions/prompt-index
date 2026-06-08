#!/usr/bin/env python3
"""Generate a static detail page per prompt resource (p/<slug>/index.html) from data.json.
Fully SEO'd (title/meta/canonical/OG + SoftwareSourceCode JSON-LD + breadcrumb). Run after build_data.py."""
from __future__ import annotations

import html
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SITE_URL = "https://prompt.kymatalabs.com"
P_DIR = os.path.join(HERE, "p")


def esc(s) -> str:
    return html.escape(str(s or ""), quote=True)


def ago(iso) -> str:
    from datetime import datetime, timezone
    if not iso:
        return "—"
    try:
        d = (datetime.now(timezone.utc) - datetime.fromisoformat(iso.replace("Z", "+00:00"))).days
    except ValueError:
        return "—"
    return "today" if d < 1 else (f"{d}d ago" if d < 30 else (f"{d // 30}mo ago" if d < 365 else f"{d // 365}y ago"))


def page(it: dict, related: list[dict]) -> str:
    title = f"{it['full_name']} — {it['category']} | The Prompt Index"
    desc = (it["description"] or f"{it['full_name']}, a {it['category']} resource on The Prompt Index.")[:300]
    url = f"{SITE_URL}/p/{it['slug']}/"
    topics = "".join(f'<span class="topic">{esc(t)}</span>' for t in (it.get("topics") or [])[:12])
    rel = "".join(
        f'<a class="card in" href="/p/{esc(r["slug"])}/"><div class="band"></div><div class="card-body">'
        f'<div class="card-top"><span class="num disp">{str(r["rank"]).zfill(2)}</span>'
        f'<span class="cat">{esc(r["category"])}</span></div>'
        f'<div class="name disp">{esc(r["name"])}</div>'
        f'<div class="desc">{esc((r["description"] or "")[:90])}</div></div></a>'
        for r in related)
    ld = {"@context": "https://schema.org", "@type": "SoftwareSourceCode", "name": it["full_name"],
          "description": desc, "url": url, "codeRepository": it["url"],
          "programmingLanguage": it.get("language") or "Markdown",
          "author": {"@type": "Person", "name": it["owner"]}, "license": it.get("license") or ""}
    crumb = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "The Prompt Index", "item": SITE_URL + "/"},
        {"@type": "ListItem", "position": 2, "name": it["full_name"], "item": url}]}
    return f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow">
<meta property="og:type" content="article">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{esc(it['full_name'])} — The Prompt Index">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{SITE_URL}/og.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/style.css">
<script type="application/ld+json">{json.dumps(ld)}</script>
<script type="application/ld+json">{json.dumps(crumb)}</script>
<script>var t;try{{t=localStorage.getItem('pi-theme')}}catch(e){{}}if(t)document.documentElement.setAttribute('data-theme',t);</script>
</head>
<body>
<header><div class="wrap head-row">
  <div class="brand disp"><a href="/" style="text-decoration:none;color:inherit;display:flex;align-items:center;gap:9px"><span class="sq"></span>THE&nbsp;PROMPT&nbsp;INDEX</a></div>
  <div class="head-actions"><a href="/">← All prompts</a><button class="theme-btn" id="theme" aria-label="Toggle theme">◐</button></div>
</div></header>
<main class="wrap detail">
  <div class="crumb"><a href="/">The Prompt Index</a> / {esc(it['category'])} / #{it['rank']}</div>
  <h1 class="disp">{esc(it['full_name'])}</h1>
  <div class="sub">by {esc(it['owner'])} · {esc(it['category'])} · updated {ago(it.get('pushed_at'))}</div>
  <p class="desc-big">{esc(it['description'] or 'No description provided.')}</p>
  <div class="detail-stats">
    <div class="box"><div class="num disp">{it['momentum']}</div><div class="lbl">momentum</div></div>
    <div class="box"><div class="num disp">{it['stars']:,}</div><div class="lbl">stars</div></div>
    <div class="box"><div class="num disp">{it['forks']:,}</div><div class="lbl">forks</div></div>
    <div class="box"><div class="num disp">#{it['rank']}</div><div class="lbl">rank</div></div>
  </div>
  <div class="topics">{topics}</div>
  <a class="cta" href="{esc(it['url'])}" target="_blank" rel="noopener">View on GitHub →</a>
  <div class="related"><h2 class="disp">More in {esc(it['category'])}</h2><div class="grid">{rel}</div></div>
</main>
<footer><div class="wrap foot-row">
  <div class="blurb">The Prompt Index is a self-updating zine, recomputed daily from live GitHub signals.</div>
  <div class="links"><a href="/">All prompts</a><a href="/rss.xml">RSS</a><a href="/sitemap.xml">Sitemap</a></div>
</div></footer>
<script>document.getElementById('theme').addEventListener('click',function(){{var c=document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark';document.documentElement.setAttribute('data-theme',c);try{{localStorage.setItem('pi-theme',c)}}catch(e){{}}}});</script>
</body>
</html>
"""


def main() -> int:
    data = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))
    items = data["items"]
    if os.path.isdir(P_DIR):
        shutil.rmtree(P_DIR)
    os.makedirs(P_DIR, exist_ok=True)
    by_cat: dict[str, list] = {}
    for it in items:
        by_cat.setdefault(it["category"], []).append(it)
    for it in items:
        related = [r for r in by_cat[it["category"]] if r["slug"] != it["slug"]][:4]
        d = os.path.join(P_DIR, it["slug"])
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(page(it, related))
    print(f"generated {len(items)} detail pages in p/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
