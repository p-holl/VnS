import json
from pathlib import Path

from html_gen.generate import generate_playlist_html
from order_opt.simulated_annealing import simulated_annealing, greedy_fill
from process_mp3.compress import compress_mp3_vbr_parallel
from process_mp3.tracks import track_from_file, Track, search_track, slugify, check_no_duplicates


def create_shuffled_playlist(src_dir: Path, amend: bool, create_preview: bool):
    playlist_name = src_dir.name.split("(", 1)[0].strip()
    output_dir = Path(__file__).parent.parent / 'docs' / 'audio' / slugify(playlist_name)
    if output_dir.is_dir():
        for file in output_dir.iterdir():
            if file.name.endswith('.mp3'):
                file.unlink(missing_ok=True)
    preview_dir = Path(__file__).parent.parent / 'preview-audio' / slugify(playlist_name)
    if create_preview and preview_dir.is_dir():
        for file in preview_dir.iterdir():
            file.unlink(missing_ok=True)
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
    all_tracks = [track_from_file(file, playlist_name) for file in src_dir.iterdir() if file.name.endswith('.mp3')]
    if amend:
        for i, existing in enumerate(playlist_data['tracks'], 1):
            matching_track = search_track(existing['full'], existing['url'], i, all_tracks)
            if matching_track:
                matching_track.number = i
            else:
                print(f"Track removed: {existing['name']}")
    ordered = [None] * len(all_tracks)
    for track in all_tracks:
        if track.number is not None:
            ordered[track.number - 1] = track
    remaining = [t for t in all_tracks if t.number is None]
    ordered = greedy_fill(ordered, remaining)
    ordered, loss = simulated_annealing(ordered, iterations_per_temp=2*len(remaining))
    check_no_duplicates(ordered)
    print("Ordering loss per element:", loss / len(ordered))
    # --- Shuffle & write ---
    track_data = []
    hosted_src: list[Track] = []
    hosted_dst: list[Path] = []
    for i, track in enumerate(ordered, 1):
        track.number = i
        if not track.is_hosted_externally:
            dst = output_dir / track.get_output_filename(i)
            hosted_src.append(track)
            hosted_dst.append(dst)
            track_data.append({"name": track.display_name, "full": track.long_name, "url": dst.name, "start": 0., "end": None, "source": track.url})
        else:  # YouTube
            track_data.append({"name": track.display_name, "full": track.long_name, "url": track.clean_url, "start": track.start_time, "end": track.end_time})
            if create_preview:
                preview = preview_dir / track.get_output_filename(i)
                hosted_src.append(track)
                hosted_dst.append(preview)
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
            file, name, hosted_tracks, hosted_paths = create_shuffled_playlist(playlist_dir, amend=True, create_preview=True)
            compress_mp3_vbr_parallel(hosted_tracks, hosted_paths, overwrite=False)
    generate_playlist_html(ROOT / 'playlists', ROOT / 'docs')
