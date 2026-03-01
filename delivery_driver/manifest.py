"""Album manifest generation."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .album import Album


def generate_manifest(
    album: Album,
    torrent_info: dict | None = None,
    include_hashes: bool = True,
) -> dict[str, Any]:
    """
    Generate a manifest dict for an album release.

    The manifest contains all metadata needed to verify and access the release.
    """
    manifest = {
        'version': '1.0',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'generator': 'delivery-driver',
        'album': {
            'title': album.title,
            'artist': album.artist,
            'release_version': album.version,
            'total_tracks': len(album.tracks),
            'total_duration_seconds': album.total_duration,
            'total_size_bytes': album.total_size,
        },
        'tracks': [],
        'artwork': [],
        'other_files': [],
    }

    # Add IPFS info if available
    if album.ipfs_cid:
        manifest['ipfs'] = {
            'directory_cid': album.ipfs_cid,
            'gateway_url': f"https://ipfs.io/ipfs/{album.ipfs_cid}",
            'dweb_url': f"ipfs://{album.ipfs_cid}",
        }

    # Add tracks
    for track in album.tracks:
        track_info = {
            'filename': track.filename,
            'title': track.title,
            'artist': track.artist,
            'track_number': track.track_number,
            'duration_seconds': track.duration_seconds,
            'format': track.format,
            'size_bytes': track.size_bytes,
        }

        if include_hashes and track.sha256:
            track_info['sha256'] = track.sha256

        if track.ipfs_cid:
            track_info['ipfs_cid'] = track.ipfs_cid

        manifest['tracks'].append(track_info)

    # Add artwork
    for art_path in album.artwork:
        manifest['artwork'].append({
            'filename': art_path.name,
            'size_bytes': art_path.stat().st_size,
        })

    # Add other files
    for other_path in album.other_files:
        manifest['other_files'].append({
            'filename': other_path.name,
            'size_bytes': other_path.stat().st_size,
        })

    # Add torrent info if available
    if torrent_info:
        manifest['torrent'] = {
            'info_hash': torrent_info.get('info_hash'),
            'magnet': torrent_info.get('magnet'),
            'trackers': torrent_info.get('trackers', []),
            'web_seeds': torrent_info.get('web_seeds', []),
        }

    return manifest


def write_manifest(manifest: dict, output_path: Path, format: str = 'yaml') -> Path:
    """
    Write manifest to file.

    Args:
        manifest: The manifest dict
        output_path: Where to write (extension will be adjusted based on format)
        format: 'yaml' or 'json'

    Returns:
        Path to the written file
    """
    output_path = Path(output_path)

    if format == 'yaml':
        if output_path.suffix not in ('.yaml', '.yml'):
            output_path = output_path.with_suffix('.yaml')

        with open(output_path, 'w') as f:
            yaml.dump(manifest, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    elif format == 'json':
        if output_path.suffix != '.json':
            output_path = output_path.with_suffix('.json')

        with open(output_path, 'w') as f:
            json.dump(manifest, f, indent=2)

    else:
        raise ValueError(f"Unknown format: {format}")

    return output_path


def format_duration(seconds: float) -> str:
    """Format duration as MM:SS or HH:MM:SS."""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def format_size(bytes: int) -> str:
    """Format size in human-readable form."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} TB"
