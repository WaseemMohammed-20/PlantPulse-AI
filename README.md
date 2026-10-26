# PlantPulse AI

PlantPulse AI is a portfolio project for a manufacturing intelligence and
analytics platform. It is intended to help manufacturing teams understand
production performance, investigate machine downtime, spot quality issues, and
make better operational decisions.

> **Data notice:** All manufacturing data used by this project will be
> simulated. The application will identify simulated data clearly and will not
> present hardcoded sample metrics as calculated production results.

## Project goals

- Build a production-style application with a clear separation between its
  frontend, API, data, and analytics.
- Calculate operational metrics from their underlying data.
- Demonstrate practical skills in Python, SQL, Pandas, React, and data
  visualization.
- Keep configuration out of source code and make the project suitable for
  public hosting and eventual deployment.

## Planned technology stack

| Area | Technology |
| --- | --- |
| Frontend | React, TypeScript, Vite, Tailwind CSS, Recharts |
| UI | Tailwind CSS |
| API | Python, FastAPI |
| Database | PostgreSQL |
| Analytics | SQL, Python, Pandas |
| Business intelligence | Apache Superset |
| Containerization | Docker, Docker Compose |
| Version control | Git, GitHub |

## Planned features

- A plant overview with production and operational performance indicators.
- Production analysis with trends over time.
- Machine downtime analysis, including downtime duration and reason breakdowns.
- Quality analysis for defects and scrap.
- Validated API endpoints backed by PostgreSQL data.
- Analytics calculated from simulated source data rather than hardcoded API
  responses.
- An optional Apache Superset layer for business intelligence exploration.

The database foundation, deterministic data generator, read-only FastAPI
endpoints, and React analytics dashboard are implemented. Superset is managed
separately; create an administrator and register the PlantPulse connection on
a fresh metadata volume, then use the provisioning command below to create or
refresh the dashboards.

## Proposed project structure

```text
plantpulse-ai/
├── backend/
│   └── app/
│       ├── routers/          # Read-only API endpoints
│       ├── database.py       # PostgreSQL connection and query helper
│       ├── main.py           # FastAPI application and CORS
│       └── schemas.py        # Pydantic response models
├── data/
│   ├── raw/                 # Versioned simulated source fixtures, if useful
│   └── generated/           # Locally generated data (not committed)
├── docs/
├── frontend/
│   ├── src/
│   │   ├── api/             # Typed API client
│   │   ├── components/      # Dashboard shell, cards, and panels
│   │   ├── hooks/           # Dashboard data loading
│   │   └── pages/           # Overview and analytics views
│   ├── .env.example
│   └── package.json
├── infra/
│   └── superset/            # Local Superset Docker setup and configuration
├── tests/
│   └── test_api.py
├── .env.example
├── .gitignore
└── README.md
```

The frontend and local Superset integration are implemented. Superset
dashboards and charts are created or refreshed by the provisioning command
described below.

The current database foundation consists of:

```text
plantpulse-ai/
├── database/
│   ├── analytics.sql
│   └── schema.sql
├── infra/
│   └── superset/
│       ├── compose.yaml
│       ├── superset_config.py
│       └── .env.example
├── scripts/
│   └── generate_data.py
├── backend/
│   └── app/
│       ├── routers/
│       ├── database.py
│       ├── main.py
│       └── schemas.py
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── pages/
│   ├── .env.example
│   └── package.json
├── tests/
│   └── test_api.py
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

The relational schema connects factories to production lines, lines to
machines, and machine shifts to production records, downtime events, and
quality inspections. Database constraints enforce required relationships and
valid quantities. Shift timestamps are stored in UTC. All generated
manufacturing data is simulated.

## Database setup and simulated data

### Prerequisites

- Python 3.11 or newer.
- PostgreSQL 15 or newer, running locally or otherwise accessible.
- The PostgreSQL command-line client (`psql`) to apply and run the SQL files.

The Python generator and API use Psycopg 3 and `python-dotenv`. The API uses
FastAPI and Uvicorn. Docker Compose is used by the optional Superset
integration documented below.

### Install dependencies and configure PostgreSQL

From the project root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with the connection details for a PostgreSQL database you have
created. The generator and API both accept `DATABASE_URL`; when it is
non-empty, it takes precedence over `POSTGRES_HOST`, `POSTGRES_PORT`,
`POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`. Otherwise, configure
the `POSTGRES_*` values. Database connection attempts time out after five
seconds. Keep actual passwords in the ignored `.env`, never in source control.

If you need a dedicated local database, connect to PostgreSQL as an
administrator and create an application role and database:

```text
psql -U postgres
CREATE ROLE plantpulse_app LOGIN;
\password plantpulse_app
CREATE DATABASE plantpulse OWNER plantpulse_app;
\q
```

The `\password` command prompts for the role password without putting it in a
SQL script. Set the matching host, port, database, user, and password in the
ignored `.env` file.

The Python generator reads `.env` directly. For `psql`, set its standard
connection environment variables in PowerShell; `psql -W` prompts for the
password instead of putting it in a command:

```powershell
$env:PGHOST = Read-Host "PostgreSQL host"
$env:PGPORT = Read-Host "PostgreSQL port"
$env:PGUSER = Read-Host "PostgreSQL user"
$env:PGDATABASE = Read-Host "PostgreSQL database"
psql -W -v ON_ERROR_STOP=1 -f database\schema.sql
```

These connection values are for the current shell session. Do not put real
passwords or connection strings in tracked files.

### Generate and validate data

Generate 30 days ending today with the default reproducible seed (`42`):

```powershell
python scripts\generate_data.py
```

The generator creates three factories, six production lines, 18 machines, one
production record and quality inspection per machine per day, and simulated
downtime events. It validates inserted row counts and checks the production,
downtime, and quality foreign-key relationships before the transaction
commits. Existing table contents are preserved: if any of the six tables
already contains data, generation stops. Use `--reset` only when you intend to
replace data in all six tables.

Useful reproducibility and reset options:

```powershell
python scripts\generate_data.py --validate-only
python scripts\generate_data.py --days 45 --seed 123 --end-date 2026-10-24
python scripts\generate_data.py --reset
```

`--validate-only` generates the samples twice with the same seed, checks their
relationships and value constraints, reports expected row counts, and does not
connect to PostgreSQL. Re-running with the same seed, day count, and end date
produces the same sample data. `--reset` truncates all six tables and restarts
their identity sequences before generating data; it does not drop the schema.

Run the analytics queries against the populated database:

```powershell
psql -W -v ON_ERROR_STOP=1 -f database\analytics.sql
```

The OEE query documents its assumptions in `database/analytics.sql`: scheduled
breaks are excluded from planned production time, availability subtracts
unplanned downtime, performance uses rated capacity during run time, and
quality uses good versus total units. Target attainment and defect rate are
calculated from stored production and inspection records; no analytics results
are hardcoded.

## FastAPI backend

The read-only API connects to the existing PostgreSQL database using
`DATABASE_URL` or `POSTGRES_*` from the ignored `.env` file. It uses the
existing schema and computes responses from database records. Database
connection/query errors return HTTP 503 responses without exposing credentials
or driver details.

### Authentication and local demo mode

The API keeps `/api/health` public for health checks. All analytics routes
require a Clerk session token when `AUTH_REQUIRED=true`; `/docs`, `/redoc`, and
the OpenAPI schema are disabled. The backend validates the JWT signature
against the configured Clerk JWKS, requires the configured issuer and expiry,
checks the `azp` authorized-party against `CLERK_AUTHORIZED_PARTIES`, and
validates `aud` when `CLERK_AUDIENCE` is configured. It uses the officially
documented Clerk session-token/JWKS verification method; it does not require
the Clerk secret key.

The local demo remains usable without a Clerk account: Vite development mode
shows a demo-mode notice when `VITE_CLERK_PUBLISHABLE_KEY` is empty, and the
backend defaults to auth-disabled only when `APP_ENV=development`. Staging and
production environments default to requiring authentication; authentication
cannot be disabled outside development. This mode is for local development
only. A protected backend refuses to start without its Clerk verification
settings.

To enable local sign-in, create a Clerk application and configure its
development instance. In the Clerk dashboard, allow the local Vite origins,
then set the public publishable key in `frontend/.env`. In the root `.env`,
set:

```text
APP_ENV=development
AUTH_REQUIRED=true
CLERK_ISSUER=https://<your-clerk-instance>.clerk.accounts.dev
CLERK_JWKS_URL=https://<your-clerk-instance>.clerk.accounts.dev/.well-known/jwks.json
CLERK_AUTHORIZED_PARTIES=http://localhost:5173,http://127.0.0.1:5173
CLERK_AUDIENCE=
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

`VITE_CLERK_PUBLISHABLE_KEY` is intentionally public. Never put
`CLERK_SECRET_KEY`, database credentials, or other private keys in a
`VITE_*` variable. The API obtains a session JWT from Clerk and sends it as a
Bearer token on analytics requests. `/api/health` does not require a token.
The automated tests use locally generated signing keys; they do not contact
Clerk or create a user.

Start the API from the project root in PowerShell after installing
`requirements.txt` and configuring `.env`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Interactive OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.
The API reads the comma-separated `CORS_ORIGINS` setting from the root `.env`.
When it is blank or unset, both `http://localhost:5173` and
`http://127.0.0.1:5173` are allowed for local development. Set explicit
trusted HTTPS origins for a hosted frontend; do not use `*`.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | API and PostgreSQL connectivity status; returns 503 if the database is unavailable. |
| `GET /api/overview` | Total production and target, attainment, unplanned downtime, and inspected-sample defect rate. |
| `GET /api/production/trends` | Daily production, good-unit, and target totals. |
| `GET /api/production/lines` | Actual and target production, attainment, and unplanned downtime by line. |
| `GET /api/downtime/causes` | Event counts and downtime minutes by cause and planned/unplanned classification. |
| `GET /api/downtime/machines` | Machine ranking by accumulated unplanned downtime. |
| `GET /api/quality/lines` | Inspected units, defective units, and defect rate by line. |
| `GET /api/machines` | Machine/factory/line relationships and production, downtime, and quality metrics. |

Metric assumptions follow the SQL analytics: target attainment is total units
divided by target units; defect rate is defective inspected sample units
divided by inspected units; downtime totals and rankings use unplanned events
unless a response explicitly includes the planned/unplanned classification.
Percentage fields are `null` when their denominator is zero. Empty list
endpoints return an empty JSON array.

Run the API tests from the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

These tests cover response validation, database errors, empty results, and the
configured CORS origin. Endpoint SQL can also be verified against the running
database by starting Uvicorn and requesting each route.

## React analytics dashboard

The Vite application uses the existing API endpoints. It loads the API base
URL from `VITE_API_BASE_URL` and defaults to `http://127.0.0.1:8000/api` for
local development. The example frontend environment file can be copied and
edited if the API is hosted at another address:

```powershell
Copy-Item frontend\.env.example frontend\.env
```

Install dependencies and start the frontend from the project root:

```powershell
Set-Location frontend
npm install
npm run dev
```

The dashboard is served at `http://localhost:5173`. The backend must be
running separately; in another PowerShell window, from the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Build the production frontend bundle with:

```powershell
Set-Location frontend
npm run build
```

The Overview, Production, Downtime, Quality, and Machines navigation views use
the live API responses. Individual panels show loading, empty, or error states,
and the header connection indicator is driven by `/api/health`.

## Production deployment preparation

The public demo must use a newly created, dedicated managed PostgreSQL database
containing only the simulated data generated by this project. Do not copy the
existing local database or use the local Docker database in a public deployment.
The UI labels its dataset as simulated. The public API must keep
`AUTH_REQUIRED=true`; only `/api/health` is public, while analytics endpoints
require a valid Clerk session token.

### Initialize a new simulated demo database

Create a new Neon project/database. Do not import or restore the existing local
database. Apply `database/schema.sql` to the new empty database using the Neon
SQL Editor. The script creates the existing tables and indexes with
`IF NOT EXISTS`; it does not seed or reset rows.

Check the fixed simulated dataset without connecting to a database:

```powershell
.\.venv\Scripts\python.exe scripts\generate_data.py --days 30 --seed 42 --end-date 2026-10-26 --validate-only
```

Then seed the new, empty Neon database. Use its TLS-enabled connection string
(`sslmode=require`), enter it at the hidden prompt, and never use `--reset`:

```powershell
$secureUrl = Read-Host "New Neon DATABASE_URL" -AsSecureString
$env:DATABASE_URL = [System.Net.NetworkCredential]::new("", $secureUrl).Password
try {
    .\.venv\Scripts\python.exe scripts\generate_data.py --days 30 --seed 42 --end-date 2026-10-26
}
finally {
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
}
```

The generator refuses to insert if any of its six tables already contains
rows. This makes the documented bootstrap safe to rerun on a blank database
without replacing existing data; do not bypass that guard or use `--reset` for
a hosted database. Keep the Neon connection string only in the API host's
secret settings. Use a dedicated database role with only the permissions
required by the API.

### Deploy the FastAPI service

The backend can be built as a non-root container from the repository root:

```powershell
docker build -f backend\Dockerfile -t plantpulse-api .
```

For Render, create a **Docker web service** from the repository after the
backend source files have been published to GitHub. Use the repository root as
the build context and `backend/Dockerfile` as its Dockerfile. The container
already starts Uvicorn on Render's `PORT`, runs as a non-root user, and includes
a health check at `/api/health`. Configure Render's health check path as
`/api/health`. The health endpoint is public and returns HTTP 200 only when the
database is reachable. Set these backend environment variables in the Render
service settings:

| Variable | Value |
| --- | --- |
| `APP_ENV` | `production` |
| `AUTH_REQUIRED` | `true` |
| `DATABASE_URL` | Neon TLS connection string; keep private |
| `CLERK_ISSUER` | Exact issuer URL from the Clerk production instance |
| `CLERK_JWKS_URL` | Exact JWKS URL for that issuer |
| `CLERK_AUTHORIZED_PARTIES` | `https://frontend-gamma-three-16.vercel.app` (and any other exact trusted browser origins) |
| `CORS_ORIGINS` | Same exact HTTPS origin(s), comma-separated; no trailing slash |
| `CLERK_AUDIENCE` | Set only if the configured Clerk session token includes an audience |

The app fails to start if production authentication or CORS configuration is
missing. Never set `AUTH_REQUIRED=false` in a public environment. There is no
need to put a Clerk secret key in the frontend; backend verification uses the
public JWKS endpoint. Keep the database URL and all other private credentials
in server-side host settings only.

### Configure the existing Vercel frontend

The public frontend is already deployed at
<https://frontend-gamma-three-16.vercel.app/>. It currently runs as a
simulated-data demo: no Vercel environment variables are configured, and no
production API or Neon database is connected. The frontend project uses
`frontend` as its root directory, `npm run build` as its build command, and
`dist` as its output directory.

After the Render API is ready, add these **Production** environment variables
to the existing Vercel project and redeploy:

- `VITE_API_BASE_URL`: the Render HTTPS service URL ending in `/api`, for
  example `https://<your-render-service>.onrender.com/api`
- `VITE_CLERK_PUBLISHABLE_KEY`: the production Clerk `pk_live_...` key

When configured, `VITE_API_BASE_URL` must be an external HTTPS URL ending in
`/api`; localhost URLs and URLs containing credentials or query parameters are
rejected. If it is omitted, production tries same-origin `/api` and switches to
clearly labeled simulated demo data when the API is unavailable or rejects the
request. Production never falls back to localhost. Never use
`CLERK_SECRET_KEY` as a `VITE_*` variable. Configure the final Vercel HTTPS
origin in Clerk and in both backend origin variables above.

If `VITE_CLERK_PUBLISHABLE_KEY` is not configured, the dashboard opens in
simulated demo mode. When Clerk is configured but the visitor is signed out,
the sign-in page also offers a separate simulated demo entry. Demo data is
static and does not relax API authentication; only a valid Clerk session can
retrieve live API data.

### Initialize an empty Neon database safely

The generator connects through `DATABASE_URL` when set and refuses to insert
anything if any of the six target tables already contains rows. It does not
apply the schema automatically. First confirm in the Neon SQL Editor that the
database is the intended new database and that all six tables are empty; run
`database/schema.sql` there if the tables have not yet been created. Do not run
the generator with `--reset`.

To run the deterministic default 30-day seed from PowerShell without echoing
the connection string, enter it at the hidden prompt. Include `sslmode=require`
in the Neon URL. This only runs the generator after its table-empty checks:

```powershell
$secure = Read-Host "Neon PostgreSQL URL (include sslmode=require)" -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $env:DATABASE_URL = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    .\.venv\Scripts\python.exe scripts\generate_data.py --validate-only
    if ($LASTEXITCODE -ne 0) { throw "Generator validation failed." }
    .\.venv\Scripts\python.exe scripts\generate_data.py
    if ($LASTEXITCODE -ne 0) { throw "Data generation failed." }
}
finally {
    $env:DATABASE_URL = $null
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    $secure.Dispose()
}
```

If using a project without the local `.venv`, substitute its Python executable.
The generator's normal run inserts data but never creates tables or uses
`--reset`.

### Clerk and deployment readiness

The local Clerk development key is not a production Clerk configuration, and
a real Clerk-issued session has not been verified end-to-end. Configure a
Clerk production instance and allow the Vercel origin, then add the production
publishable key to Vercel and the exact issuer/JWKS values to Render. Verify a
real sign-in, successful authenticated API request, and sign-out before
considering live API access ready.

At the time of writing, only the Vercel frontend exists; Render and Neon are
not connected. The local PostgreSQL database is separate and must not be used
as the public service's database. Apache Superset remains local-only.

## Apache Superset business intelligence

The local Superset stack is separate from the application and the existing
PostgreSQL container. It builds a small local image from the official
`apache/superset:6.1.0` image and adds the pinned PostgreSQL driver required for
database connections. It stores Superset metadata in the independent Docker volume
`plantpulse-superset-home`, and reads its required secret key from the ignored
`infra/superset/.env` file. The web interface is published only on
`127.0.0.1:8088`.

All manufacturing source data is simulated. The Superset metadata volume now
contains four PlantPulse SQL datasets, 17 charts, and five dashboards. Run the
idempotent provisioning and chart-validation command below after starting
Superset to create or refresh them.

### Prepare and start Superset

Run from the repository root in PowerShell. Copy the example only if the local
file does not already exist. A random secret is generated only if the example
placeholder is still present; keep the resulting secret across restarts:

```powershell
if (-not (Test-Path infra\superset\.env)) {
    Copy-Item infra\superset\.env.example infra\superset\.env
}
if (Select-String -Quiet -Path infra\superset\.env -Pattern '^SUPERSET_SECRET_KEY=replace-this-with-a-random-secret$') {
    $secret = python -c "import secrets; print(secrets.token_urlsafe(48))"
    $settings = Get-Content infra\superset\.env
    $settings = $settings -replace '^SUPERSET_SECRET_KEY=.*$', "SUPERSET_SECRET_KEY=$secret"
    Set-Content -Path infra\superset\.env -Value $settings
}
```

This generates a secret only when the example placeholder is present, and
retains any existing secret. Do not commit this file or share the key.
The database migration and Superset role initialization run when the service
starts:

```powershell
docker compose -f infra\superset\compose.yaml up -d --wait
docker compose -f infra\superset\compose.yaml logs --tail 100 superset
```

The existing `plantpulse-postgres` container must be running. The Compose
configuration uses `host.docker.internal:5432` to reach its already-published
host port; it does not use `localhost` from inside the Superset container and
does not attach to, recreate, or change the existing PostgreSQL container or
`plantpulse_pgdata` volume.

The existing local Superset metadata currently has no administrator account.
Create one interactively before signing in; Superset prompts for the account
details and password, so no credential is stored in this repository:

```powershell
docker compose -f infra\superset\compose.yaml exec superset superset fab create-admin
```

Open `http://127.0.0.1:8088` and sign in with that account. Do not put the
password in a command, script, or tracked file.

### Register PlantPulse and provision dashboards

The existing local Superset metadata already has the `PlantPulse` PostgreSQL
connection registered and tested. On a fresh Superset metadata volume, add it
once using the UI steps below. No source database tables, rows, containers, or
volumes are created or modified by dashboard provisioning.

Run the provisioning command from the repository root after the PostgreSQL
connection is registered:

```powershell
docker compose -f infra\superset\compose.yaml exec superset python /app/provision_dashboards.py
```

The script upserts the four SQL datasets and all named charts and dashboards,
then executes every saved chart query through Superset against PostgreSQL.
During that validation it generates a random, temporary administrator
credential in memory, removes the temporary account immediately afterward,
and does not print or persist its password. Re-running the command refreshes
these PlantPulse assets rather than creating duplicate copies.

The provisioned dashboards and contents are:

| Dashboard | Charts |
| --- | --- |
| Manufacturing Overview | Daily production output vs target; target attainment by line; OEE by production line; unplanned downtime by cause; defect rate by line. |
| Production Analytics | Daily output and target trend; actual units by line; daily target attainment. |
| Downtime Intelligence | Unplanned downtime by cause; unplanned downtime by machine; detailed cause/machine event table. |
| Quality Analytics | Defect rate by line; inspected vs defective sample units; daily defect-rate trend. |
| Machine Performance | OEE by machine; actual vs target output by machine; unplanned-downtime ranking. |

Each dashboard includes a default 90-day date-range filter. Open
**Dashboards** in Superset, or use the dashboard page URLs listed there after
sign-in.

For a fresh metadata volume, open **Settings → Database Connections → +
Database**, select PostgreSQL, and use:

| Field | Value |
| --- | --- |
| Host | `host.docker.internal` |
| Port | `5432` |
| Database name | `plantpulse` |
| Username | `POSTGRES_USER` from the ignored root `.env` |
| Password | `POSTGRES_PASSWORD` from the ignored root `.env` |

Test the connection and save it as `PlantPulse` before running provisioning.
Do not use `localhost` as the host: inside the Superset container, that refers
to Superset itself.

To stop Superset without deleting its metadata:

```powershell
docker compose -f infra\superset\compose.yaml down
```

Do not add `--volumes` / `-v` when stopping the service; that would delete
Superset's metadata volume. PostgreSQL is a separately managed service and is
not stopped by these Compose commands.

The existing port mapping publishes PostgreSQL on the host's interfaces. That
mapping was already present and is intentionally left unchanged; restrict it
separately if the machine is reachable from untrusted networks. For a
non-local deployment, use a dedicated least-privilege read-only database role,
TLS, and an appropriate secrets manager rather than reusing an administrator
credential.

The four virtual datasets are built from the existing tables:
`pp_production_daily`, `pp_downtime`, `pp_quality`, and
`pp_machine_performance`. The downtime dataset sums recorded event durations;
overlapping event intervals are not deduplicated. The quality dataset's defect
rate denominator is inspected sample units. OEE assumptions are: each
production record represents one machine shift; scheduled breaks are excluded from
`planned_production_minutes`; availability subtracts **unplanned** downtime
only and clamps run time at zero; performance compares actual units with the
machine's rated hourly capacity over run time; quality is `good_units /
total_units`; and OEE is the product of availability, performance, and quality
computed from aggregated numerators and denominators. The separate defect-rate
chart uses inspected sample units and is not a substitute for the production
record's OEE quality factor. All values originate from simulated manufacturing
records, not live plant operations.

## Verify the database foundation

With dependencies installed and PostgreSQL running, configure the connection
as above and run these commands from the project root in PowerShell:

```powershell
python -m py_compile scripts\generate_data.py
python scripts\generate_data.py --validate-only --days 30 --seed 42 --end-date 2026-10-24
psql -W -v ON_ERROR_STOP=1 -f database\schema.sql
python scripts\generate_data.py --days 30 --seed 42 --end-date 2026-10-24
psql -W -v ON_ERROR_STOP=1 -f database\analytics.sql
git check-ignore -v .env
```

The schema and analytics commands stop on SQL errors. The generator's database
run checks row counts and foreign-key relationships before committing. Run the
data-generation command once for an empty database; use `--reset` only when
replacing all existing PlantPulse table data is intentional.

The FastAPI backend, React frontend, and local Superset Docker integration are
implemented. For a fresh Superset metadata volume, create an administrator and
register the PlantPulse database connection before running the idempotent
provisioning command. Existing metadata and dashboards are preserved by the
documented provisioning workflow.
