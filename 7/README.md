# Lesson 7: user authentication

Two authentication implementations are available: `app/utilities.py` uses
pwdlib with Argon2 and bcrypt support, while `app/authentication.py` uses bcrypt
directly. Both have separate routes in `app/router/` and share the same
PostgreSQL users through SQLAlchemy, not the tutorial's
in-memory user dictionary. Install the dependencies in `../requirements.txt`,
including `pwdlib[argon2,bcrypt]` for password hashing.

## Application structure

`app/main.py` creates the FastAPI application, keeps the existing database startup
setup, and registers the routers with `app.include_router()`.
Endpoint declarations live in the `app/router/` package:

- `users.py`: `/users`, `/login`, and `/users/me` using `app/utilities.py`.
- `authentication.py`: `/auth/users`, `/auth/login`, and `/auth/users/me` using
  `app/authentication.py`.
- `courses.py`: course CRUD endpoints.
- `models.py`: model listing and creation endpoints.
- `root.py`: the `/` greeting endpoint.

The refactor does not change endpoint URLs, JSON login bodies, or responses.

## Run

Start PostgreSQL using the existing configuration in `app/database.py`. From this
directory, set a random JWT signing key and start the application (PowerShell):

```powershell
$env:JWT_SECRET_KEY = & ..\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Keep the key secret and reuse the same key across restarts and application
workers. Generating a new key invalidates previously issued tokens. The application
refuses to start without a key; use a randomly generated key of at least 32 bytes.
Both authentication modules load `7/.env` without overriding existing environment
variables. Existing tables are not migrated by `create_all()`.

## Logging

Application logs are written to the console (stderr) using Python's standard
`logging` module. Each entry includes a timestamp, severity, and module name.
Requests include the method, route template, status code, and time to response
in milliseconds. Authentication outcomes, course changes, and database startup
are also logged. Database session details are available at `DEBUG` level.

The default level is `INFO`. Set `LOG_LEVEL` in `7/.env` or in PowerShell before
starting the server:

```powershell
$env:LOG_LEVEL = "DEBUG"
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --no-access-log
```

Supported levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`.
Invalid levels fall back to `INFO` with a warning. Application logging does not
change Uvicorn or third-party logging settings; `--no-access-log` avoids duplicate
access logs and Uvicorn logging raw URLs with query parameters.

Application logs omit request/response bodies, headers, query strings, and actual
path parameter values. Exceptions retain traceback locations and their type but
omit their messages, which can contain SQL parameters or credentials. Uvicorn and
third-party error logs are independent and are not sanitized by this formatter.

## Endpoints

| Method | Path | Input | Success |
| --- | --- | --- | --- |
| POST | `/users` | JSON: `username`, `email`, `password` | 201: `id`, `username`, `email` |
| GET | `/users/` | Bearer token; optional `skip`, `limit`, `search` | 200: a page of users with nested `courses` |
| GET | `/courses/` | Optional `skip`, `limit` | 200: a page of courses with nested `instructor` |
| GET | `/courses/{course_id}` | Course ID | 200: a course with nested `instructor` |
| POST | `/login` | JSON: `email`, `password` | 200: `access_token`, `token_type` |
| GET | `/users/me` | `Authorization: Bearer <access_token>` | 200: `id`, `username`, `email` |

### List users with courses

`GET /users/` requires a valid bearer token and returns a page of users ordered by ID.
Each user includes `id`, `username`, `email`, and a `courses` array; users without
courses have an empty array. Password hashes are never included. Courses are
loaded in batches rather than with a separate database query for every user.
The optional `search` parameter matches a substring of the username or email
before pagination. Omitting `search`, or supplying an empty value, leaves the
results unfiltered; a search with no matches returns `[]`.

```json
[
  {
    "id": 1,
    "username": "alice",
    "email": "alice@example.com",
    "courses": [
      {"id": 1, "name": "FastAPI", "description": "Tutorial", "price": 10.0, "instructor_id": 1}
    ]
  }
]
```

The endpoint returns `[]` when there are no users and `401` for missing or invalid
credentials. A course's `description` and `price` may be `null`, matching the
database model. Existing registration and current-user response formats are
unchanged. Any authenticated user can access this tutorial endpoint; add an
administrator permission check before using it as a private directory in production.

### Pagination

Both `GET /users/` and `GET /courses/` accept these optional query parameters:

| Parameter | Default | Allowed values |
| --- | --- | --- |
| `skip` | `0` | Integer greater than or equal to `0` |
| `limit` | `20` | Integer from `1` to `100` |

```text
GET /users/?skip=0&limit=20
GET /users/?skip=20&limit=20
GET /courses/?skip=0&limit=20
GET /courses/?skip=20&limit=20
```

Results are ordered by ascending ID and remain JSON arrays. Requests without
pagination parameters now return only the first 20 records, not every record.
Advance `skip` by `limit` to fetch subsequent pages; an offset past the end returns
`[]`, and the last page may contain fewer than `limit` records. Invalid parameters
return `422`. User pagination limits users only: each returned user's complete
`courses` array is still included. Users still require a bearer token; courses
remain public. No database migration is needed.

### Fetch courses with instructors

Both `GET /courses/` and `GET /courses/{course_id}` include the instructor object:

```json
{
  "id": 1,
  "name": "FastAPI",
  "description": "Tutorial",
  "price": 10.0,
  "instructor_id": 1,
  "instructor": {"id": 1, "username": "alice", "email": "alice@example.com"}
}
```

The list endpoint returns an array of these objects with the existing pagination.
Instructors are eager-loaded in batches, avoiding a query per course. The nested
object excludes passwords and the instructor's own course list to avoid recursive
responses. Course creation/update responses and courses nested under users keep
their compact format. These course routes remain public, including the returned
instructor usernames and emails; protect them if that directory should be private.

The user routes above use `utilities.py`. These additional routes use
`authentication.py` directly:

| Method | Path | Input | Success |
| --- | --- | --- | --- |
| POST | `/auth/users` | JSON: `username`, `email`, `password` | 201: `id`, `username`, `email` |
| POST | `/auth/login` | JSON: `email`, `password` | 200: `access_token`, `token_type` |
| GET | `/auth/users/me` | `Authorization: Bearer <access_token>` | 200: `id`, `username`, `email` |

Register through `/auth/users` to try the bcrypt flow, then log in through
`/auth/login` and send its token to `/auth/users/me`. These routes also appear
under **Bcrypt authentication** in `/docs`. Both flows use the same registration
validation, unique usernames and emails, JSON login format, and token lifetime.
`/auth/users` stores bcrypt hashes, while `/users` stores Argon2 hashes.
Bcrypt accounts can log in through either flow; Argon2 accounts must use `/login`
because the direct bcrypt implementation cannot verify Argon2 hashes.
Both flows share the JWT signing key and token format, so tokens work with either
profile endpoint. `/auth/users/me` uses `authentication.get_current_user`;
`/users/me` additionally applies the active-user check described below.

Registration requires a valid email, a non-whitespace username of 1–50 characters,
and a password of at least 8 characters and at most 72 UTF-8 bytes. Duplicate
usernames or emails return 409; invalid registration data returns 422. Passwords
from `/users` are stored as salted Argon2 hashes and excluded from responses. Existing bcrypt
hashes still authenticate. Plaintext passwords will not authenticate; they must
be securely reset.

Login uses `Content-Type: application/json` with the user's email and password:

```json
{
  "email": "alice@example.com",
  "password": "a-secure-password"
}
```

Form submissions and missing or invalid JSON fields return 422. Incorrect
credentials return 401. Tokens expire after 30 minutes; missing, invalid, expired,
or deleted-user tokens return 401 with a `WWW-Authenticate: Bearer` header.

Open `http://127.0.0.1:8000/docs`, register a user with `POST /users`, then call
`POST /login` with JSON. Copy the returned `access_token` into **Authorize**
(without the `Bearer ` prefix) to try `/users/me`. Authorization uses an HTTP
Bearer security scheme, not the OAuth2 password flow, which requires form data.
Course endpoints remain public. Use HTTPS and add rate limiting
before exposing authentication publicly; refresh tokens and logout/revocation
are not implemented.

`/users/me` uses `utilities.get_current_active_user`. The SQL user model has no
`disabled` column, so current database users are treated as active; persistent
account disabling would require a model change and migration.

### Create a course

`POST /courses/` requires the ID of an existing user as `instructor_id`:

```json
{
  "name": "FastAPI",
  "description": "Tutorial",
  "price": 10.0,
  "instructor_id": 1
}
```

Replace `1` with the user's actual ID from registration or `GET /users/`.
Successful creation returns `200` with the course and its `instructor_id`.
Missing, null, or non-positive IDs return `422`; a nonexistent instructor returns
`404`. Database constraint conflicts return `409` and roll back the transaction.
On `PUT /courses/{course_id}`, omit `instructor_id` to keep the current instructor,
or provide another existing user ID to reassign it. Explicit null is rejected.
This tutorial's course routes do not enforce instructor ownership; add authorization
before exposing these write operations in production.

## Tests

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s 7/tests -v
```

Tests exercise the FastAPI application with an isolated in-memory SQLite
database. The existing PostgreSQL startup calls are bypassed only inside tests;
these tests do not verify live PostgreSQL connectivity or migrations.
