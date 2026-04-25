# API Reference

Complete reference for the FaceID REST API and WebSocket events.

---

- [Base URL](#base-url)
- [Authentication](#authentication)
  - [Session Authentication](#session-authentication)
  - [JWT Bearer Authentication](#jwt-bearer-authentication)
  - [Public Endpoints](#public-endpoints)
- [Error Format](#error-format)
- [Role Permissions](#role-permissions)
- [Endpoints](#endpoints)
  - [Auth](#auth)
  - [Faces](#faces)
  - [Enroll](#enroll)
  - [Stream](#stream)
  - [Logs](#logs)
  - [Stats](#stats)
  - [Cameras](#cameras)
  - [Settings](#settings)
  - [Users](#users)
- [WebSocket Events](#websocket-events)
- [Data Schemas](#data-schemas)

---

## Base URL

```
http://<host>:5000
```

REST API routes are prefixed `/api/`. Auth routes use `/auth/`. Page routes have no prefix.

---

## Authentication

The API supports two authentication methods simultaneously. Use whichever fits your client.

### Session Authentication

Used by the web browser. POST credentials to `/auth/login` — the server sets a signed session cookie that is sent automatically on subsequent requests.

```http
POST /auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "changeme",
  "remember": false
}
```

Successful response (`200`):

```json
{
  "success": true,
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "is_active": true,
    "created_at": "2026-04-25T10:00:00",
    "last_login": "2026-04-25T12:30:00",
    "face_count": 2
  }
}
```

### JWT Bearer Authentication

Used by the CLI and headless API clients. Exchange credentials for a token at `/auth/token`, then include the token in the `Authorization` header on every request.

```http
POST /auth/token
Content-Type: application/json

{
  "username": "admin",
  "password": "changeme"
}
```

Response (`200`):

```json
{
  "access_token": "eyJhbGci...",
  "user": { ... }
}
```

Using the token:

```http
GET /api/faces
Authorization: Bearer eyJhbGci...
```

Tokens do not expire by default. Treat them like passwords — store securely, never commit to source control.

### Public Endpoints

The following endpoints do not require authentication so that the login page camera preview works:

- `GET /api/video` — MJPEG stream
- `GET /api/snapshot` — single JPEG frame
- `GET /auth/login` — login page (GET only)
- `POST /auth/login` — submit credentials
- `POST /auth/token` — issue a JWT
- `GET /auth/face-login` — camera-based authentication

---

## Error Format

All error responses return JSON with a single `error` field:

```json
{ "error": "Description of what went wrong." }
```

Common HTTP status codes:

| Code | Meaning |
|---|---|
| `400` | Bad request — missing or invalid parameters |
| `401` | Authentication required |
| `403` | Insufficient permissions for your role |
| `404` | Resource not found |
| `409` | Conflict — e.g. username already exists |
| `500` | Server error |

---

## Role Permissions

| Role | Description |
|---|---|
| `admin` | Full access to all endpoints |
| `operator` | Can enroll faces, delete faces, change camera, update settings |
| `viewer` | Read-only — can view faces, logs, stats, and the live feed |

Routes that require a specific minimum role return `403` if the authenticated user's role does not qualify.

---

## Endpoints

### Auth

#### GET /auth/login

Renders the login page HTML. Redirects to `/` if already authenticated.

---

#### POST /auth/login

Authenticate with a username and password. Sets a session cookie.

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `username` | string | Yes | Account username |
| `password` | string | Yes | Account password |
| `remember` | boolean | No | Extend session cookie lifetime (default: `false`) |

**Responses:**

| Status | Description |
|---|---|
| `200` | Login successful — session cookie set |
| `400` | Username or password missing |
| `401` | Invalid credentials |
| `403` | Account is disabled |

---

#### POST /auth/token

Issue a JWT for CLI or API use.

**Request body:** same fields as `POST /auth/login` (`remember` is ignored).

**Response (`200`):**
```json
{
  "access_token": "eyJhbGci...",
  "user": { "id": 1, "username": "admin", "role": "admin", ... }
}
```

**Errors:** `401` invalid credentials, `403` account disabled.

---

#### GET /auth/face-login

Capture a frame from the live camera and match it against all enrolled face encodings. If a match is found and the encoding is linked to a user account, that user is logged in via session.

**Response (`200`) — match found:**
```json
{ "success": true, "user": { "id": 1, "username": "alice", ... } }
```

**Response (`200`) — match found but encoding not linked to a user account:**
```json
{ "success": true, "name": "alice" }
```

**Response (`200`) — no match or no face detected:**
```json
{ "success": false, "message": "Face not recognised" }
```

**Errors:** `500` if the camera is unavailable.

---

#### GET /auth/logout

Invalidate the current session. Redirects to `/auth/login`.

---

### Faces

#### GET /api/faces

List all enrolled faces grouped by name with the number of stored encodings.

**Auth:** Any authenticated user.

**Response (`200`):**
```json
{
  "faces": [
    { "name": "Alice", "count": 3 },
    { "name": "Bob", "count": 1 }
  ]
}
```

---

#### DELETE /api/faces/\<name\>

Remove all encodings stored under the given name. The in-memory recognizer is refreshed immediately.

**Auth:** `admin` or `operator`.

**URL parameter:** `name` — the exact name string (case-sensitive).

**Response (`200`):**
```json
{ "message": "'Alice' removed (3 encodings deleted)" }
```

**Errors:** `404` if no encodings exist for that name.

---

### Enroll

#### POST /api/enroll

Detect a face in an uploaded image and store its encoding in the database. If the `name` matches an existing username, the encoding is linked to that user account.

**Auth:** `admin` or `operator`.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Name to associate with the face |
| `image` | file | Yes | JPEG or PNG image containing exactly one face |

**Response (`200`):**
```json
{ "message": "'Alice' enrolled successfully." }
```

**Errors:**

| Status | Reason |
|---|---|
| `400` | `name` or `image` field missing |
| `400` | No face detected in the image |

---

### Stream

#### GET /api/video

MJPEG video stream from the active camera. Recognition bounding boxes are drawn on each frame. When no camera is connected, a placeholder image is streamed instead.

**Auth:** Public.

**Content-Type:** `multipart/x-mixed-replace; boundary=frame`

Embed directly in an `<img>` tag:
```html
<img src="/api/video" />
```

---

#### GET /api/snapshot

Return a single JPEG frame from the current camera without recognition overlays.

**Auth:** Public.

**Content-Type:** `image/jpeg`

**Errors:** `500` if the camera is unavailable or the frame cannot be encoded.

---

#### GET /api/reload

Force the recognition service to reload all face encodings from the database. Call this after enrolling faces via an external process.

**Auth:** Public.

**Response (`200`):**
```json
{ "message": "Encodings reloaded." }
```

---

### Logs

#### GET /api/logs

Return paginated recognition events, ordered newest first.

**Auth:** Any authenticated user.

**Query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `limit` | integer | `100` | Number of events to return (max `500`) |
| `offset` | integer | `0` | Number of events to skip for pagination |
| `name` | string | — | Filter events by person name (case-insensitive, partial match) |

**Response (`200`):**
```json
{
  "events": [
    {
      "id": 42,
      "name": "Alice",
      "confidence": 87,
      "timestamp": "2026-04-25T14:32:10",
      "user_id": 3
    }
  ],
  "total": 142
}
```

---

#### DELETE /api/logs

Clear all recognition log entries from the database.

**Auth:** `admin` only.

**Response (`200`):**
```json
{ "message": "Cleared 142 log entries." }
```

---

#### GET /api/logs/export

Download all recognition events as a CSV file.

**Auth:** Any authenticated user.

**Response:** Attachment download with `Content-Type: text/csv`.

CSV columns: `id`, `name`, `confidence`, `timestamp`

---

### Stats

#### GET /api/stats

Return system statistics for the dashboard.

**Auth:** Any authenticated user.

**Response (`200`):**
```json
{
  "enrolled_count": 4,
  "today_recognitions": 17,
  "camera_connected": true,
  "hourly": [
    { "hour": "09", "count": 3 },
    { "hour": "10", "count": 7 }
  ],
  "per_person": [
    { "name": "Alice", "count": 12 },
    { "name": "Bob", "count": 5 }
  ]
}
```

- `hourly` — per-hour recognition counts for the last 24 hours
- `per_person` — top 10 most-recognised people across all time

---

### Cameras

#### GET /api/cameras

List all camera device indices that OpenCV can open, plus the currently active device.

**Auth:** Any authenticated user.

**Response (`200`):**
```json
{
  "cameras": [0, 1],
  "active": 0,
  "connected": true
}
```

---

#### POST /api/cameras/select

Switch the active camera device. The current camera is released before the new one is opened.

**Auth:** `admin` or `operator`.

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `index` | integer | Yes | Camera device index to activate |

**Response (`200`):**
```json
{ "message": "Switched to camera 1.", "connected": true }
```

**Errors:** `400` if the index is not an integer or the camera cannot be opened.

---

### Settings

#### POST /api/settings

Update recognition settings at runtime. Changes take effect immediately without restarting.

**Auth:** `admin` or `operator`.

**Request body (all fields optional):**

| Field | Type | Range | Description |
|---|---|---|---|
| `tolerance` | float | `0.30`–`0.70` | Recognition match threshold. Values outside range are clamped. |
| `show_landmarks` | boolean | — | Overlay facial landmark points on the video stream |

**Response (`200`):**
```json
{
  "message": "Settings updated.",
  "applied": {
    "tolerance": 0.45,
    "show_landmarks": false
  }
}
```

**Errors:** `400` if the body contains no recognised fields, or `tolerance` is not a number.

---

### Users

#### GET /api/users

List all user accounts ordered by creation date (newest first).

**Auth:** `admin` only.

**Response (`200`):**
```json
{
  "users": [
    {
      "id": 2,
      "username": "bob",
      "email": "bob@example.com",
      "role": "operator",
      "is_active": true,
      "created_at": "2026-04-25T10:00:00",
      "last_login": "2026-04-25T13:45:00",
      "face_count": 1
    }
  ]
}
```

---

#### POST /api/users

Create a new user account.

**Auth:** `admin` only.

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `username` | string | Yes | Unique username |
| `password` | string | Yes | Plain-text password (hashed server-side) |
| `role` | string | No | `admin`, `operator`, or `viewer` (default: `operator`) |
| `email` | string | No | Optional email address |

**Response (`201`):**
```json
{
  "message": "User 'bob' created.",
  "user": { "id": 2, "username": "bob", ... }
}
```

**Errors:** `400` missing username/password, `400` invalid role, `409` username already exists.

---

#### PATCH /api/users/\<id\>

Update an existing user account. All body fields are optional — only send what you want to change.

**Auth:** `admin` only.

**Request body:**

| Field | Type | Description |
|---|---|---|
| `role` | string | New role (`admin`, `operator`, `viewer`) |
| `password` | string | New password (plain-text, hashed server-side) |
| `email` | string | New email address (send `null` to clear) |
| `is_active` | boolean | Enable or disable the account |

**Response (`200`):**
```json
{
  "message": "User updated.",
  "user": { ... }
}
```

**Errors:** `400` invalid role, `404` user not found.

---

#### DELETE /api/users/\<id\>

Delete a user account. The currently authenticated user cannot delete their own account.

**Auth:** `admin` only.

**Response (`200`):**
```json
{ "message": "User 'bob' deleted." }
```

**Errors:** `400` if trying to delete your own account, `404` user not found.

---

## WebSocket Events

The server uses Flask-SocketIO (eventlet). Connect to the root namespace at `ws://<host>:5000/`.

### Server → Client

#### `recognition`

Emitted every time a known face is recognised (subject to an 8-second per-person cooldown).

```json
{
  "name": "Alice",
  "confidence": 87,
  "timestamp": "2026-04-25T14:32:10.123456"
}
```

Use this to push live recognition alerts to the UI without polling.

---

## Data Schemas

### User object

```json
{
  "id": 1,
  "username": "alice",
  "email": "alice@example.com",
  "role": "operator",
  "is_active": true,
  "created_at": "2026-04-20T09:00:00",
  "last_login": "2026-04-25T14:00:00",
  "face_count": 2
}
```

### Recognition event object

```json
{
  "id": 99,
  "name": "Alice",
  "confidence": 87,
  "timestamp": "2026-04-25T14:32:10",
  "user_id": 3
}
```

- `confidence` is an integer from `0` to `100` — the percentage equivalent of `(1 - face_distance) × 100`
- `user_id` is `null` if the face encoding is not linked to a user account

### Face object

```json
{
  "name": "Alice",
  "count": 3
}
```

- `count` is the number of distinct encoding vectors stored for that name. More encodings generally improve recognition accuracy.
