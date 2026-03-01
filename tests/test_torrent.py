"""Tests for torrent creation."""

import pytest
from pathlib import Path

from delivery_driver.torrent import create_torrent, get_torrent_info


class TestCreateTorrent:
    """Tests for create_torrent function."""

    def test_creates_torrent_file(self, sample_album, temp_dir):
        """Should create a .torrent file."""
        output_path = temp_dir / "test.torrent"

        result = create_torrent(sample_album, output_path=output_path)

        assert result == output_path
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_default_output_path(self, sample_album):
        """Should create torrent in parent directory by default."""
        result = create_torrent(sample_album)

        expected = sample_album.parent / f"{sample_album.name}.torrent"
        assert result == expected
        assert result.exists()

        # Clean up
        result.unlink()

    def test_includes_default_trackers(self, sample_album, temp_dir):
        """Should include default public trackers."""
        output_path = temp_dir / "test.torrent"
        create_torrent(sample_album, output_path=output_path)

        info = get_torrent_info(output_path)
        assert len(info['trackers']) > 0
        assert any('opentrackr' in t for t in info['trackers'])

    def test_custom_trackers(self, sample_album, temp_dir):
        """Should use custom trackers when provided."""
        output_path = temp_dir / "test.torrent"
        custom_trackers = ['udp://custom.tracker:1234/announce']

        create_torrent(
            sample_album,
            output_path=output_path,
            trackers=custom_trackers
        )

        info = get_torrent_info(output_path)
        assert 'udp://custom.tracker:1234/announce' in info['trackers']

    def test_web_seeds(self, sample_album, temp_dir):
        """Should include web seeds when provided."""
        output_path = temp_dir / "test.torrent"
        web_seeds = ['https://ipfs.io/ipfs/QmFakeHash']

        create_torrent(
            sample_album,
            output_path=output_path,
            web_seeds=web_seeds
        )

        info = get_torrent_info(output_path)
        assert 'https://ipfs.io/ipfs/QmFakeHash' in info['web_seeds']

    def test_comment(self, sample_album, temp_dir):
        """Should include comment when provided."""
        output_path = temp_dir / "test.torrent"

        create_torrent(
            sample_album,
            output_path=output_path,
            comment="Test comment"
        )

        info = get_torrent_info(output_path)
        assert info['comment'] == "Test comment"


class TestGetTorrentInfo:
    """Tests for get_torrent_info function."""

    def test_reads_torrent_info(self, sample_album, temp_dir):
        """Should read info from torrent file."""
        output_path = temp_dir / "test.torrent"
        create_torrent(sample_album, output_path=output_path)

        info = get_torrent_info(output_path)

        assert 'name' in info
        assert 'info_hash' in info
        assert 'size' in info
        assert 'files' in info
        assert 'magnet' in info

    def test_info_hash_is_valid(self, sample_album, temp_dir):
        """Should return valid info hash."""
        output_path = temp_dir / "test.torrent"
        create_torrent(sample_album, output_path=output_path)

        info = get_torrent_info(output_path)

        # Info hash should be 40 hex chars
        assert len(info['info_hash']) == 40
        assert all(c in '0123456789abcdef' for c in info['info_hash'].lower())

    def test_magnet_link_format(self, sample_album, temp_dir):
        """Should return valid magnet link."""
        output_path = temp_dir / "test.torrent"
        create_torrent(sample_album, output_path=output_path)

        info = get_torrent_info(output_path)

        assert info['magnet'].startswith('magnet:?')
        assert 'xt=urn:btih:' in info['magnet']

    def test_lists_files(self, sample_album, temp_dir):
        """Should list all files in torrent."""
        output_path = temp_dir / "test.torrent"
        create_torrent(sample_album, output_path=output_path)

        info = get_torrent_info(output_path)

        # Should have 3 wav files + cover.jpg + README.txt
        assert len(info['files']) == 5
