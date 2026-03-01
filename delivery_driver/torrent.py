"""Torrent file creation."""

from pathlib import Path
from datetime import datetime

from torf import Torrent


def create_torrent(
    path: Path,
    output_path: Path | None = None,
    trackers: list[str] | None = None,
    web_seeds: list[str] | None = None,
    comment: str | None = None,
    created_by: str = "Delivery Driver",
) -> Path:
    """
    Create a .torrent file for an album directory.

    Args:
        path: Directory or file to create torrent for
        output_path: Where to save the .torrent file (default: same dir as input)
        trackers: List of tracker URLs
        web_seeds: List of HTTP/HTTPS URLs for web seeding (e.g., IPFS gateways)
        comment: Comment to embed in torrent
        created_by: Creator string

    Returns:
        Path to the created .torrent file
    """
    path = Path(path)

    # Default trackers - public trackers that allow music
    if trackers is None:
        trackers = [
            'udp://tracker.opentrackr.org:1337/announce',
            'udp://open.stealth.si:80/announce',
            'udp://tracker.torrent.eu.org:451/announce',
            'udp://open.demonii.com:1337/announce',
            'udp://explodie.org:6969/announce',
        ]

    # Create the torrent
    torrent = Torrent(
        path=path,
        trackers=trackers,
        comment=comment,
        created_by=created_by,
        creation_date=datetime.now(),
        private=False,  # Public torrent
    )

    # Add web seeds (IPFS gateway URLs work great here)
    if web_seeds:
        torrent.webseeds = web_seeds

    # Generate the torrent
    torrent.generate()

    # Determine output path
    if output_path is None:
        if path.is_dir():
            output_path = path.parent / f"{path.name}.torrent"
        else:
            output_path = path.with_suffix('.torrent')

    # Write the torrent file
    torrent.write(output_path)

    return output_path


def get_torrent_info(torrent_path: Path) -> dict:
    """Read info from an existing torrent file."""
    torrent = Torrent.read(torrent_path)

    # Flatten tracker tiers into a single list
    # torf stores trackers as tiers (list of lists)
    trackers = []
    for tier in torrent.trackers:
        for tracker in tier:
            trackers.append(str(tracker))

    return {
        'name': torrent.name,
        'info_hash': str(torrent.infohash),
        'size': torrent.size,
        'piece_size': torrent.piece_size,
        'num_pieces': torrent.pieces if isinstance(torrent.pieces, int) else len(torrent.pieces),
        'files': [str(f) for f in torrent.files],
        'trackers': trackers,
        'web_seeds': list(torrent.webseeds) if torrent.webseeds else [],
        'comment': torrent.comment,
        'created_by': torrent.created_by,
        'creation_date': torrent.creation_date.isoformat() if torrent.creation_date else None,
        'magnet': str(torrent.magnet()),
    }
