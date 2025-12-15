import json
from pathlib import Path
from util import escape, slugify


ROOT = Path(__file__).resolve().parent.parent
PLAYLISTS_DIR = ROOT / "playlists"
OUT_DIR = ROOT / "out"

OUT_DIR.mkdir(parents=True, exist_ok=True)

playlist_files = [f for f in PLAYLISTS_DIR.glob("*.json") if not f.name.startswith('_')]
AUDIO_EXTS = {".mp3", ".ogg", ".wav"}

OUT_AUDIO_DIR = OUT_DIR / "audio"
OUT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# ---- Generate HTML files ----
index_entries = []

for f in playlist_files:
    with open(f, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    playlist_name = data.get("name", f.stem)
    mp3_tracks = [t for t in data.get("tracks", []) if any(t['url'].lower().endswith(ext) for ext in AUDIO_EXTS) and not t['url'].startswith('http')]
    supports_download = bool(mp3_tracks)
    filename = slugify(playlist_name) + ".html"
    download_file = slugify(playlist_name) + "-download.html" if supports_download else None
    for t in mp3_tracks:
        url = t.get("url")
        src = ROOT / 'audio' / url
        if not src.exists():
            print(f"Warning: audio file not found: {src}")
            continue
        dst = OUT_AUDIO_DIR / src.name
        dst.write_bytes(src.read_bytes())
        print("Copying to", dst)
        t["url"] = f"audio/{src.name}"
    # --- Write HTML ---
    index_entries.append((playlist_name, filename, f.name))
    with (Path(__file__).parent / "player_template.html").open('r', encoding='utf-8') as file:
        html_text = file.read()
    html_text = html_text.replace("{playlist_title}", escape(playlist_name))
    html_text = html_text.replace("{playlist_data}", json.dumps(data, indent=2))
    if supports_download:
        html_text = html_text.replace("{download_link}", f'<p><a href="{download_file}">Herunterladen</a></p>')
        with (Path(__file__).parent / "download_template.html").open('r', encoding='utf-8') as file:
            download_html = file.read()
        download_html = download_html.replace("{playlist_title}", escape(playlist_name))
        download_html = download_html.replace("{playlist_title_filename}", slugify(playlist_name))
        download_html = download_html.replace("{playlist_link}", filename)
        files_and_sources = [{'url': mp3['url'], 'outputName': f"{i:03d} {slugify(mp3['name'])}.mp3"} for i, mp3 in enumerate(mp3_tracks, 1)]
        download_html = download_html.replace('{files_and_sources}', json.dumps(files_and_sources, indent=2))
        items = []
        with (Path(__file__).parent / "download_item_template.html").open('r', encoding='utf-8') as file:
            li_html = file.read()
        for mp3 in mp3_tracks:
            mp3_li = li_html.replace("{name}", mp3['name']).replace("{download_link}", mp3['url'])
            if mp3['source'] is not None:
                mp3_li = mp3_li.replace("{original_href}", f'<a href="{mp3["source"]}" class="original-link" target="_blank">🗗</a>')
            else:
                mp3_li = mp3_li.replace("{original_href}", "")
            items.append(mp3_li)
        download_html = download_html.replace("{items}", "\n".join(items))
        (OUT_DIR / download_file).write_text(download_html, encoding="utf-8")
    else:
        html_text = html_text.replace("{download_link}", "")
    (OUT_DIR / filename).write_text(html_text, encoding="utf-8")
    print("Wrote", filename, download_file)


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
    index_html += f'<li><a href="{file_html}">{escape(title)}</a></li>\n'

index_html += "</ul></body></html>"

(OUT_DIR / "index.html").write_text(index_html, encoding="utf-8")

print("Wrote", OUT_DIR / "index.html")
