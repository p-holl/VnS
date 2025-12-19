import json
import random
from pathlib import Path

from html_gen.generate import generate_playlist_html
from process_mp3.compress import compress_mp3_vbr_parallel
from process_mp3.tracks import track_from_file, Track, search_track, slugify


def score_similarity(tags_a, tags_b):
    """Return number of shared tags (lower = better separation)."""
    return len(tags_a & tags_b)


def greedy_shuffle(tracks: list[Track]) -> list[Track]:
    """
    Create an ordering where items with similar tags end up far apart.
    Greedy: start with any item, repeatedly pick the least-similar next item.
    """
    remaining = tracks[:]
    random.shuffle(remaining)
    ordering = [remaining.pop()]  # start with random file
    while remaining:
        last_tags = set(ordering[-1].tags)
        # Pick file with minimum shared tags with last file
        next_file = min(remaining, key=lambda f: score_similarity(last_tags, set(f.tags)))
        ordering.append(next_file)
        remaining.remove(next_file)
    return ordering


def create_shuffled_playlist(src_dir: Path, amend=True):
    playlist_name = src_dir.name
    output_dir = Path(__file__).parent.parent / 'docs' / 'audio' / slugify(playlist_name)
    playlist_file = Path(__file__).parent.parent / 'playlists' / (playlist_name + ".json")
    if playlist_file.is_file():
        with playlist_file.open('r', encoding='utf-8') as f:
            playlist_data = json.load(f)
        if not amend:
            playlist_data['majorVersion'] += 1
            playlist_data['minorVersion'] = 0
        else:
            playlist_data['minorVersion'] += 1
    else:
        playlist_data = {'majorVersion': 0, 'minorVersion': 0, 'tracks': []}
    # --- Discover tracks & shuffle ---
    all_tracks = [track_from_file(file) for file in src_dir.iterdir() if file.name.endswith('.mp3')]
    ordered = []
    if amend:
        for i, existing in enumerate(playlist_data['tracks'], 1):
            matching_track = search_track(existing['name'], existing['url'], i, all_tracks)
            if matching_track:
                ordered.append(matching_track)
            else:
                print(f"Track removed: {existing['name']}")
    remaining = set(all_tracks) - set(ordered)
    if remaining:
        ordered = ordered + greedy_shuffle(list(remaining))
    # --- Shuffle & write ---
    track_data = []
    hosted_src: list[Track] = []
    hosted_dst: list[Path] = []
    for i, track in enumerate(ordered, 1):
        track.number = i
        track.playlist_name = playlist_name
        if not track.is_hosted_externally:
            if 'Erik' in track.title:
                print()
            dst = output_dir / track.get_output_filename(i)
            hosted_src.append(track)
            hosted_dst.append(dst)
            track_data.append({"name": track.display_name, "url": dst.name, "start": 0., "end": None, "source": track.url})
        else:  # YouTube
            track_data.append({"name": track.display_name, "url": track.clean_url, "start": track.start_time, "end": None})
    playlist_data['tracks'] = track_data
    playlist_file.parent.mkdir(exist_ok=True, parents=True)
    with playlist_file.open('w', encoding='utf-8') as f:
        json.dump(playlist_data, f, indent=2)
    print(f"✅ Created playlist {src_dir.name}! {len(hosted_src)} / {len(ordered)} audio files will be hosted", output_dir)
    return playlist_file, playlist_name, hosted_src, hosted_dst


if __name__ == "__main__":
    ROOT = Path(__file__).parent.parent
    for playlist_dir in (ROOT / 'source_playlists').iterdir():
        if not playlist_dir.name.startswith('_'):
            print(f"Creating playlist from '{playlist_dir.name}'")
            file, name, hosted_tracks, hosted_paths = create_shuffled_playlist(playlist_dir, amend=True)
            compress_mp3_vbr_parallel(hosted_tracks, hosted_paths, overwrite=False)
    generate_playlist_html(ROOT / 'playlists', ROOT / 'docs')
