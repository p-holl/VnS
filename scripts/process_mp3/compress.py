from pathlib import Path
import subprocess

from .tracks import Track


def compress_mp3_vbr(track: Track, output_path: Path, vbr_quality=7, overwrite=True):
    """
    Compress MP3 to lower VBR bitrate using FFmpeg.

    vbr_quality: LAME VBR quality level (0 = highest quality, 9 = lowest bitrate).
    """
    if not overwrite and output_path.is_file():
        print(f"Already exists: {output_path}")
        return
    output_path.parent.mkdir(exist_ok=True, parents=True)
    command = [
        "ffmpeg",
        "-y",  # overwrite output without asking
        "-i", str(track.file_path),
        "-codec:a", "libmp3lame",
        "-qscale:a", str(vbr_quality),
        str(output_path)
    ]
    result = subprocess.run(command, check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    track.apply_id3(str(output_path), track.number, track.playlist_name)
    if result.returncode == 0:
        print(f"✅ Wrote compressed {output_path}")
    else:
        raise RuntimeError(f"Failed to write {output_path}")


def compress_mp3_vbr_parallel(tracks: list[Track], outputs: list[Path], vbr_quality=7, overwrite=True):
    # for track, path_out in zip(tracks, outputs):
    #     compress_mp3_vbr(track, path_out, vbr_quality, overwrite)
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=12) as pool:
        for track, path_out in zip(tracks, outputs):
            pool.submit(compress_mp3_vbr, track, path_out, vbr_quality, overwrite)


if __name__ == '__main__':
    files = [file for file in (Path(__file__).parent.parent / 'audio').iterdir() if file.name.endswith('.mp3')]
    # compress_mp3_vbr_parallel(files)
    # compress_mp3_vbr(files[0], files[0].parent / 'compressed' / files[0].name)
