import json
import shutil
import random
from pathlib import Path

from tracks import track_from_file, Track, search_track


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
    output_dir = Path(__file__).parent.parent / 'audio'
    output_dir.mkdir(exist_ok=True)
    playlist_name = src_dir.name
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
        for existing in playlist_data['tracks']:
            matching_track = search_track(existing['name'], existing['url'], all_tracks)
            if matching_track:
                ordered.append(matching_track)
    remaining = set(all_tracks) - set(ordered)
    if remaining:
        ordered = ordered + greedy_shuffle(list(remaining))
    # --- Shuffle & write ---
    track_data = []
    for i, track in enumerate(ordered, 1):
        if not track.is_hosted_externally:
            dst = output_dir / f"{track.artist} - {track.title}.mp3"
            shutil.copy2(track.file_path, dst)
            track.apply_id3(str(dst), i, playlist_name)
            track_data.append({"name": track.display_name, "url": dst.name, "start": 0., "end": None, "source": track.url})
        else:  # YouTube
            track_data.append({"name": track.display_name, "url": track.clean_url, "start": track.start_time, "end": None})
        # ToDo also copy as {i:03d}_...mp3
    playlist_data['tracks'] = track_data
    with playlist_file.open('w', encoding='utf-8') as f:
        json.dump(playlist_data, f, indent=2)
    print(f"✅ Done! {len(ordered)} audio files copied to", output_dir)


if __name__ == "__main__":
    for playlist_dir in (Path(__file__).parent.parent / 'source_playlists').iterdir():
        if not playlist_dir.name.startswith('_'):
            print(f"Creating playlist from '{playlist_dir.name}'")
            create_shuffled_playlist(playlist_dir)
