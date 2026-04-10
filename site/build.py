"""
Static site generator for the Signal Microblog.
Reads posts/*.md → renders HTML → writes to public/

Run:  python site/build.py
Deps: pip install markdown jinja2 pyyaml
"""

import re
import shutil
from pathlib import Path
from datetime import datetime

import yaml
import markdown as mdlib
from jinja2 import Environment, FileSystemLoader, select_autoescape

# ---------------------------------------------------------------------------
# Paths (relative to repo root)
# ---------------------------------------------------------------------------
POSTS_DIR     = Path("posts")
OUTPUT_DIR    = Path("public")
TEMPLATES_DIR = Path("site/templates")
STATIC_DIR    = Path("site/static")

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


# ---------------------------------------------------------------------------
# Post parsing
# ---------------------------------------------------------------------------

def parse_post(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")

    fm: dict = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                pass
            body = parts[2].strip()

    # Parse date
    raw_date = fm.get("date", "")
    try:
        dt = datetime.fromisoformat(str(raw_date).strip('"'))
    except (ValueError, TypeError):
        dt = datetime.now()

    # Render markdown body
    html_body = mdlib.markdown(
        body,
        extensions=["nl2br", "extra", "sane_lists"],
    )

    return {
        "slug":         path.stem,
        "date":         dt,
        "date_display": _format_date(dt),
        "date_iso":     dt.isoformat(),
        "type":         fm.get("type", "note"),
        "title":        fm.get("title", ""),
        "images":       fm.get("images") or [],
        "body":         html_body,
    }


def _format_date(dt: datetime) -> str:
    """Human-friendly date: 'April 10, 2026 · 14:23'"""
    return dt.strftime("%-d %B %Y · %H:%M")


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build():
    # Clean and recreate output dir
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    # Copy static assets
    if STATIC_DIR.exists():
        shutil.copytree(STATIC_DIR, OUTPUT_DIR / "static")

    # Copy images
    images_src = POSTS_DIR / "images"
    if images_src.exists():
        shutil.copytree(images_src, OUTPUT_DIR / "images")

    # Parse all posts, newest first
    posts = []
    if POSTS_DIR.exists():
        for md_path in sorted(POSTS_DIR.glob("*.md"), reverse=True):
            post = parse_post(md_path)
            if post:
                posts.append(post)

    # Index page
    (OUTPUT_DIR / "index.html").write_text(
        env.get_template("index.html").render(posts=posts),
        encoding="utf-8",
    )

    # Individual post pages
    post_dir = OUTPUT_DIR / "post"
    post_dir.mkdir()
    for post in posts:
        (post_dir / f"{post['slug']}.html").write_text(
            env.get_template("post.html").render(post=post),
            encoding="utf-8",
        )

    print(f"✓ Built {len(posts)} posts → {OUTPUT_DIR}/")


if __name__ == "__main__":
    build()
