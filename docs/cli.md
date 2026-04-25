# CLI Reference

`cli.py` is a headless command-line interface for the FaceID system. It communicates with a running FaceID server over HTTP using JWT tokens — no browser required.

---

- [Requirements](#requirements)
- [Config File](#config-file)
- [Global Options](#global-options)
- [Commands](#commands)
  - [login](#login)
  - [status](#status)
  - [list-faces](#list-faces)
  - [enroll](#enroll)
  - [delete-face](#delete-face)
  - [logs](#logs)
  - [users](#users)
    - [users list](#users-list)
    - [users create](#users-create)
    - [users delete](#users-delete)
  - [server](#server)

---

## Requirements

The CLI uses only packages already in `requirements.txt` — no separate install needed if you have the full virtual environment active.

For a minimal install (e.g. on a Pi without the ML libraries):

```bash
pip install click requests rich
```

---

## Config File

On first `login`, the CLI writes a config file to:

```
~/.faceid/config.json
```

It stores the server URL and the JWT token. Example contents:

```json
{
  "server": "http://localhost:5000",
  "token": "eyJhbGci..."
}
```

The token grants the same permissions as the account used to log in. Delete the file or run `login` again to switch accounts.

---

## Global Options

```
python cli.py [OPTIONS] COMMAND
```

| Option | Description |
|---|---|
| `--server URL` | Override the server URL for this invocation only. Does not update the config file. |

**Example:**
```bash
python cli.py --server http://192.168.1.50:5000 status
```

---

## Commands

### login

Authenticate with a username and password and store a JWT locally.

```bash
python cli.py login
```

Prompts for `username` and `password` interactively (password input is hidden).

On success, the token is saved to `~/.faceid/config.json`. All subsequent commands use this token until you run `login` again.

**Example:**
```
$ python cli.py login
Username: admin
Password:
Logged in as admin (admin)
```

---

### status

Show a summary of the current system state.

```bash
python cli.py status
```

Displays enrolled face count, today's recognition count, and camera connection status.

**Example output:**
```
╭──────────── FaceID Status ────────────╮
│ Enrolled Faces:       4               │
│ Recognitions Today:   17              │
│ Camera:               Connected       │
╰───────────────────────────────────────╯
```

---

### list-faces

Print a table of all enrolled faces and how many encodings each has.

```bash
python cli.py list-faces
```

**Example output:**
```
        Enrolled Faces
┌──────────┬───────────┐
│ Name     │ Encodings │
├──────────┼───────────┤
│ Alice    │         3 │
│ Bob      │         1 │
└──────────┴───────────┘
```

More encodings per person generally improves recognition accuracy.

---

### enroll

Enroll a face by capturing snapshots directly from the server's camera.

```bash
python cli.py enroll NAME [OPTIONS]
```

| Argument / Option | Description |
|---|---|
| `NAME` | Name to enroll (required, positional) |
| `--frames N` | Number of frames to capture (default: `3`) |

The command captures one snapshot per second, sends each to `POST /api/enroll`, and reports success or failure per frame.

**Tips:**
- Stand still, face the camera directly, and ensure good lighting.
- Use `--frames 5` or more to build a richer encoding set.
- The name must exactly match a username to link the encoding to a user account.

**Example:**
```bash
python cli.py enroll "Alice" --frames 5
```
```
Enrolling Alice with 5 frame(s)
Position your face in front of the camera.

  Frame 1: enrolled
  Frame 2: enrolled
  Frame 3: enrolled
  Frame 4: No face detected in image. Try better lighting or a clearer angle.
  Frame 5: enrolled

Enrolled 4/5 frames for 'Alice'
```

---

### delete-face

Delete all encodings for a named person and prompt for confirmation.

```bash
python cli.py delete-face NAME
```

| Argument | Description |
|---|---|
| `NAME` | Name to delete (required, positional, case-sensitive) |

**Example:**
```bash
python cli.py delete-face "Alice"
```
```
Delete all encodings for 'Alice'? [y/N]: y
'Alice' removed (3 encodings deleted)
```

---

### logs

Display recent recognition events in a table.

```bash
python cli.py logs [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--limit N` | `20` | Number of events to display |
| `--name TEXT` | — | Filter events by person name (partial match) |

Confidence is colour-coded: **green** for ≥ 70%, **yellow** for < 70%.

**Example:**
```bash
python cli.py logs --limit 10 --name "Alice"
```
```
      Recognition Log (last 10)
┌────────┬───────────┬─────────────────────┐
│ Name   │Confidence │ Time                │
├────────┼───────────┼─────────────────────┤
│ Alice  │       87% │ 2026-04-25 14:32:10 │
│ Alice  │       91% │ 2026-04-25 13:15:42 │
└────────┴───────────┴─────────────────────┘
```

---

### users

A command group for managing user accounts. All sub-commands require an `admin` account.

```bash
python cli.py users COMMAND
```

#### users list

Print a table of all user accounts.

```bash
python cli.py users list
```

**Example output:**
```
                User Accounts
┌────┬──────────┬──────────┬────────┬───────┐
│ ID │ Username │ Role     │ Status │ Faces │
├────┼──────────┼──────────┼────────┼───────┤
│  1 │ admin    │ admin    │ Active │     0 │
│  2 │ alice    │ operator │ Active │     3 │
│  3 │ bob      │ viewer   │ Active │     1 │
└────┴──────────┴──────────┴────────┴───────┘
```

Role colours: **red** = admin, **yellow** = operator, **white** = viewer.

---

#### users create

Create a new user account interactively.

```bash
python cli.py users create [OPTIONS]
```

| Option | Description |
|---|---|
| `--username TEXT` | Username (prompted if not provided) |
| `--password TEXT` | Password (prompted with confirmation if not provided) |
| `--role [admin\|operator\|viewer]` | Role (default: `operator`) |

**Example:**
```bash
python cli.py users create --role viewer
```
```
Username: charlie
Password:
Repeat for confirmation:
User 'charlie' created.
```

---

#### users delete

Delete a user account by username with confirmation prompt.

```bash
python cli.py users delete USERNAME
```

| Argument | Description |
|---|---|
| `USERNAME` | Username to delete (required, positional) |

The command first fetches the user list to resolve the username to an ID, then sends the delete request.

**Example:**
```bash
python cli.py users delete charlie
```
```
Delete user 'charlie'? [y/N]: y
User 'charlie' deleted.
```

---

### server

Start the FaceID web server from the CLI. Useful for deployments where you want a single entry point.

```bash
python cli.py server [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--host TEXT` | `0.0.0.0` | Interface to bind to |
| `--port INTEGER` | `5000` | Port to listen on |
| `--debug` | Off | Enable Flask debug mode (development only) |

**Example:**
```bash
python cli.py server --port 8080 --debug
```

> For production deployments, use the Docker image which runs gunicorn instead of this command.
