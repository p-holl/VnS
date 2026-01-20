import re
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, TIT3, TPE2, TCON, COMM
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


def slugify(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = re.sub(r"^-|-$", "", name)
    return name


@dataclass(eq=False, unsafe_hash=False)
class Track:
    url: str | None  # source website
    title: str
    subtitle: str
    album: str
    artist: str
    performer: str
    genre: str
    tags: list[str]
    file_path: Path = None
    number: int = None
    playlist_name: str = None

    def apply_id3(self, file: str, number: int, playlist_name: str):
        tags = ID3()
        tags.add(TIT2(encoding=3, text=self.title))
        tags.add(TIT3(encoding=3, text=self.subtitle))
        tags.add(TPE1(encoding=3, text=", ".join(list({self.artist, self.performer}))))
        tags.add(TPE2(encoding=3, text="Vibe & Seek"))
        tags.add(TALB(encoding=3, text=playlist_name))
        if self.genre:
            tags.add(TCON(encoding=3, text=self.genre))
        if number is not None:
            tags.add(TRCK(encoding=3, text=str(number)))  # or "1/10"
        if self.album:
            tags.add(COMM(lang='eng', text=f"Album: {self.album}"))
        tags.save(file)

    def cache_dict(self):
        return {'url': self.url, 'title': self.title, 'subtitle': self.subtitle, 'album': self.album, 'artist': self.artist, 'performer': self.performer, 'genre': self.genre, 'tags': self.tags}

    @property
    def display_name(self):
        """Short name"""
        title = self.title.split('(', 1)[0].split(',', 1)[0].strip()
        artist = self.artist.strip()
        if ',' in artist:
            artist = artist[:artist.index(',')]
        if artist.count(' ') >= 2:
            artist = artist.split(' ')[-1]
        return f"{title} • {self.album}" if self.album else f"{title} • {artist}"

    @property
    def long_name(self):
        title = self.title.split('(', 1)[0].strip()
        if self.subtitle:
            title += f" ({self.subtitle})"
        return f"{title} • {self.album} • {self.artist}" if self.album else f"{title} • {self.artist}"

    def get_output_filename(self, number: int):
        return f"{number:03d} {slugify(self.artist)} - {slugify(self.title)}.mp3"

    @property
    def is_hosted_externally(self):
        return self.url and 'youtu' in self.url and not self.url.rstrip('/').endswith('audiolibrary')

    @cached_property
    def parsed_url(self):
        return urlparse(self.url)

    @cached_property
    def clean_url(self):
        parsed = self.parsed_url
        query_params = parse_qs(parsed.query)
        query_params.pop("t", None)
        query_params.pop("e", None)
        new_query = urlencode(query_params, doseq=True)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

    @property
    def start_time(self):
        assert self.is_hosted_externally
        time_str = parse_qs(self.parsed_url.query).get("t", [None])[0]
        return float(time_str) if time_str else None

    @property
    def end_time(self):
        assert self.is_hosted_externally
        time_str = parse_qs(self.parsed_url.query).get("e", [None])[0]
        return float(time_str) if time_str else None


def search_track(long_name: str, url: str, number: int, tracks: list[Track]):
    matches = [t for t in tracks if t.long_name == long_name]
    if not matches:
         return None
    elif len(matches) == 1:
        return matches[0]
    else:  # multiple matches
        matches2 = [t for t in matches if t.get_output_filename(number) == url]
        assert len(matches2) <= 1
        return matches2[0] if matches2 else None


def track_from_file(path: Path, playlist_name: str = None) -> Track:
    tags = ID3(path)

    def get_text(frame_id, default=""):
        frame = tags.get(frame_id)
        return ", ".join(frame.text) if frame else default

    title = get_text('TIT2')
    subtitle = get_text('TIT3')
    if not subtitle and ',' in title:
        subtitle = title[title.index(',')+1:].strip()
        title = title[:title.index(',')]
    comments = sum([frame.text for frame in tags.getall("COMM")], [])
    performer = get_text('TPE1')  # "Contributing Artists"
    artist = get_text('TPE2') or performer  # "Album Artist" (e.g. composer)
    performer = performer or artist
    album = get_text('TALB')
    genre = get_text('TCON')
    # --- Construct Track ---
    number = None  # get_text('TRCK')
    tags = [t.strip().lower() for t in path.stem.split(' ') if len(t.strip()) > 2 and t.strip().lower() not in {'the',}] + ([genre] if genre else [])
    if path.stem[0].isdigit():
        number = int(path.stem.split(" ", 1)[0])
    source = get_url_from_comments(comments)
    return Track(source, title, subtitle, album, artist, performer, genre, tags, path, number, playlist_name)


def get_url_from_comments(comments: list[str]):
    for comment in comments:
        if '.org' in comment and not comment.startswith('http'):
            comment = 'https://' + comment
        if comment.endswith('/watch'):
            continue
        if comment.startswith('http'):
            return comment
    return None


def check_no_duplicates(tracks: list[Track]):
    for i, t1 in enumerate(tracks):
        for t2 in tracks[i+1:]:
            if t1 is not None and t2 is not None:
                if t1.long_name == t2.long_name:
                    raise AssertionError(f"Duplicate songs with name {t1.long_name}")


# if __name__ == '__main__':
#     for file in os.listdir(r""):
