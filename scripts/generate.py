import json
import os
import re
from pathlib import Path
import html

ROOT = Path(__file__).resolve().parent.parent
PLAYLISTS_DIR = ROOT / "playlists"
OUT_DIR = ROOT / "out"

OUT_DIR.mkdir(parents=True, exist_ok=True)


def slugify(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = re.sub(r"^-|-$", "", name)
    return name


def escape(s: str) -> str:
    return html.escape(s, quote=True)


# Read playlists
playlist_files = [f for f in PLAYLISTS_DIR.glob("*.json")]

if not playlist_files:
    print("No playlist JSON files found in playlists/, nothing to do.")
    exit(0)


def build_html(playlist_data: dict, playlist_title: str) -> str:
    """
    Inserts the playlist JSON into the full single-file HTML page.
    """

    # ---- INLINE HTML TEMPLATE ----
    # (Identical to the Node version, but injected via Python)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Vibe &amp; Seek — {escape(playlist_title)}</title>
<style>
  :root{{
    --bg:#0f1724; --card:#0b1220; --muted:#9aa4b2; --accent:#7c4dff; --text:#e6eef7;
  }}
  html,body{{height:100%;margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial;}}
  body{{background:linear-gradient(180deg,#071227 0%, #0b1726 100%);color:var(--text);display:flex;align-items:flex-start;justify-content:center;padding:28px;}}
  .container{{width:100%;max-width:980px;}}
  header{{display:flex;align-items:center;gap:16px;margin-bottom:18px}}
  h1{{margin:0;font-size:20px;letter-spacing:0.2px}}
  .subtitle{{color:var(--muted);font-size:13px;margin-top:4px}}
  .card{{background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));border-radius:12px;padding:14px;box-shadow:0 6px 20px rgba(2,6,23,0.6)}}
  .player-row{{display:flex;gap:14px;align-items:center}}
  .video-wrap{{flex:0 0 500px;height:80px;max-width:100%}}
  .video-wrap iframe{{width:100%;height:100%;border-radius:8px;border:0;background:#000}}
  .controls{{flex:1;display:flex;flex-direction:column;gap:10px}}
  .big-controls{{display:flex;gap:10px;align-items:center}}
  button{{background:transparent;border:1px solid rgba(255,255,255,0.06);color:var(--text);padding:8px 12px;border-radius:8px;cursor:pointer}}
  button.primary{{background:linear-gradient(90deg,var(--accent),#00c4ff);border:none;color:#071227;font-weight:600}}
  .track-list{{margin-top:14px;display:flex;gap:12px}}
  .list{{background:rgba(255,255,255,0.02);border-radius:10px;padding:10px;flex:1;max-height:360px;overflow:auto}}
  .track{{padding:10px;border-radius:8px;display:flex;gap:12px;align-items:center;cursor:pointer}}
  .track:hover{{background:rgba(255,255,255,0.02)}}
  .track .idx{{width:28px;text-align:center;color:var(--muted);font-size:13px}}
  .track .title{{font-size:14px}}
  .track.active{{background:linear-gradient(90deg, rgba(124,77,255,0.12), rgba(0,196,255,0.06));box-shadow:0 4px 14px rgba(12,8,32,0.6)}}
  footer{{margin-top:10px;color:var(--muted);font-size:13px}}
  @media (max-width:640px){{
    .player-row{{flex-direction:column;align-items:stretch}}
    .video-wrap{{height:64px;flex-basis:auto}}
    .controls{{order:2}}
  }}
</style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>Vibe &amp; Seek</h1>
        <div class="subtitle">{escape(playlist_title)}</div>
      </div>
    </header>

    <div class="card">
      <div class="player-row">
        <div class="video-wrap" id="video-wrap">
          <div id="player-container"></div>
        </div>
        <div class="controls">
          <div class="big-controls">
            <button id="prevBtn">⟵ Prev</button>
            <button id="playBtn" class="primary">Play</button>
            <button id="nextBtn">Next ⟶</button>
            <div style="margin-left:auto;color:var(--muted);font-size:13px" id="timeLabel">—</div>
          </div>
          <div class="track-list">
            <div class="list" id="trackList"></div>
          </div>
        </div>
      </div>
    </div>

    <footer>Built with the YouTube IFrame API — playback respects user settings and ads.</footer>
  </div>

<script>
const PLAYLIST = {json.dumps(playlist_data, indent=2)};

function idFromUrl(url){{
  try {{
    const u = new URL(url);
    if (u.hostname.includes('youtu.be')) return u.pathname.slice(1);
    if (u.searchParams.get('v')) return u.searchParams.get('v');
  }} catch(e){{}}
  const m = url.match(/(?:v=|youtu\\.be\\/)([A-Za-z0-9_-]{{6,}})/);
  return m ? m[1] : null;
}}

function formatTime(s){{
  if (s == null) return '—';
  s = Math.floor(s);
  const m = Math.floor(s/60), sec = s%60;
  return m+':' + (sec<10? '0'+sec:sec);
}}

const trackListEl = document.getElementById('trackList');
const tracks = (PLAYLIST.tracks || []).map((t, i) => {{
  const vid = idFromUrl(t.url);
  return {{
    index: i,
    name: t.name || ('Track ' + (i+1)),
    videoId: vid,
    start: t.start != null ? Number(t.start) : 0,
    end: t.end != null ? (t.end === null ? null : Number(t.end)) : null
  }};
}});

tracks.forEach(tr => {{
  const el = document.createElement('div');
  el.className = 'track';
  el.dataset.index = tr.index;
  el.innerHTML = '<div class="idx">'+(tr.index+1)+'</div><div class="title">'+tr.name.replace(/[&<>]/g, s=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[s]))+'</div>';
  el.addEventListener('click', () => playIndex(tr.index, true));
  trackListEl.appendChild(el);
}});

let player;
let currentIndex = 0;
let loopTimer = null;
let isPlaying = false;

(function loadYT(){{
  const s = document.createElement('script');
  s.src = "https://www.youtube.com/iframe_api";
  document.head.appendChild(s);
}})();

function onYouTubeIframeAPIReady(){{
  const first = tracks[0];
  if (!first){{
    document.getElementById('player-container').innerHTML = '<div style="color:#ccc">No tracks.</div>';
    return;
  }}
  player = new YT.Player('player-container', {{
    videoId: first.videoId,
    width: 500,
    height: 80,
    playerVars: {{
      enablejsapi: 1,
      modestbranding: 1,
      rel: 0,
      controls: 1,
      iv_load_policy: 3
    }},
    events: {{
      onReady: onPlayerReady,
      onStateChange: onPlayerStateChange
    }}
  }});
  window.addEventListener('resize', resizePlayer);
}}

function resizePlayer(){{
  if (!player || !player.getIframe) return;
  const wrap = document.getElementById('video-wrap');
  const width = Math.min(500, wrap.clientWidth);
  const height = Math.max(56, Math.round(width * (80/500)));
  const ifr = player.getIframe();
  ifr.width = width;
  ifr.height = height;
}}

function onPlayerReady(){{
  resizePlayer();
  highlightActive();
  updateTimeLabel();
}}

function onPlayerStateChange(e){{
  if (e.data === YT.PlayerState.PLAYING){{
    isPlaying = true;
    document.getElementById('playBtn').textContent = 'Pause';
    startLoopWatcher();
  }} else {{
    isPlaying = false;
    document.getElementById('playBtn').textContent = 'Play';
    stopLoopWatcher();
  }}
  updateTimeLabel();
}}

function startLoopWatcher(){{
  stopLoopWatcher();
  loopTimer = setInterval(() => {{
    if (!player) return;
    const now = player.getCurrentTime();
    const t = tracks[currentIndex];
    const end = t.end;
    if (end != null && now >= end - 0.1){{
      player.seekTo(t.start || 0, true);
    }}
    document.getElementById('timeLabel').textContent =
      formatTime(now) + (end ? (' / ' + formatTime(end)) : '');
  }}, 250);
}}

function stopLoopWatcher(){{
  if (loopTimer) clearInterval(loopTimer), loopTimer = null;
}}

function updateTimeLabel(){{
  if (!player) return;
  const now = player.getCurrentTime();
  const t = tracks[currentIndex];
  document.getElementById('timeLabel').textContent =
    formatTime(now) + (t.end ? (' / ' + formatTime(t.end)) : '');
}}

function playIndex(i, play){{
  if (!tracks[i]) return;
  currentIndex = i;
  highlightActive();

  const t = tracks[i];
  player.loadVideoById({{
    videoId: t.videoId,
    startSeconds: t.start || 0
  }});

  if (play){{
    setTimeout(() => player.playVideo(), 80);
  }}
}}

function highlightActive(){{
  document.querySelectorAll('.track').forEach(el =>
    el.classList.toggle('active', Number(el.dataset.index) === currentIndex)
  );
}}

document.getElementById('prevBtn').onclick = () => {{
  playIndex((currentIndex - 1 + tracks.length) % tracks.length, true);
}};
document.getElementById('nextBtn').onclick = () => {{
  playIndex((currentIndex + 1) % tracks.length, true);
}};
document.getElementById('playBtn').onclick = () => {{
  const state = player.getPlayerState();
  if (state === YT.PlayerState.PLAYING) player.pauseVideo();
  else player.playVideo();
}};

window.onYouTubeIframeAPIReady = onYouTubeIframeAPIReady;
</script>
</body>
</html>
"""


# ---- Generate HTML files ----

index_entries = []

for f in playlist_files:
    with open(f, "r", encoding="utf-8") as fp:
        try:
            data = json.load(fp)
        except Exception as e:
            print(f"Skipping invalid JSON: {f} ({e})")
            continue

    playlist_name = data.get("name", f.stem)
    filename = slugify(playlist_name) + ".html"
    outpath = OUT_DIR / filename

    html_text = build_html(data, playlist_name)
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
