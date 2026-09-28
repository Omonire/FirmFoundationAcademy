"""
Firm Foundation Academy - page rendering

Serves the seven site pages with the shared header and footer baked in at
render time, so the browser no longer has to fetch() them after the page
has already painted.

The HTML files in the repository root are the source of truth and are not
modified: every transformation here happens on the way out, so the site
still works as plain static files if this app is ever removed.

Run locally:
    pip install -r api/requirements.txt
    python -m api.index

Deploy: see DEPLOY.md
"""

import os
import re
import time
from pathlib import Path

from flask import Flask, abort, request, send_from_directory
from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parent.parent
PAGES_DIR = BASE_DIR


def _load_local_env() -> None:
    """Read a local .env if one exists, tolerating a Windows UTF-8 BOM.

    Notepad and PowerShell both save UTF-8 with a BOM by default, and
    dotenv does not strip it, so the first key would otherwise be read as
    '\\ufeffSUPABASE_URL' and never match. Production gets its values from
    the Vercel environment instead, where this file does not exist.
    """
    for key, value in dotenv_values(PAGES_DIR / ".env").items():
        os.environ.setdefault(key.lstrip("\ufeff"), value or "")


_load_local_env()

app = Flask(__name__, static_folder=None)

# Pages that carry the shared header/footer placeholders.
PAGES = {
    "index": "index.html",
    "about": "about.html",
    "academics": "academics.html",
    "admissions": "admissions.html",
    "gallery": "gallery.html",
    "news": "news.html",
    "contact": "contact.html",
}

# Cheap in-process cache: path -> (mtime, contents). Keeps repeat hits off
# the filesystem without going stale during local editing.
_cache: dict = {}


def read_source(name: str) -> str:
    """Read a repo file, re-reading only when it changes on disk."""
    path = (PAGES_DIR / name).resolve()
    if not path.is_relative_to(PAGES_DIR):
        abort(404)

    try:
        mtime = path.stat().st_mtime
    except OSError:
        abort(404)

    cached = _cache.get(name)
    if cached and cached[0] == mtime:
        return cached[1]

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        abort(500)

    _cache[name] = (mtime, text)
    return text


# Matches the client-side include block: the two fetches, the placeholder
# injection, the active-nav loop, and the trailing icon render. Replaced
# with just the icon render, which still has to run after injection.
_FETCH_BLOCK = re.compile(
    r"const \[headerHTML.*?lucide\.createIcons\(\);",
    re.DOTALL,
)


def mark_active_nav(fragment: str, current: str) -> str:
    """Add the active class server-side, the way loadIncludes() used to."""
    def repl(match: re.Match) -> str:
        tag = match.group(0)
        key = re.search(r'data-nav="([^"]+)"', tag)
        if not key or key.group(1) != current:
            return tag
        return tag.replace(
            'class="', 'class="text-secondary font-bold ', 1
        )

    return re.sub(r"<a\b[^>]*\bdata-nav=\"[^\"]+\"[^>]*>", repl, fragment)


def build_page(page: str) -> str:
    """Return a page with the header and footer already in place."""
    header = read_source("header.html")
    footer = read_source("footer.html")
    html = read_source(PAGES[page])

    header = mark_active_nav(header, page)
    footer = mark_active_nav(footer, page)

    html = html.replace(
        '<div id="header-placeholder"></div>', header, 1
    )
    html = html.replace(
        '<div id="footer-placeholder"></div>', footer, 1
    )

    # Drop the now-redundant client-side fetch of the same two files.
    html, count = _FETCH_BLOCK.subn("lucide.createIcons();", html, count=1)
    if count == 0:
        # Nothing matched: the page is already free of the fetch block.
        # Carry on rather than fail the request.
        app.logger.warning("no include block found in %s", PAGES[page])

    return html


@app.get("/")
def index():
    return build_page("index")


@app.get("/health")
def health():
    """Reports which environment variables arrived. Never returns values."""
    configured = {
        name: bool(os.environ.get(name))
        for name in ("GEMINI_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
    }
    return {
        "status": "ok",
        "env": os.environ.get("FLASK_ENV", "production"),
        "configured": configured,
    }, 200


@app.get("/<page>.html")
def page(page: str):
    if page not in PAGES:
        abort(404)
    return build_page(page)


# Only these may be served as files. Everything else - source, config, and
# anything without a listed extension, notably a local .env, is refused.
ALLOWED_ASSETS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".ico",
    ".webmanifest", ".css", ".js", ".woff", ".woff2", ".ttf", ".otf",
}


@app.get("/<path:filename>")
def asset(filename: str):
    """Serve root-level static files (founder images, logo)."""
    # Refuse dotfiles and nested paths outright: a developer keeping a local
    # .env next to index.html must never be able to publish it.
    if filename.startswith(".") or "/" in filename or "\\" in filename:
        abort(404)
    if Path(filename).suffix.lower() not in ALLOWED_ASSETS:
        abort(404)

    path = (PAGES_DIR / filename).resolve()
    if not path.is_relative_to(PAGES_DIR) or not path.is_file():
        abort(404)
    return send_from_directory(PAGES_DIR, filename)


@app.errorhandler(404)
def not_found(_e):
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Page not found | Firm Foundation Academy</title>"
        "<style>body{font-family:system-ui,-apple-system,'Segoe UI',sans-serif;"
        "background:#0D2420;color:#fff;min-height:100vh;margin:0;"
        "display:flex;align-items:center;justify-content:center;text-align:center}"
        "a{color:#FACC15}</style></head><body><div>"
        "<h1 style='font-size:3rem;margin:0'>404</h1>"
        "<p style='color:#FACC15;letter-spacing:.2em;text-transform:uppercase;"
        "font-size:.75rem'>Page not found</p>"
        "<p>That page does not exist.</p>"
        "<p><a href='/'>Back to home</a></p>"
        "</div></body></html>",
        404,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Debug only when asked. Never expose the debugger in production.
    app.run(host="127.0.0.1", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
