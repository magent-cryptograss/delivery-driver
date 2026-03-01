"""IPFS operations - add files and directories to IPFS."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import httpx


@dataclass
class IPFSConfig:
    """Configuration for IPFS connection."""
    api_url: str = "http://127.0.0.1:5001"
    gateway_url: str = "https://ipfs.io"
    pinata_jwt: str | None = None
    pinata_api_url: str = "https://api.pinata.cloud"


@dataclass
class AddResult:
    """Result of adding a file/directory to IPFS."""
    cid: str
    name: str
    size: int


def check_ipfs_available(config: IPFSConfig) -> bool:
    """Check if IPFS daemon is running and accessible."""
    try:
        response = httpx.post(
            f"{config.api_url}/api/v0/id",
            timeout=5.0
        )
        return response.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def add_file(path: Path, config: IPFSConfig) -> AddResult:
    """Add a single file to IPFS."""
    with open(path, 'rb') as f:
        response = httpx.post(
            f"{config.api_url}/api/v0/add",
            files={'file': (path.name, f)},
            params={'pin': 'true', 'quieter': 'true'},
            timeout=300.0  # Large files may take a while
        )
        response.raise_for_status()
        data = response.json()

    return AddResult(
        cid=data['Hash'],
        name=data['Name'],
        size=int(data['Size'])
    )


def add_directory(path: Path, config: IPFSConfig) -> tuple[AddResult, list[AddResult]]:
    """
    Add a directory to IPFS recursively.

    Returns:
        Tuple of (directory_result, list_of_file_results)
    """
    path = Path(path)

    # Use ipfs CLI for directory adds - the HTTP API is fiddly with multipart
    # This assumes `ipfs` CLI is available and configured
    try:
        result = subprocess.run(
            ['ipfs', 'add', '-r', '-Q', str(path)],
            capture_output=True,
            text=True,
            check=True
        )
        dir_cid = result.stdout.strip()
    except FileNotFoundError:
        # Fall back to HTTP API if CLI not available
        return _add_directory_http(path, config)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ipfs add failed: {e.stderr}")

    # Get the directory CID
    dir_result = AddResult(
        cid=dir_cid,
        name=path.name,
        size=0  # Will be filled in by ls
    )

    # List the directory to get individual file CIDs
    file_results = []
    try:
        ls_result = subprocess.run(
            ['ipfs', 'ls', dir_cid],
            capture_output=True,
            text=True,
            check=True
        )
        for line in ls_result.stdout.strip().split('\n'):
            if line:
                parts = line.split()
                if len(parts) >= 3:
                    cid = parts[0]
                    size = int(parts[1])
                    name = ' '.join(parts[2:])
                    file_results.append(AddResult(cid=cid, name=name, size=size))
    except subprocess.CalledProcessError:
        pass  # Non-fatal - we still have the directory CID

    return dir_result, file_results


def _add_directory_http(path: Path, config: IPFSConfig) -> tuple[AddResult, list[AddResult]]:
    """Add directory via HTTP API (fallback)."""
    file_results = []

    # Add each file individually first
    for file_path in path.rglob('*'):
        if file_path.is_file():
            result = add_file(file_path, config)
            file_results.append(result)

    # For the directory, we need to construct it with object patch
    # This is complex - for now, just return the files
    # A proper implementation would use MFS or object patch
    raise NotImplementedError(
        "Directory add via HTTP API not implemented. "
        "Please install ipfs CLI: https://docs.ipfs.tech/install/"
    )


def pin_to_pinata(cid: str, name: str, config: IPFSConfig) -> dict:
    """Pin an existing CID to Pinata for redundant hosting."""
    if not config.pinata_jwt:
        raise ValueError("Pinata JWT not configured")

    response = httpx.post(
        f"{config.pinata_api_url}/pinning/pinByHash",
        headers={
            "Authorization": f"Bearer {config.pinata_jwt}",
            "Content-Type": "application/json"
        },
        json={
            "hashToPin": cid,
            "pinataMetadata": {
                "name": name
            }
        },
        timeout=60.0
    )
    response.raise_for_status()
    return response.json()


def get_gateway_url(cid: str, config: IPFSConfig, filename: str | None = None) -> str:
    """Get a gateway URL for a CID."""
    url = f"{config.gateway_url}/ipfs/{cid}"
    if filename:
        url = f"{url}/{filename}"
    return url
