"""Tests for CLI interface."""

import pytest
from click.testing import CliRunner

from delivery_driver.cli import main


@pytest.fixture
def cli_runner():
    """Create a CLI test runner."""
    return CliRunner()


class TestScanCommand:
    """Tests for the scan command."""

    def test_scan_shows_tracks(self, cli_runner, sample_album):
        """Should display track information."""
        result = cli_runner.invoke(main, ['scan', str(sample_album)])

        assert result.exit_code == 0
        assert 'Scanning' in result.output
        assert '3 tracks' in result.output

    def test_scan_with_version(self, cli_runner, sample_album):
        """Should display version when provided."""
        result = cli_runner.invoke(main, ['scan', str(sample_album), '--version', 'RC1'])

        assert result.exit_code == 0
        assert 'RC1' in result.output

    def test_scan_nonexistent_path(self, cli_runner, temp_dir):
        """Should error on non-existent path."""
        result = cli_runner.invoke(main, ['scan', str(temp_dir / 'nonexistent')])

        assert result.exit_code != 0


class TestTorrentCommand:
    """Tests for the torrent command."""

    def test_creates_torrent(self, cli_runner, sample_album, temp_dir):
        """Should create a torrent file."""
        output_path = temp_dir / "test.torrent"

        result = cli_runner.invoke(main, [
            'torrent', str(sample_album),
            '--output', str(output_path)
        ])

        assert result.exit_code == 0
        assert output_path.exists()
        assert 'Created' in result.output
        assert 'Info hash' in result.output
        assert 'Magnet link' in result.output

    def test_with_web_seed(self, cli_runner, sample_album, temp_dir):
        """Should include web seed when provided."""
        output_path = temp_dir / "test.torrent"

        result = cli_runner.invoke(main, [
            'torrent', str(sample_album),
            '--output', str(output_path),
            '--web-seed', 'https://example.com/files'
        ])

        assert result.exit_code == 0

    def test_with_comment(self, cli_runner, sample_album, temp_dir):
        """Should include comment when provided."""
        output_path = temp_dir / "test.torrent"

        result = cli_runner.invoke(main, [
            'torrent', str(sample_album),
            '--output', str(output_path),
            '--comment', 'Test release'
        ])

        assert result.exit_code == 0


class TestReleaseCommand:
    """Tests for the release command."""

    def test_release_no_ipfs(self, cli_runner, sample_album, temp_dir):
        """Should create release without IPFS when --no-ipfs is set."""
        result = cli_runner.invoke(main, [
            'release', str(sample_album),
            '--output', str(temp_dir),
            '--no-ipfs',
            '--version', 'RC1'
        ])

        assert result.exit_code == 0
        assert 'Release complete' in result.output

        # Should have created torrent and manifest
        torrent_files = list(temp_dir.glob('*.torrent'))
        manifest_files = list(temp_dir.glob('*-manifest.yaml'))

        assert len(torrent_files) == 1
        assert len(manifest_files) == 1

    def test_release_no_torrent(self, cli_runner, sample_album, temp_dir):
        """Should create release without torrent when --no-torrent is set."""
        result = cli_runner.invoke(main, [
            'release', str(sample_album),
            '--output', str(temp_dir),
            '--no-ipfs',
            '--no-torrent'
        ])

        assert result.exit_code == 0

        # Should only have manifest, no torrent
        torrent_files = list(temp_dir.glob('*.torrent'))
        manifest_files = list(temp_dir.glob('*-manifest.yaml'))

        assert len(torrent_files) == 0
        assert len(manifest_files) == 1

    def test_release_with_hashes(self, cli_runner, sample_album, temp_dir):
        """Should compute hashes when --compute-hashes is set."""
        result = cli_runner.invoke(main, [
            'release', str(sample_album),
            '--output', str(temp_dir),
            '--no-ipfs',
            '--compute-hashes'
        ])

        assert result.exit_code == 0
        assert 'checksums' in result.output.lower()


class TestVersionOption:
    """Tests for --version option."""

    def test_shows_version(self, cli_runner):
        """Should show version info."""
        result = cli_runner.invoke(main, ['--version'])

        assert result.exit_code == 0
        assert '0.1.0' in result.output
