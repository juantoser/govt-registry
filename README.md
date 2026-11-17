# Hybrid procurement buyer demo

Three agents in a local **Microsoft Agent Framework Workflow**:

```text
Viitenumber
  -> Router (Foundry Local)
  -> ProcurementLookup (actually hosted in Foundry)
       -> public riigihanked.riik.ee API
  -> RegistryAgent (Foundry Local)
       -> local FastAPI -> Docker PostgreSQL
  -> same Router (Foundry Local) -> buyer summary
```

Only the procurement reference goes to the cloud. Company details remain local.
The local orchestrator passes the cloud result to the local agent; no tunnel,
public database endpoint, or MCP server is needed.

## Run locally

Requires Python 3.13 or 3.14, the Azure CLI signed in with access to the
`main-govt` Foundry project, Foundry Local, and the existing populated registry
PostgreSQL container. This demo reuses the database; it does not import data or
create a replacement database.

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env

foundry server start
foundry model download 'qwen2.5-1.5b-instruct-generic-gpu:4'
```

The GPU variant is intentional: the cached Qwen NPU variant advertises tool
calling but fails with missing tool markers. The GPU variant was verified with
actual function calls. The workflow discovers its current endpoint/model ID via
the Foundry CLI, loads the cached model, and does not download models implicitly.
This avoids a native Python SDK DLL loading issue on Windows ARM64.

Start the existing database if stopped, then run the registry API in a terminal:

```powershell
docker start company-registry-demo-db-1
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

The container must already contain the registry data. `compose.yaml` belongs to
the original database setup and references an ignored `init.sql`; that schema
and data import are not included here. Do not delete the populated Docker volume.

In another terminal:

```powershell
.\.venv\Scripts\python.exe workflow.py 317735
```

The CLI prints all four stages, including the actual local company tool call.
The example resolves to:

```text
Viitenumber 317735: the main buyer is Aktsiaselts Ida-Tallinna Keskhaigla (registry code 10822068).
Status: Registrisse kantud
Legal form: Aktsiaselts
Registered: 13.12.2001
```

The demo API also exposes `GET /companies?limit=20&offset=0` and
`GET /companies/{registry_code}`. Its default database connection is the existing
demo database on `127.0.0.1:5432`; set `DATABASE_URL` in the API process if needed.

## Configuration

`.env.example` contains the already-deployed `procurement-lookup` Responses
endpoint in `main-govt`, the local model variant, and the registry API URL.
Copy it to `.env`; there are no API keys. Cloud calls use `AzureCliCredential`.
If Azure authentication has expired, sign in with `az login` yourself.

The registry API and Foundry Local must use loopback addresses. The hosted agent
only accesses the public procurement portal, not the local API/database.

## Hosted procurement agent

The agent is deployed to the existing `main-govt` project and uses its
`gpt-6.1-sol` model deployment. Hosting and cloud inference can incur Azure charges.
No additional model or Foundry project is required.

Deployment configuration is in `hosted\azure.yaml`; source and its separate cloud
dependencies are in `hosted\src\procurement-lookup`. With azd and its
`azure.ai.agents` extension installed:

```powershell
Set-Location .\hosted
$env:AZURE_DEV_USER_AGENT = 'microsoft_foundry_skill'
```

For a fresh checkout, initialize the local azd environment from the checked-in
manifest first (skip this in the already-initialized demo workspace):

```powershell
azd ai agent init --no-prompt -t .\azure.yaml `
  --project-id '/subscriptions/c4b40a12-d97e-4287-9c93-7d6bda9690cf/resourceGroups/main-govt/providers/Microsoft.CognitiveServices/accounts/main-govt-resource/projects/main-govt' `
  --model-deployment gpt-6.1-sol
```

Then deploy from the same `hosted` folder:

```powershell
azd deploy procurement-lookup --no-prompt
azd ai agent show procurement-lookup --output json
```

Use the returned `agent_endpoints.responses` URL as `FOUNDRY_AGENT_ENDPOINT`.
Deployment creates a new immutable agent version; it does not require
`azd provision` for this existing project.

The lookup function uses the portal's public endpoints in order:

1. `/procurement/{reference}/identifier`
2. `/procurement/{procurement_id}/latest-version`
3. `/proc-vers/{version_id}/procurers`

It extracts the eight-digit registry code from `mainProcurer`. The portal's
`mainProcurerId` is an internal ID, **not** the company registry code.

Workflow handoffs use validated, executed tool results rather than model-written
identifiers. The router uses a local summary tool to render the verified company
fields without a small model changing names or facts. Invalid input, upstream
failure, missing company, or a model failing to call its tool stops the workflow
with an error instead of returning invented data.

This is a CLI PoC: no automated tests, evaluation suites, UI, or production
infrastructure. It uses the Agent Framework
[workflow APIs](https://learn.microsoft.com/en-us/agent-framework/workflows/).
