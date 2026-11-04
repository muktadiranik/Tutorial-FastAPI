# calcula

A responsive calculator with a **Python / FastAPI** backend and a **TypeScript / Vite** frontend.

## Features

- Addition, subtraction, multiplication, division, parentheses, percentages, and integer powers.
- Decimal arithmetic with 28 significant digits; `0.1 + 0.2` gives `0.3`.
- Keyboard input, sign toggle, backspace, and clear.
- The last 30 calculations saved in your browser. Click a result to reuse it.
- Clear messages for incomplete expressions, division by zero, and connection errors.
- Responsive layout, labeled controls, visible keyboard focus, and live status messages.

## Requirements

- Python 3.10 or newer.
- Node.js 20.19+ or 22.12+ (Vite 8 requirements).

## Run locally

From `Project/calculator`, create an environment and install the Python dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn backend.main:app --reload
```

In another terminal, from `Project/calculator/frontend`:

```powershell
npm install
npm run dev
```

Open **http://127.0.0.1:5173** (or the URL Vite prints). The frontend proxies `/api` to the Python server on port 8000. API documentation is at **http://127.0.0.1:8000/docs**.

On macOS/Linux, use `.venv/bin/python` in place of `.\.venv\Scripts\python`.

## Serve the built app from Python

From `frontend`, run:

```powershell
npm run build
```

Then start or restart the Python server from `Project/calculator`:

```powershell
.\.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. FastAPI serves both the built interface and the API. The build must exist before the server starts. `npm run preview` only previews frontend assets; use Vite development mode or FastAPI for working calculations.

## Keyboard and expressions

- Type an expression, then press **Enter** or **=** to calculate.
- **Escape** clears; **Backspace** deletes.
- `*` / `×`, `/` / `÷`, `-` / `−`, and `^` / `**` are supported.
- `%` is postfix percentage: `10% = 0.1`, `200 × 10% = 20`, and `100 + 10% = 100.1`.
- Powers use whole-number exponents from -100 to 100. `-2^2 = -4`; `(-2)^2 = 4`.
- Use explicit multiplication: `2 × (3 + 4)`.
- Results and intermediate values must be zero or have a magnitude between `1e-100` and `1e100`. Expressions are limited to 256 characters.
- Calculations are evaluated by a restricted decimal parser, never Python `eval`.

History stays in this browser's local storage and can be cleared with **Clear**. Fonts load from Google Fonts, with system fallbacks when offline.

## API

`POST /api/calculate`

```json
{ "expression": "(12 + 3) × 2" }
```

Response:

```json
{ "expression": "(12 + 3) × 2", "result": "30" }
```

Results are strings to preserve decimal precision. Calculation errors return HTTP 400 with a `detail` message; malformed request bodies return HTTP 422. `GET /api/health` returns `{ "status": "ok" }`.

## Verification

From `Project/calculator`:

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
```

From `frontend`:

```powershell
npm run build
```
