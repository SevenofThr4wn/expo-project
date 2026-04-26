#!/usr/bin/env python3
"""FaceID CLI — headless interface for Raspberry Pi deployments."""

import json
import os
import sys
import time

import click
import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

CONFIG_DIR = os.path.expanduser("~/.faceid")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DEFAULT_SERVER = "http://127.0.0.1:5000"


# ── Config helpers ─────────────────────────────────────────────────────────────

def _load_cfg() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def _save_cfg(data: dict):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _server(cfg: dict) -> str:
    return cfg.get("server", DEFAULT_SERVER)


def _headers(cfg: dict) -> dict:
    token = cfg.get("token")
    if not token:
        console.print("[red]Not logged in. Run: [bold]faceid login[/bold][/red]")
        sys.exit(1)
    return {"Authorization": f"Bearer {token}"}


# ── Root group ─────────────────────────────────────────────────────────────────

@click.group()
@click.option("--server", default=None, help="Override server URL")
@click.pass_context
def cli(ctx, server):
    """FaceID — facial recognition system CLI."""
    ctx.ensure_object(dict)
    cfg = _load_cfg()
    if server:
        cfg["server"] = server
    ctx.obj["cfg"] = cfg


# ── Auth ───────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--username", prompt=True)
@click.option("--password", prompt=True, hide_input=True)
@click.pass_context
def login(ctx, username, password):
    """Authenticate and store a session token."""
    cfg = ctx.obj["cfg"]
    try:
        r = requests.post(
            f"{_server(cfg)}/auth/token",
            json={"username": username, "password": password},
            timeout=10,
        )
        d = r.json()
        if r.status_code != 200:
            console.print(f"[red]Login failed: {d.get('error', 'Unknown error')}[/red]")
            return
        cfg["token"] = d["access_token"]
        cfg.setdefault("server", DEFAULT_SERVER)
        _save_cfg(cfg)
        u = d["user"]
        console.print(
            f"[green]Logged in as [bold]{u['username']}[/bold] "
            f"([dim]{u['role']}[/dim])[/green]"
        )
    except requests.exceptions.ConnectionError:
        console.print(f"[red]Could not connect to {_server(cfg)}[/red]")


# ── Status ─────────────────────────────────────────────────────────────────────

@cli.command()
@click.pass_context
def status(ctx):
    """Show system status."""
    cfg = ctx.obj["cfg"]
    try:
        r = requests.get(f"{_server(cfg)}/api/stats", headers=_headers(cfg), timeout=10)
        d = r.json()
        cam = "[green]Connected[/green]" if d["camera_connected"] else "[red]Disconnected[/red]"
        console.print(Panel.fit(
            f"[bold]Enrolled Faces:[/bold]       {d['enrolled_count']}\n"
            f"[bold]Recognitions Today:[/bold]   {d['today_recognitions']}\n"
            f"[bold]Camera:[/bold]               {cam}",
            title="[bold cyan]FaceID Status[/bold cyan]",
        ))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


# ── Face management ────────────────────────────────────────────────────────────

@cli.command("list-faces")
@click.pass_context
def list_faces(ctx):
    """List all enrolled faces."""
    cfg = ctx.obj["cfg"]
    r = requests.get(f"{_server(cfg)}/api/faces", headers=_headers(cfg), timeout=10)
    faces = r.json().get("faces", [])
    if not faces:
        console.print("[yellow]No faces enrolled.[/yellow]")
        return
    t = Table(title="Enrolled Faces")
    t.add_column("Name", style="cyan")
    t.add_column("Encodings", justify="right")
    for f in faces:
        t.add_row(f["name"], str(f["count"]))
    console.print(t)


@cli.command("delete-face")
@click.argument("name")
@click.pass_context
def delete_face(ctx, name):
    """Delete all encodings for a person."""
    cfg = ctx.obj["cfg"]
    if not click.confirm(f"Delete all encodings for '{name}'?"):
        return
    r = requests.delete(
        f"{_server(cfg)}/api/faces/{name}", headers=_headers(cfg), timeout=10
    )
    d = r.json()
    if r.status_code == 200:
        console.print(f"[green]{d['message']}[/green]")
    else:
        console.print(f"[red]{d.get('error', 'Failed')}[/red]")


@cli.command()
@click.argument("name")
@click.option("--frames", default=3, show_default=True, help="Frames to capture")
@click.pass_context
def enroll(ctx, name, frames):
    """Enroll a face by capturing from the camera."""
    cfg = ctx.obj["cfg"]
    srv = _server(cfg)
    headers = _headers(cfg)

    console.print(f"[cyan]Enrolling [bold]{name}[/bold] with {frames} frame(s)[/cyan]")
    console.print("[yellow]Position your face in front of the camera.[/yellow]\n")

    enrolled = 0
    for i in range(frames):
        time.sleep(1.2)
        try:
            snap = requests.get(f"{srv}/api/snapshot", headers=headers, timeout=10)
            if snap.status_code != 200:
                console.print(f"  Frame {i+1}: [red]snapshot failed[/red]")
                continue
            er = requests.post(
                f"{srv}/api/enroll",
                headers=headers,
                data={"name": name},
                files={"image": (f"frame_{i}.jpg", snap.content, "image/jpeg")},
                timeout=20,
            )
            d = er.json()
            if er.status_code == 200:
                enrolled += 1
                console.print(f"  Frame {i+1}: [green]enrolled[/green]")
            else:
                console.print(f"  Frame {i+1}: [yellow]{d.get('error', 'failed')}[/yellow]")
        except Exception as e:
            console.print(f"  Frame {i+1}: [red]{e}[/red]")

    console.print(
        f"\n[bold]{'[green]' if enrolled else '[red]'}Enrolled {enrolled}/{frames} frames for '{name}'[/bold]"
    )


# ── Logs ───────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--limit", default=20, show_default=True)
@click.option("--name", default=None, help="Filter by person name")
@click.pass_context
def logs(ctx, limit, name):
    """Show recent recognition logs."""
    from datetime import datetime

    cfg = ctx.obj["cfg"]
    params = {"limit": limit}
    if name:
        params["name"] = name
    r = requests.get(
        f"{_server(cfg)}/api/logs", headers=_headers(cfg), params=params, timeout=10
    )
    events = r.json().get("events", [])
    if not events:
        console.print("[yellow]No recognition events.[/yellow]")
        return
    t = Table(title=f"Recognition Log (last {limit})")
    t.add_column("Name", style="cyan")
    t.add_column("Confidence", justify="right")
    t.add_column("Time", style="dim")
    for e in events:
        c = e["confidence"]
        cs = f"[green]{c}%[/green]" if c >= 70 else f"[yellow]{c}%[/yellow]"
        ts = datetime.fromisoformat(e["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        t.add_row(e["name"], cs, ts)
    console.print(t)


# ── User management ────────────────────────────────────────────────────────────

@cli.group()
def users():
    """Manage user accounts (admin only)."""


@users.command("list")
@click.pass_context
def users_list(ctx):
    cfg = ctx.obj["cfg"]
    r = requests.get(f"{_server(cfg)}/api/users", headers=_headers(cfg), timeout=10)
    if r.status_code == 403:
        console.print("[red]Admin access required.[/red]")
        return
    t = Table(title="User Accounts")
    t.add_column("ID", style="dim")
    t.add_column("Username", style="cyan")
    t.add_column("Role")
    t.add_column("Status")
    t.add_column("Faces", justify="right")
    role_color = {"admin": "red", "operator": "yellow", "viewer": "white"}
    for u in r.json().get("users", []):
        rc = role_color.get(u["role"], "white")
        st = "[green]Active[/green]" if u["is_active"] else "[red]Disabled[/red]"
        t.add_row(str(u["id"]), u["username"], f"[{rc}]{u['role']}[/{rc}]", st, str(u["face_count"]))
    console.print(t)


@users.command("create")
@click.option("--username", prompt=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@click.option("--role", type=click.Choice(["admin", "operator", "viewer"]), default="operator")
@click.pass_context
def users_create(ctx, username, password, role):
    cfg = ctx.obj["cfg"]
    r = requests.post(
        f"{_server(cfg)}/api/users",
        headers=_headers(cfg),
        json={"username": username, "password": password, "role": role},
        timeout=10,
    )
    d = r.json()
    if r.status_code == 201:
        console.print(f"[green]{d['message']}[/green]")
    else:
        console.print(f"[red]{d.get('error', 'Failed')}[/red]")


@users.command("delete")
@click.argument("username")
@click.pass_context
def users_delete(ctx, username):
    cfg = ctx.obj["cfg"]
    r = requests.get(f"{_server(cfg)}/api/users", headers=_headers(cfg), timeout=10)
    user = next((u for u in r.json().get("users", []) if u["username"] == username), None)
    if not user:
        console.print(f"[red]User '{username}' not found.[/red]")
        return
    if not click.confirm(f"Delete user '{username}'?"):
        return
    r2 = requests.delete(
        f"{_server(cfg)}/api/users/{user['id']}", headers=_headers(cfg), timeout=10
    )
    d = r2.json()
    if r2.status_code == 200:
        console.print(f"[green]{d['message']}[/green]")
    else:
        console.print(f"[red]{d.get('error', 'Failed')}[/red]")


# ── Server ─────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=5000, show_default=True)
@click.option("--debug", is_flag=True)
def server(host, port, debug):
    """Start the FaceID web server."""
    console.print(f"[cyan]Starting FaceID server on {host}:{port}[/cyan]")
    from app import create_app
    from app.extensions import socketio as sio

    application = create_app()
    sio.run(application, host=host, port=port, debug=debug)


if __name__ == "__main__":
    cli()
