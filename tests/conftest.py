"""Pytest fixtures for delivery-driver tests."""

import os
import struct
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def minimal_flac(temp_dir):
    """
    Create a minimal valid FLAC file for testing.

    This creates a tiny but valid FLAC file that mutagen can parse.
    """
    # Minimal FLAC: magic + STREAMINFO block + empty audio
    # FLAC format: https://xiph.org/flac/format.html

    flac_path = temp_dir / "test.flac"

    # This is a minimal valid FLAC file (silent, very short)
    # Generated from: ffmpeg -f lavfi -i "sine=frequency=440:duration=0.1" -c:a flac minimal.flac
    # Then base64 encoded
    import base64
    minimal_flac_b64 = (
        "ZkxhQwAAACIQABAAAAAYABj/+QAA/wAAAQ4AAAABAAAAAAAAAAAAAAAA"
        "AAAAAAAAAP8BAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP//"
    )

    # Actually, let's just write a WAV instead - simpler and mutagen handles it
    wav_path = temp_dir / "test.wav"

    # Minimal WAV: RIFF header + fmt chunk + data chunk
    sample_rate = 44100
    num_channels = 1
    bits_per_sample = 16
    num_samples = 4410  # 0.1 seconds

    with open(wav_path, 'wb') as f:
        # RIFF header
        data_size = num_samples * num_channels * (bits_per_sample // 8)
        f.write(b'RIFF')
        f.write(struct.pack('<I', 36 + data_size))
        f.write(b'WAVE')

        # fmt chunk
        f.write(b'fmt ')
        f.write(struct.pack('<I', 16))  # chunk size
        f.write(struct.pack('<H', 1))   # audio format (PCM)
        f.write(struct.pack('<H', num_channels))
        f.write(struct.pack('<I', sample_rate))
        f.write(struct.pack('<I', sample_rate * num_channels * bits_per_sample // 8))
        f.write(struct.pack('<H', num_channels * bits_per_sample // 8))
        f.write(struct.pack('<H', bits_per_sample))

        # data chunk
        f.write(b'data')
        f.write(struct.pack('<I', data_size))
        f.write(b'\x00' * data_size)  # silence

    return wav_path


@pytest.fixture
def sample_album(temp_dir, minimal_flac):
    """Create a sample album directory with test files."""
    album_dir = temp_dir / "Test Album"
    album_dir.mkdir()

    # Create a few "tracks" (copies of the minimal wav)
    import shutil
    for i in range(3):
        track_path = album_dir / f"0{i+1} - Track {i+1}.wav"
        shutil.copy(minimal_flac, track_path)

    # Create a fake cover image
    cover_path = album_dir / "cover.jpg"
    # Minimal JPEG: SOI + APP0 + EOI
    cover_path.write_bytes(
        b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
        b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
        b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9telecomvoice\n'
        b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00'
        b'\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b'
        b'\xff\xda\x00\x08\x01\x01\x00\x00?\x00\x7f\xff\xd9'
    )

    # Create a readme
    readme_path = album_dir / "README.txt"
    readme_path.write_text("This is a test album.\n")

    return album_dir
