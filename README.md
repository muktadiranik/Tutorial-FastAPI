# FastAPI tutorials

This repository contains lessons `1/` through `7/`, additional examples in
`Full Tutorial/` and `Tutorial/`, and the calculator project in
`Project/calculator/`. See `7/README.md` and `Project/calculator/README.md` for
their setup and test instructions.

## JWT signing keys

The authentication examples in `1/Blog/token.py`, `3/auth/oauth2.py`,
`Tutorial/blog/token.py`, and Lesson 7 require `JWT_SECRET_KEY` in the process
environment. Set a random key before starting an example (PowerShell):

```powershell
$env:JWT_SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
```

Keep the key private and stable between application restarts. Replacing it
invalidates existing tokens. These examples no longer contain hardcoded JWT
signing keys. The older examples read the process environment directly;
Lesson 7 additionally supports its local `.env` file.

Local `.env` files, database files, virtual environments, caches, and IDE files
are excluded from Git. Database connection settings in the tutorial code are
for local development; do not use them as production credentials.

## Practice repository

`practice-1/` is a Git submodule referencing
<https://github.com/muktadiranik/FastAPI-practice-1>. After cloning, initialize it
from the repository root:

```shell
git submodule update --init --recursive
```

The parent repository records a submodule commit, not uncommitted changes inside
that repository.
