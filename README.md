# Company Registry Demo

A local company registry API built with FastAPI and PostgreSQL 17. The API lists
company summaries and returns the stored JSON document for an individual company.
Docker Compose runs the database; Python runs the API on your machine.

This walkthrough uses fictional sample data. The repository does not include a
real registry dataset or an import script.

## Prerequisites

- Git.
- Python 3.11 or newer, with `pip` and virtual environment support.
- Docker with a running Docker engine and Docker Compose v2 or newer.
- Available local ports `5432` (PostgreSQL) and `8000` (API).

Commands below use **Windows PowerShell**. The existing Compose file uses a
Windows-style bind-mount source, `.\init.sql`; adapt that source and the Python
virtual environment executable path if running on another platform.

## Run the demo

### 1. Get the code and install dependencies

```powershell
git clone https://github.com/juantoser/govt-registry.git
Set-Location govt-registry
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run subsequent commands from the repository root. Calling the virtual
environment's Python directly avoids needing to activate it or change PowerShell
execution policy.

### 2. Create the database initialization file

Create a file named `init.sql` in the repository root, next to `compose.yaml`,
containing the following SQL:

```sql
CREATE TABLE companies (
    registry_code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    data JSONB NOT NULL
);

INSERT INTO companies (registry_code, name, data)
VALUES
    (
        '10000001',
        'Example Company One',
        '{"ariregistri_kood": 10000001, "nimi": "Example Company One", "yldandmed": {}}'::jsonb
    ),
    (
        '10000002',
        'Example Company Two',
        '{"ariregistri_kood": 10000002, "nimi": "Example Company Two", "yldandmed": {}}'::jsonb
    );
```

These are synthetic records, not actual registry entries. The summary columns
(`registry_code`, `name`) support listing; `data` is the full detail response.
Each detail document must include integer `ariregistri_kood`, string `nimi`, and
object `yldandmed`. Additional fields are allowed.

`init.sql` is intentionally ignored by Git and is not included in the checkout.
You must create it **before starting Compose**, because Compose mounts it into
PostgreSQL as `/docker-entrypoint-initdb.d/001-schema.sql`.

### 3. Start PostgreSQL

```powershell
docker compose up -d --wait db
docker compose ps
```

Wait for `db` to be healthy before starting the API. On a new database volume,
PostgreSQL creates the `registry` database and runs `init.sql`.

The default connection URL used by the API matches `compose.yaml`:

```text
postgresql://demo:demo@127.0.0.1:5432/registry
```

These credentials are for a local demo only. PostgreSQL is published on loopback,
not on all host interfaces.

### 4. Start the API

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Leave this terminal running. Open <http://127.0.0.1:8000/docs> for interactive
Swagger UI, or use the examples below from a second PowerShell terminal.
The root URL `/` has no route; use `/docs` or `/companies`.

If needed, set `DATABASE_URL` in the API terminal **before** starting Uvicorn:

```powershell
$env:DATABASE_URL = "postgresql://demo:demo@127.0.0.1:5432/registry"
```

Otherwise no environment configuration is required. The application reads this
variable at startup; it does not automatically load `.env` files.

## Try the API

### List companies

```powershell
curl.exe "http://127.0.0.1:8000/companies"
```

Expected response with the sample data:

```json
[
  {"registry_code": "10000001", "name": "Example Company One"},
  {"registry_code": "10000002", "name": "Example Company Two"}
]
```

Results are ordered by `registry_code`. Pagination defaults to `limit=20` and
`offset=0`; `limit` must be between 1 and 100, and `offset` must be nonnegative.
Invalid pagination values return HTTP 422.

```powershell
curl.exe "http://127.0.0.1:8000/companies?limit=1&offset=1"
```

```json
[{"registry_code": "10000002", "name": "Example Company Two"}]
```

### Get a company

```powershell
curl.exe "http://127.0.0.1:8000/companies/10000001"
```

```json
{
  "ariregistri_kood": 10000001,
  "nimi": "Example Company One",
  "yldandmed": {}
}
```

An unknown registry code returns HTTP 404:

```powershell
curl.exe -i "http://127.0.0.1:8000/companies/99999999"
```

```json
{"detail": "Company not found"}
```

## Troubleshooting

| Problem | What to check |
| --- | --- |
| Docker cannot connect to its engine | Start Docker Desktop or your Docker engine, then retry. |
| Database startup fails around `001-schema.sql` | Ensure root `init.sql` exists as a file, not a directory, before starting Compose. Inspect `docker compose logs db` for the actual error. |
| Port `5432` is already allocated | Stop the conflicting service if appropriate, or change only the host port in `compose.yaml` and set `DATABASE_URL` to match. |
| Port `8000` is already allocated | Use another Uvicorn `--port` and adjust the example URLs. |
| API returns HTTP 500 or cannot connect to PostgreSQL | Check the Uvicorn error output, `docker compose ps`, `docker compose logs db`, and the API process's `DATABASE_URL`. API startup alone does not verify the database connection. |
| `companies` does not exist, or edited sample SQL has no effect | Initialization SQL runs only when the database volume is empty. Restarting Compose does not rerun it. For disposable demo data, use the reset below. |
| Authentication fails after changing Compose credentials | Existing volumes retain their original database users/passwords. Use matching credentials or deliberately reset disposable data. |

## Stop or reset

Stop the API with `Ctrl+C` in its terminal. Stop and remove the database container
and Compose network while keeping the database data:

```powershell
docker compose down
```

The named `postgres_data` volume persists across restarts. To start over with
`init.sql`, use the following **only if all data in this demo database can be
deleted**:

```powershell
docker compose down --volumes
docker compose up -d --wait db
```

**Warning:** `--volumes` permanently deletes this Compose project's database
volume and all records in it. Keep any data you need before resetting.
