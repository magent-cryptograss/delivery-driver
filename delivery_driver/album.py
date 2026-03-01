"""Album scanning and metadata extraction."""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from mutagen import File as MutagenFile
from mutagen.flac import FLAC


@dataclass
class Track:
    """Represents a single audio track."""
    path: Path
    filename: str
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    track_number: int | None = None
    duration_seconds: float | None = None
    format: str = "flac"
    size_bytes: int = 0
    sha256: str | None = None
    ipfs_cid: str | None = None

    def compute_hash(self) -> str:
        """Compute SHA256 hash of the file."""
        sha256 = hashlib.sha256()
        with open(self.path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        self.sha256 = sha256.hexdigest()
        return self.sha256


@dataclass
class Album:
    """Represents an album release."""
    path: Path
    title: str | None = None
    artist: str | None = None
    version: str | None = None  # e.g., "RC0", "RC1", "final"
    tracks: list[Track] = field(default_factory=list)
    artwork: list[Path] = field(default_factory=list)
    other_files: list[Path] = field(default_factory=list)
    ipfs_cid: str | None = None  # CID of the whole album directory

    @property
    def total_size(self) -> int:
        """Total size of all tracks in bytes."""
        return sum(t.size_bytes for t in self.tracks)

    @property
    def total_duration(self) -> float:
        """Total duration of all tracks in seconds."""
        return sum(t.duration_seconds or 0 for t in self.tracks)


def extract_track_metadata(path: Path) -> Track:
    """Extract metadata from an audio file."""
    audio = MutagenFile(path)

    track = Track(
        path=path,
        filename=path.name,
        size_bytes=path.stat().st_size,
    )

    if audio is None:
        return track

    # Get duration
    if hasattr(audio.info, 'length'):
        track.duration_seconds = audio.info.length

    # Detect format
    if isinstance(audio, FLAC):
        track.format = "flac"
    elif path.suffix.lower() == '.mp3':
        track.format = "mp3"
    elif path.suffix.lower() in ('.m4a', '.aac'):
        track.format = "aac"
    elif path.suffix.lower() == '.wav':
        track.format = "wav"

    # Extract tags
    if hasattr(audio, 'tags') and audio.tags:
        tags = audio.tags

        # FLAC/Vorbis comments
        if hasattr(tags, 'get'):
            track.title = _get_first(tags.get('title'))
            track.artist = _get_first(tags.get('artist'))
            track.album = _get_first(tags.get('album'))
            track_num = _get_first(tags.get('tracknumber'))
            if track_num:
                try:
                    # Handle "1/10" format
                    track.track_number = int(track_num.split('/')[0])
                except ValueError:
                    pass

    return track


def _get_first(value) -> str | None:
    """Get first item if list, otherwise return as-is."""
    if value is None:
        return None
    if isinstance(value, list):
        return value[0] if value else None
    return str(value)


def scan_album(path: Path, version: str | None = None) -> Album:
    """Scan an album directory and extract metadata from all tracks."""
    path = Path(path)

    if not path.is_dir():
        raise ValueError(f"Not a directory: {path}")

    album = Album(path=path, version=version)

    # Audio file extensions
    audio_extensions = {'.flac', '.mp3', '.m4a', '.aac', '.wav', '.ogg'}
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

    for file_path in sorted(path.iterdir()):
        if file_path.is_file():
            suffix = file_path.suffix.lower()

            if suffix in audio_extensions:
                track = extract_track_metadata(file_path)
                album.tracks.append(track)
            elif suffix in image_extensions:
                album.artwork.append(file_path)
            elif suffix not in {'.ds_store', '.gitignore'}:
                album.other_files.append(file_path)

    # Sort tracks by track number if available
    album.tracks.sort(key=lambda t: (t.track_number or 999, t.filename))

    # Try to infer album metadata from tracks
    if album.tracks:
        first_track = album.tracks[0]
        album.title = first_track.album or path.name
        album.artist = first_track.artist

    return album
