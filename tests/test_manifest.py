"""Tests for manifest generation."""

import json
import yaml
from pathlib import Path

import pytest

from delivery_driver.album import scan_album
from delivery_driver.manifest import (
    generate_manifest,
    write_manifest,
    format_duration,
    format_size,
)


class TestGenerateManifest:
    """Tests for generate_manifest function."""

    def test_includes_album_info(self, sample_album):
        """Should include basic album info."""
        album = scan_album(sample_album, version="RC1")

        manifest = generate_manifest(album)

        assert 'album' in manifest
        assert manifest['album']['release_version'] == "RC1"
        assert manifest['album']['total_tracks'] == 3

    def test_includes_track_list(self, sample_album):
        """Should include all tracks."""
        album = scan_album(sample_album)

        manifest = generate_manifest(album)

        assert 'tracks' in manifest
        assert len(manifest['tracks']) == 3

    def test_includes_track_details(self, sample_album):
        """Should include track details."""
        album = scan_album(sample_album)

        manifest = generate_manifest(album)

        track = manifest['tracks'][0]
        assert 'filename' in track
        assert 'size_bytes' in track
        assert 'duration_seconds' in track
        assert 'format' in track

    def test_includes_artwork(self, sample_album):
        """Should include artwork list."""
        album = scan_album(sample_album)

        manifest = generate_manifest(album)

        assert 'artwork' in manifest
        assert len(manifest['artwork']) == 1
        assert manifest['artwork'][0]['filename'] == 'cover.jpg'

    def test_includes_ipfs_info(self, sample_album):
        """Should include IPFS info when CID is set."""
        album = scan_album(sample_album)
        album.ipfs_cid = "QmFakeHash123"

        manifest = generate_manifest(album)

        assert 'ipfs' in manifest
        assert manifest['ipfs']['directory_cid'] == "QmFakeHash123"
        assert 'gateway_url' in manifest['ipfs']
        assert 'dweb_url' in manifest['ipfs']

    def test_includes_torrent_info(self, sample_album):
        """Should include torrent info when provided."""
        album = scan_album(sample_album)
        torrent_info = {
            'info_hash': 'abc123',
            'magnet': 'magnet:?xt=urn:btih:abc123',
            'trackers': ['udp://tracker.example.com'],
            'web_seeds': ['https://ipfs.io/ipfs/QmFake'],
        }

        manifest = generate_manifest(album, torrent_info=torrent_info)

        assert 'torrent' in manifest
        assert manifest['torrent']['info_hash'] == 'abc123'
        assert manifest['torrent']['magnet'] == 'magnet:?xt=urn:btih:abc123'

    def test_includes_hashes_when_computed(self, sample_album):
        """Should include SHA256 hashes when tracks have them."""
        album = scan_album(sample_album)
        for track in album.tracks:
            track.compute_hash()

        manifest = generate_manifest(album, include_hashes=True)

        for track in manifest['tracks']:
            assert 'sha256' in track
            assert len(track['sha256']) == 64

    def test_excludes_hashes_when_disabled(self, sample_album):
        """Should exclude hashes when include_hashes=False."""
        album = scan_album(sample_album)
        for track in album.tracks:
            track.compute_hash()

        manifest = generate_manifest(album, include_hashes=False)

        for track in manifest['tracks']:
            assert 'sha256' not in track

    def test_includes_metadata(self, sample_album):
        """Should include generation metadata."""
        album = scan_album(sample_album)

        manifest = generate_manifest(album)

        assert manifest['version'] == '1.0'
        assert manifest['generator'] == 'delivery-driver'
        assert 'generated_at' in manifest


class TestWriteManifest:
    """Tests for write_manifest function."""

    def test_writes_yaml(self, sample_album, temp_dir):
        """Should write YAML manifest."""
        album = scan_album(sample_album)
        manifest = generate_manifest(album)

        output_path = write_manifest(manifest, temp_dir / "manifest", format='yaml')

        assert output_path.suffix == '.yaml'
        assert output_path.exists()

        # Should be valid YAML
        with open(output_path) as f:
            loaded = yaml.safe_load(f)
        assert loaded['album']['total_tracks'] == 3

    def test_writes_json(self, sample_album, temp_dir):
        """Should write JSON manifest."""
        album = scan_album(sample_album)
        manifest = generate_manifest(album)

        output_path = write_manifest(manifest, temp_dir / "manifest", format='json')

        assert output_path.suffix == '.json'
        assert output_path.exists()

        # Should be valid JSON
        with open(output_path) as f:
            loaded = json.load(f)
        assert loaded['album']['total_tracks'] == 3

    def test_invalid_format_raises(self, sample_album, temp_dir):
        """Should raise error for invalid format."""
        album = scan_album(sample_album)
        manifest = generate_manifest(album)

        with pytest.raises(ValueError, match="Unknown format"):
            write_manifest(manifest, temp_dir / "manifest", format='xml')


class TestFormatDuration:
    """Tests for format_duration function."""

    def test_formats_seconds(self):
        assert format_duration(45) == "0:45"

    def test_formats_minutes(self):
        assert format_duration(125) == "2:05"

    def test_formats_hours(self):
        assert format_duration(3725) == "1:02:05"

    def test_handles_zero(self):
        assert format_duration(0) == "0:00"


class TestFormatSize:
    """Tests for format_size function."""

    def test_formats_bytes(self):
        assert format_size(500) == "500.0 B"

    def test_formats_kilobytes(self):
        assert format_size(2048) == "2.0 KB"

    def test_formats_megabytes(self):
        assert format_size(5 * 1024 * 1024) == "5.0 MB"

    def test_formats_gigabytes(self):
        assert format_size(2 * 1024 * 1024 * 1024) == "2.0 GB"
