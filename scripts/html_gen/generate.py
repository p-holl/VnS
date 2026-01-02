import json
from pathlib import Path

from html_gen.util import escape, slugify


def generate_playlist_html(PLAYLISTS_DIR, OUT_DIR):
    playlist_files = [f for f in PLAYLISTS_DIR.glob("*.json") if not f.name.startswith('_')]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ---- Generate HTML files ----
    index_entries = []
    for f in playlist_files:
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        for track in data.get("tracks", []):
            if 'full' not in track:
                track['full'] = track['name']
        playlist_name = data.get("name", f.stem)
        audio_out_dir = OUT_DIR / "audio" / slugify(playlist_name)
        audio_out_dir.mkdir(parents=True, exist_ok=True)
        mp3_tracks = [t for t in data.get("tracks", []) if t['url'].lower().endswith('.mp3') and not t['url'].startswith('http')]
        supports_download = bool(mp3_tracks)
        filename = slugify(playlist_name) + ".html"
        download_file = slugify(playlist_name) + "-download.html" if supports_download else None
        for t in mp3_tracks:
            url = t.get("url")
            t["url"] = f"audio/{slugify(playlist_name)}/{url}"
        # --- Write HTML ---
        index_entries.append((playlist_name, filename, f.name))
        with (Path(__file__).parent / "player_template.html").open('r', encoding='utf-8') as file:
            html_text = file.read()
        html_text = html_text.replace("{playlist_title}", escape(playlist_name))
        html_text = html_text.replace("{playlist_data}", json.dumps(data, indent=2))
        if supports_download:
            html_text = html_text.replace("{download_link}", f"""
<a href="{download_file}" class="download-button" aria-label="Download">
    <svg class="download-icon" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
      <polyline points="7 10 12 15 17 10"></polyline>
      <line x1="12" y1="15" x2="12" y2="3"></line>
    </svg>
</a>
""")#f'<a href="{download_file}" class="download-href">Herunterladen</a>')
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
                    mp3_li = mp3_li.replace("{original_href}", f'<a href="{mp3["source"]}" class="original-link" target="_blank">↗</a>')
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
    with (Path(__file__).parent / "index_template.html").open('r', encoding='utf-8') as file:
        index_html = file.read()
    index_contents = ""
    for title, file_html, fname in index_entries:
        index_contents += f'<li><a href="{file_html}">{escape(title)}</a></li>\n'
    index_html = index_html.replace("{playlists}", index_contents)

    (OUT_DIR / "index.html").write_text(index_html, encoding="utf-8")

    print("Wrote", OUT_DIR / "index.html")


if __name__ == '__main__':
    ROOT = Path(__file__).resolve().parent.parent.parent
    generate_playlist_html(ROOT / "playlists", ROOT / "docs")
