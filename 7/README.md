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

## Endpoints

| Method | Path | Input | Success |
| --- | --- | --- | --- |
| POST | `/users` | JSON: `username`, `email`, `password` | 201: `id`, `username`, `email` |
| POST | `/login` | JSON: `email`, `password` | 200: `access_token`, `token_type` |
| GET | `/users/me` | `Authorization: Bearer <access_token>` | 200: `id`, `username`, `email` |

The routes above use `utilities.py`. These additional routes use
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
Course endpoints remain public and unchanged. Use HTTPS and add rate limiting
before exposing authentication publicly; refresh tokens and logout/revocation
are not implemented.

`/users/me` uses `utilities.get_current_active_user`. The SQL user model has no
`disabled` column, so current database users are treated as active; persistent
account disabling would require a model change and migration.

## Tests

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s 7/tests -v
```

Tests exercise the FastAPI application with an isolated in-memory SQLite
database. The existing PostgreSQL startup calls are bypassed only inside tests;
these tests do not verify live PostgreSQL connectivity or migrations.
