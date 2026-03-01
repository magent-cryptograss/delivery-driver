"""Tests for IPFS operations."""

import pytest
from unittest.mock import patch, MagicMock

from delivery_driver.ipfs import (
    IPFSConfig,
    check_ipfs_available,
    add_file,
    get_gateway_url,
    pin_to_pinata,
    AddResult,
)


class TestIPFSConfig:
    """Tests for IPFSConfig."""

    def test_default_values(self):
        """Should have sensible defaults."""
        config = IPFSConfig()

        assert config.api_url == "http://127.0.0.1:5001"
        assert config.gateway_url == "https://ipfs.io"
        assert config.pinata_jwt is None

    def test_custom_values(self):
        """Should accept custom values."""
        config = IPFSConfig(
            api_url="http://custom:5001",
            gateway_url="https://my-gateway.com",
            pinata_jwt="test-jwt"
        )

        assert config.api_url == "http://custom:5001"
        assert config.gateway_url == "https://my-gateway.com"
        assert config.pinata_jwt == "test-jwt"


class TestCheckIPFSAvailable:
    """Tests for check_ipfs_available function."""

    @patch('delivery_driver.ipfs.httpx.post')
    def test_returns_true_when_available(self, mock_post):
        """Should return True when IPFS daemon responds."""
        mock_post.return_value.status_code = 200

        config = IPFSConfig()
        result = check_ipfs_available(config)

        assert result is True
        mock_post.assert_called_once()

    @patch('delivery_driver.ipfs.httpx.post')
    def test_returns_false_on_connection_error(self, mock_post):
        """Should return False when connection fails."""
        import httpx
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        config = IPFSConfig()
        result = check_ipfs_available(config)

        assert result is False

    @patch('delivery_driver.ipfs.httpx.post')
    def test_returns_false_on_timeout(self, mock_post):
        """Should return False when connection times out."""
        import httpx
        mock_post.side_effect = httpx.TimeoutException("Timeout")

        config = IPFSConfig()
        result = check_ipfs_available(config)

        assert result is False


class TestAddFile:
    """Tests for add_file function."""

    @patch('delivery_driver.ipfs.httpx.post')
    def test_adds_file_and_returns_cid(self, mock_post, minimal_flac):
        """Should add file and return CID."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'Hash': 'QmTestHash123',
            'Name': 'test.wav',
            'Size': '12345'
        }
        mock_post.return_value = mock_response

        config = IPFSConfig()
        result = add_file(minimal_flac, config)

        assert isinstance(result, AddResult)
        assert result.cid == 'QmTestHash123'
        assert result.name == 'test.wav'
        assert result.size == 12345


class TestGetGatewayUrl:
    """Tests for get_gateway_url function."""

    def test_basic_url(self):
        """Should construct basic gateway URL."""
        config = IPFSConfig(gateway_url="https://ipfs.io")

        url = get_gateway_url("QmTestHash", config)

        assert url == "https://ipfs.io/ipfs/QmTestHash"

    def test_url_with_filename(self):
        """Should include filename when provided."""
        config = IPFSConfig(gateway_url="https://ipfs.io")

        url = get_gateway_url("QmTestHash", config, filename="track.flac")

        assert url == "https://ipfs.io/ipfs/QmTestHash/track.flac"

    def test_custom_gateway(self):
        """Should use custom gateway URL."""
        config = IPFSConfig(gateway_url="https://my-gateway.com")

        url = get_gateway_url("QmTestHash", config)

        assert url == "https://my-gateway.com/ipfs/QmTestHash"


class TestPinToPinata:
    """Tests for pin_to_pinata function."""

    @patch('delivery_driver.ipfs.httpx.post')
    def test_pins_cid(self, mock_post):
        """Should pin CID to Pinata."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'id': 'pin-123', 'status': 'pinned'}
        mock_post.return_value = mock_response

        config = IPFSConfig(pinata_jwt="test-jwt")
        result = pin_to_pinata("QmTestHash", "Test Album", config)

        assert result == {'id': 'pin-123', 'status': 'pinned'}

        # Verify request
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert 'Bearer test-jwt' in str(call_args)

    def test_raises_without_jwt(self):
        """Should raise error when JWT not configured."""
        config = IPFSConfig()  # No JWT

        with pytest.raises(ValueError, match="Pinata JWT not configured"):
            pin_to_pinata("QmTestHash", "Test Album", config)
