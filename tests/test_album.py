"""Tests for album scanning and metadata extraction."""

from pathlib import Path

from delivery_driver.album import scan_album, extract_track_metadata, Album, Track


class TestExtractTrackMetadata:
    """Tests for extract_track_metadata function."""

    def test_extracts_basic_info(self, minimal_flac):
        """Should extract basic file info from audio file."""
        track = extract_track_metadata(minimal_flac)

        assert track.filename == minimal_flac.name
        assert track.path == minimal_flac
        assert track.size_bytes > 0
        assert track.format == "wav"

    def test_extracts_duration(self, minimal_flac):
        """Should extract duration from audio file."""
        track = extract_track_metadata(minimal_flac)

        # Our test file is 0.1 seconds
        assert track.duration_seconds is not None
        assert track.duration_seconds == pytest.approx(0.1, abs=0.01)


class TestScanAlbum:
    """Tests for scan_album function."""

    def test_scans_directory(self, sample_album):
        """Should scan album directory and find all tracks."""
        album = scan_album(sample_album)

        assert isinstance(album, Album)
        assert album.path == sample_album
        assert len(album.tracks) == 3

    def test_finds_artwork(self, sample_album):
        """Should find artwork files."""
        album = scan_album(sample_album)

        assert len(album.artwork) == 1
        assert album.artwork[0].name == "cover.jpg"

    def test_finds_other_files(self, sample_album):
        """Should find non-audio, non-image files."""
        album = scan_album(sample_album)

        assert len(album.other_files) == 1
        assert album.other_files[0].name == "README.txt"

    def test_sorts_tracks_by_filename(self, sample_album):
        """Should sort tracks by filename when no track numbers."""
        album = scan_album(sample_album)

        filenames = [t.filename for t in album.tracks]
        assert filenames == sorted(filenames)

    def test_version_is_stored(self, sample_album):
        """Should store version if provided."""
        album = scan_album(sample_album, version="RC1")

        assert album.version == "RC1"

    def test_total_size(self, sample_album):
        """Should calculate total size of all tracks."""
        album = scan_album(sample_album)

        assert album.total_size > 0
        assert album.total_size == sum(t.size_bytes for t in album.tracks)

    def test_total_duration(self, sample_album):
        """Should calculate total duration of all tracks."""
        album = scan_album(sample_album)

        assert album.total_duration > 0

    def test_raises_for_nonexistent_path(self, temp_dir):
        """Should raise error for non-existent path."""
        import pytest
        with pytest.raises(ValueError, match="Not a directory"):
            scan_album(temp_dir / "nonexistent")

    def test_raises_for_file_path(self, minimal_flac):
        """Should raise error when given a file instead of directory."""
        import pytest
        with pytest.raises(ValueError, match="Not a directory"):
            scan_album(minimal_flac)


class TestTrack:
    """Tests for Track dataclass."""

    def test_compute_hash(self, minimal_flac):
        """Should compute SHA256 hash of file."""
        track = Track(
            path=minimal_flac,
            filename=minimal_flac.name,
            size_bytes=minimal_flac.stat().st_size,
        )

        hash_result = track.compute_hash()

        assert hash_result is not None
        assert len(hash_result) == 64  # SHA256 hex is 64 chars
        assert track.sha256 == hash_result


# Import pytest for approx
import pytest
