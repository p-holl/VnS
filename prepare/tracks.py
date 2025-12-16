from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, TIT3, TPE2, TCON, COMM
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


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
        title = self.title.split('(', 1)[0].strip()
        if self.subtitle:
            title += f" ({self.subtitle})"
        return f"{title} • {self.album} • {self.artist}" if self.album else f"{title} • {self.artist}"

    @property
    def output_filename(self):
        return f"{self.artist} - {self.title}.mp3"

    @property
    def is_hosted_externally(self):
        return self.url and 'youtu' in self.url

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


def search_track(display_name: str, url: str, tracks: list[Track]):
    matches = [t for t in tracks if t.display_name == display_name]
    if not matches:
         return None
    elif len(matches) == 1:
        return matches[0]
    else:  # multiple matches
        matches = [t for t in matches if t.output_filename == url]
        assert len(matches) <= 1
        return matches[0] if matches else None


def track_from_file(path: Path) -> Track:
    tags = ID3(path)

    def get_text(frame_id, default=""):
        frame = tags.get(frame_id)
        return ", ".join(frame.text) if frame else default

    title = get_text('TIT2')
    subtitle = get_text('TIT3')
    comments = {frame.lang: ", ".join(frame.text) for frame in tags.getall("COMM")}
    performer = get_text('TPE1')  # "Contributing Artists"
    artist = get_text('TPE2') or performer  # "Album Artist" (e.g. composer)
    performer = performer or artist
    album = get_text('TALB')
    # track_number = get_text('TRCK')
    genre = get_text('TCON')
    # --- Construct Track ---
    tags = [t.strip() for t in path.stem.split(' ') if len(t.strip()) > 2 and t.strip().lower() not in {'the',}] + ([genre] if genre else [])
    for comment in comments.values():
        if '.org' in comment:
            comment = 'https://' + comment
        if comment.startswith('http'):
            source = comment
            break
    else:
        source = None
    return Track(source, title, subtitle, album, artist, performer, genre, tags, path)


# if __name__ == '__main__':
#     for file in os.listdir(r""):
