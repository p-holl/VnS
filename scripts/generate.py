import json
from pathlib import Path
from util import escape, slugify


ROOT = Path(__file__).resolve().parent.parent
PLAYLISTS_DIR = ROOT / "playlists"
OUT_DIR = ROOT / "out"

OUT_DIR.mkdir(parents=True, exist_ok=True)

# Read playlists
playlist_files = [f for f in PLAYLISTS_DIR.glob("*.json")]

if not playlist_files:
    print("No playlist JSON files found in playlists/, nothing to do.")
    exit(0)


AUDIO_EXTS = {".mp3", ".ogg", ".wav"}

def is_audio_url(url: str) -> bool:
    return any(url.lower().endswith(ext) for ext in AUDIO_EXTS)

def is_remote_url(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")


OUT_AUDIO_DIR = OUT_DIR / "audio"
OUT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


# ---- Generate HTML files ----

index_entries = []

for f in playlist_files:
    with open(f, "r", encoding="utf-8") as fp:
        try:
            data = json.load(fp)
        except Exception as e:
            print(f"Skipping invalid JSON: {f} ({e})")
            continue

    for t in data.get("tracks", []):
        url = t.get("url")
        if not url or not is_audio_url(url):
            continue
        # Skip remote audio
        if is_remote_url(url):
            continue
        src = ROOT / 'audio' / url
        if not src.exists():
            print(f"Warning: audio file not found: {src}")
            continue
        dst = OUT_AUDIO_DIR / src.name
        dst.write_bytes(src.read_bytes())
        # Rewrite URL for the generated HTML
        t["url"] = f"audio/{src.name}"
        print("Copying to", dst)

    playlist_name = data.get("name", f.stem)
    filename = slugify(playlist_name) + ".html"
    outpath = OUT_DIR / filename

    with (Path(__file__).parent / "player_template.html").open('r', encoding='utf-8') as file:
        html_text = file.read()
    html_text = html_text.replace("{playlist_title}", escape(playlist_name))
    html_text = html_text.replace("{playlist_data}", json.dumps(data, indent=2))
    outpath.write_text(html_text, encoding="utf-8")

    print("Wrote", outpath)
    index_entries.append((playlist_name, filename, f.name))


# ---- Build index.html ----

index_html = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vibe & Seek — Playlists</title>
<style>
body{font-family:system-ui,Segoe UI,Roboto;padding:24px;background:#071227;color:#e6eef7}
a{color:#7c4dff}
</style>
</head><body>
<h1>Vibe &amp; Seek — Playlists</h1>
<ul>
"""
for title, file_html, fname in index_entries:
    index_html += f'<li><a href="{file_html}">{escape(title)}</a> — {escape(fname)}</li>\n'

index_html += "</ul></body></html>"

(OUT_DIR / "index.html").write_text(index_html, encoding="utf-8")

print("Wrote", OUT_DIR / "index.html")
