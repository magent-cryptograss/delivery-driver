"""CLI interface for Delivery Driver."""

import os
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from . import __version__
from .album import scan_album
from .ipfs import IPFSConfig, check_ipfs_available, add_directory, pin_to_pinata, get_gateway_url
from .torrent import create_torrent, get_torrent_info
from .manifest import generate_manifest, write_manifest, format_duration, format_size


console = Console()


@click.group()
@click.version_option(version=__version__)
def main():
    """Delivery Driver - Distribute music via IPFS and BitTorrent."""
    pass


@main.command()
@click.argument('album_path', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option('--version', '-v', help='Release version (e.g., RC0, RC1, final)')
def scan(album_path: Path, version: str | None):
    """Scan an album directory and show its contents."""
    console.print(f"\n[bold]Scanning:[/bold] {album_path}\n")

    album = scan_album(album_path, version=version)

    # Album info
    console.print(f"[bold cyan]Album:[/bold cyan] {album.title or 'Unknown'}")
    console.print(f"[bold cyan]Artist:[/bold cyan] {album.artist or 'Unknown'}")
    if album.version:
        console.print(f"[bold cyan]Version:[/bold cyan] {album.version}")
    console.print()

    # Tracks table
    table = Table(title="Tracks")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="bold")
    table.add_column("Duration", justify="right")
    table.add_column("Format")
    table.add_column("Size", justify="right")

    for track in album.tracks:
        table.add_row(
            str(track.track_number or "-"),
            track.title or track.filename,
            format_duration(track.duration_seconds) if track.duration_seconds else "-",
            track.format.upper(),
            format_size(track.size_bytes),
        )

    console.print(table)
    console.print()

    # Summary
    console.print(f"[bold]Total:[/bold] {len(album.tracks)} tracks, "
                  f"{format_duration(album.total_duration)}, "
                  f"{format_size(album.total_size)}")

    if album.artwork:
        console.print(f"[bold]Artwork:[/bold] {len(album.artwork)} file(s)")

    if album.other_files:
        console.print(f"[bold]Other files:[/bold] {', '.join(f.name for f in album.other_files)}")


@main.command()
@click.argument('album_path', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option('--version', '-v', help='Release version (e.g., RC0, RC1, final)')
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output directory for generated files')
@click.option('--no-ipfs', is_flag=True, help='Skip IPFS upload')
@click.option('--no-torrent', is_flag=True, help='Skip torrent creation')
@click.option('--no-pinata', is_flag=True, help='Skip Pinata pinning')
@click.option('--compute-hashes', is_flag=True, help='Compute SHA256 hashes for all files')
@click.option('--ipfs-api', default='http://127.0.0.1:5001', help='IPFS API URL')
@click.option('--ipfs-gateway', default='https://ipfs.io', help='IPFS gateway URL')
def release(
    album_path: Path,
    version: str | None,
    output: Path | None,
    no_ipfs: bool,
    no_torrent: bool,
    no_pinata: bool,
    compute_hashes: bool,
    ipfs_api: str,
    ipfs_gateway: str,
):
    """
    Create a full release: IPFS upload, torrent, and manifest.

    This is the main command for distributing an album.
    """
    output = output or album_path.parent
    output.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold blue]🚚 Delivery Driver[/bold blue]\n")
    console.print(f"[bold]Album:[/bold] {album_path}")
    console.print(f"[bold]Output:[/bold] {output}\n")

    # Scan album
    with console.status("[bold green]Scanning album..."):
        album = scan_album(album_path, version=version)

    console.print(f"[green]✓[/green] Found {len(album.tracks)} tracks: {album.title or album_path.name}")

    # Compute hashes if requested
    if compute_hashes:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Computing checksums...", total=len(album.tracks))
            for track in album.tracks:
                track.compute_hash()
                progress.advance(task)
        console.print(f"[green]✓[/green] Computed SHA256 hashes")

    # IPFS upload
    ipfs_config = IPFSConfig(api_url=ipfs_api, gateway_url=ipfs_gateway)
    torrent_web_seeds = []

    if not no_ipfs:
        if not check_ipfs_available(ipfs_config):
            console.print("[yellow]⚠[/yellow] IPFS daemon not available, skipping IPFS upload")
            console.print(f"  (Tried: {ipfs_api})")
        else:
            with console.status("[bold green]Adding to IPFS..."):
                dir_result, file_results = add_directory(album_path, ipfs_config)
                album.ipfs_cid = dir_result.cid

                # Map file CIDs back to tracks
                file_cid_map = {r.name: r.cid for r in file_results}
                for track in album.tracks:
                    if track.filename in file_cid_map:
                        track.ipfs_cid = file_cid_map[track.filename]

            console.print(f"[green]✓[/green] Added to IPFS: [cyan]{album.ipfs_cid}[/cyan]")

            gateway_url = get_gateway_url(album.ipfs_cid, ipfs_config)
            console.print(f"  Gateway: {gateway_url}")
            torrent_web_seeds.append(gateway_url)

            # Pin to Pinata
            if not no_pinata:
                pinata_jwt = os.environ.get('PINATA_JWT')
                if pinata_jwt:
                    ipfs_config.pinata_jwt = pinata_jwt
                    with console.status("[bold green]Pinning to Pinata..."):
                        try:
                            pin_to_pinata(album.ipfs_cid, album.title or album_path.name, ipfs_config)
                            console.print(f"[green]✓[/green] Pinned to Pinata")
                        except Exception as e:
                            console.print(f"[yellow]⚠[/yellow] Pinata pinning failed: {e}")
                else:
                    console.print("[dim]  (Set PINATA_JWT to enable Pinata pinning)[/dim]")

    # Create torrent
    torrent_info = None
    if not no_torrent:
        torrent_name = f"{album_path.name}.torrent"
        torrent_path = output / torrent_name

        with console.status("[bold green]Creating torrent..."):
            create_torrent(
                album_path,
                output_path=torrent_path,
                web_seeds=torrent_web_seeds if torrent_web_seeds else None,
                comment=f"{album.artist} - {album.title}" if album.artist and album.title else None,
            )
            torrent_info = get_torrent_info(torrent_path)

        console.print(f"[green]✓[/green] Created torrent: {torrent_name}")
        console.print(f"  Info hash: [cyan]{torrent_info['info_hash']}[/cyan]")

    # Generate manifest
    with console.status("[bold green]Generating manifest..."):
        manifest = generate_manifest(album, torrent_info=torrent_info, include_hashes=compute_hashes)
        manifest_name = f"{album_path.name}-manifest"
        manifest_path = write_manifest(manifest, output / manifest_name, format='yaml')

    console.print(f"[green]✓[/green] Generated manifest: {manifest_path.name}")

    # Summary
    console.print("\n[bold green]🎉 Release complete![/bold green]\n")

    if album.ipfs_cid:
        console.print(f"[bold]IPFS CID:[/bold] {album.ipfs_cid}")
        console.print(f"[bold]IPFS URL:[/bold] ipfs://{album.ipfs_cid}")
        console.print(f"[bold]Gateway:[/bold] {get_gateway_url(album.ipfs_cid, ipfs_config)}")

    if torrent_info:
        console.print(f"\n[bold]Magnet link:[/bold]")
        console.print(f"  {torrent_info['magnet']}")


@main.command()
@click.argument('album_path', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output path for torrent file')
@click.option('--web-seed', '-w', multiple=True, help='Add web seed URL (can specify multiple)')
@click.option('--comment', '-c', help='Comment to embed in torrent')
def torrent(album_path: Path, output: Path | None, web_seed: tuple[str], comment: str | None):
    """Create a torrent file for an album."""
    console.print(f"\n[bold]Creating torrent for:[/bold] {album_path}\n")

    torrent_path = create_torrent(
        album_path,
        output_path=output,
        web_seeds=list(web_seed) if web_seed else None,
        comment=comment,
    )

    info = get_torrent_info(torrent_path)

    console.print(f"[green]✓[/green] Created: {torrent_path}")
    console.print(f"\n[bold]Info hash:[/bold] {info['info_hash']}")
    console.print(f"[bold]Size:[/bold] {format_size(info['size'])}")
    console.print(f"[bold]Files:[/bold] {len(info['files'])}")
    console.print(f"\n[bold]Magnet link:[/bold]")
    console.print(info['magnet'])


@main.command()
@click.argument('album_path', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option('--api', default='http://127.0.0.1:5001', help='IPFS API URL')
def ipfs(album_path: Path, api: str):
    """Add an album to IPFS."""
    config = IPFSConfig(api_url=api)

    if not check_ipfs_available(config):
        console.print(f"[red]✗[/red] IPFS daemon not available at {api}")
        raise SystemExit(1)

    console.print(f"\n[bold]Adding to IPFS:[/bold] {album_path}\n")

    with console.status("[bold green]Adding..."):
        dir_result, file_results = add_directory(album_path, config)

    console.print(f"[green]✓[/green] Added directory: [cyan]{dir_result.cid}[/cyan]")
    console.print(f"\n[bold]Gateway URL:[/bold] https://ipfs.io/ipfs/{dir_result.cid}")
    console.print(f"[bold]IPFS URL:[/bold] ipfs://{dir_result.cid}")

    if file_results:
        console.print(f"\n[bold]Files:[/bold]")
        for f in file_results:
            console.print(f"  {f.cid}  {f.name}")


if __name__ == '__main__':
    main()
