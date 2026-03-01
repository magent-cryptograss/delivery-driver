# Delivery Driver 🚚

CLI tool for distributing music via IPFS and BitTorrent.

## Installation

```bash
pip install -e .
```

## Usage

### Scan an album

See what's in an album directory:

```bash
delivery-driver scan /path/to/album --version RC1
```

### Full release

Create a complete release with IPFS upload, torrent, and manifest:

```bash
delivery-driver release /path/to/4masks-RC1 --version RC1
```

This will:
1. Scan the album and extract metadata
2. Add the directory to your local IPFS node
3. Pin to Pinata (if `PINATA_JWT` env var is set)
4. Create a `.torrent` file with IPFS gateway as web seed
5. Generate a YAML manifest with all the metadata

### Individual commands

Just create a torrent:
```bash
delivery-driver torrent /path/to/album
```

Just add to IPFS:
```bash
delivery-driver ipfs /path/to/album
```

## Options

```bash
# Skip IPFS upload (just make torrent + manifest)
delivery-driver release /path/to/album --no-ipfs

# Skip torrent creation
delivery-driver release /path/to/album --no-torrent

# Compute SHA256 hashes for verification
delivery-driver release /path/to/album --compute-hashes

# Custom IPFS API endpoint
delivery-driver release /path/to/album --ipfs-api http://localhost:5001

# Custom output directory
delivery-driver release /path/to/album -o /path/to/output
```

## Environment Variables

- `PINATA_JWT` - Pinata API JWT for redundant pinning

## Output

A typical release creates:

```
output/
├── 4masks-RC1.torrent      # BitTorrent file
└── 4masks-RC1-manifest.yaml # Release manifest
```

The manifest contains:
- Album metadata (title, artist, track listing)
- IPFS CIDs (directory and per-file)
- Torrent info hash and magnet link
- File checksums (if --compute-hashes)

## Requirements

- Python 3.10+
- IPFS daemon running locally (for IPFS features)
- Or just use `--no-ipfs` for torrent-only mode
