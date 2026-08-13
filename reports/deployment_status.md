# Part 2 deployment status (honest report)

**Bottom line: the demo runs correctly locally (backend + frontend
both verified working end-to-end); it is not deployed to any public
URL.** Here's exactly what was tried and why it didn't reach a public
URL, so this isn't a vague "it didn't work."

## What works right now (verified, not assumed)

- `uvicorn api.app:app --host 0.0.0.0 --port 8000` -- FastAPI backend,
  all 4 endpoints (`/api/health`, `/api/presets`,
  `/api/upload-mic-geometry`, `POST /api/run/preset`,
  `POST /api/run/upload`) tested directly via `curl` and via 8 automated
  tests (`test/unit/test_api.py`, using FastAPI's `TestClient`).
- `streamlit run demo/app.py` -- frontend, verified via Playwright
  screenshots in both preset mode and upload mode: correct 3D
  visualization (mic clusters, DOA rays, pairwise intersection cloud,
  estimated vs. true position), correct results panel (angle/position
  error, measured RT60), no layout bugs.

Anyone can run this today with the instructions in `demo/README.md`.

## What the user asked for vs. what's actually available in this environment

The request was: "FastAPI backend on Cloud Run (Dockerfile included),
frontend on Vercel if Next.js, or bundle everything into one Streamlit
app on Cloud Run if you go that route instead."

This session's connected tools are: GitHub, Vercel, a finance data
tool, and a sports-odds tool. **There is no Google Cloud / Cloud Run
connector available.** That is the literal, primary blocker for the
requested deployment target -- not a code problem, a missing platform
connection. It's stated here plainly rather than worked around with a
fake success.

## What was actually attempted with what is available

**1. Docker image (`Dockerfile` + `docker-entrypoint.sh`, committed).**
Written to Cloud Run's exact convention (single container, binds to
`$PORT`, both processes -- uvicorn backend + streamlit frontend --
started by `docker-entrypoint.sh`, `wait -n` so the container exits if
either process dies). **This image has not been build-tested.** There
is no `docker` binary in this development sandbox (confirmed:
`which docker` returns nothing), so `docker build` was never actually
run. The two processes it starts were each verified working directly
(not inside a container) as described above, but the container
packaging itself -- the `Dockerfile` build succeeding, the
`docker-entrypoint.sh` script's process orchestration working as
written -- is unverified. This is disclosed in `demo/README.md` too.
If you have Docker locally: `docker build -t doa-demo . && docker run
-p 8080:8080 -e PORT=8080 doa-demo`, then check http://localhost:8080.

**2. Vercel deployment of the FastAPI backend.** Streamlit cannot run
on Vercel at all -- it's a serverless platform (functions spin up per
request and don't hold a persistent process), and Streamlit requires a
long-lived server with a WebSocket connection back to the browser.
That part of the architecture mismatch is unavoidable regardless of
account permissions.

The FastAPI backend alone, in principle, *can* run as a Vercel Python
serverless function (its actual runtime dependencies -- numpy,
soundfile, fastapi, pydantic, pyroomacoustics -- have no dependency on
a persistent connection). A `vercel.json` routing the whole backend
through `api/app.py` was written and a real deployment was attempted
using the connected Vercel account (`npx vercel deploy --token
$VERCEL_TOKEN`).

**Result: it failed, but not because of the code or the `vercel.json`
config.** Every attempt (with `--prod`, with `--target preview`, from
a project directory with and without a linked local `.git`, under
multiple different project names) failed at the same point, with the
same message:

```
Error: You don't have permission to create a Production Deployment for this project.
```

This happened even for a brand-new, never-before-seen project name, and
even when explicitly requesting a preview (non-production) target --
Vercel appears to treat every *first* deployment of a new project as
implicitly requiring production-deploy permission, which this
account/token combination doesn't have for new projects specifically.
This is very likely an account or team-role permission setting (the
connected Vercel account authenticates fine, and can see and has
existing production deployments for other projects on the same team --
`check-your-politician`, `la-money-votes` -- so it is not a broken
connection or expired token, and not a Vercel-wide outage). Resolving
it would require either a role/permission change on the Vercel team
account, or deploying through the Vercel web dashboard directly
(outside of what this session's tools can do) rather than the CLI
token used here. All test projects created during this attempt
(`doa-demo-api`, `doa-demo-api-preview`, `doa-demo-api2`) were deleted
afterward to avoid leaving clutter in the account.

Beyond the permission error, there's also a real unresolved technical
risk that was never reached: `pyroomacoustics` ships C extensions and
is a moderately large dependency; Vercel's Python serverless functions
have a size limit (historically ~250 MB unzipped) that a
numpy+scipy+pyroomacoustics function could plausibly approach or
exceed. This was not tested because the permission error blocked any
deployment attempt from getting far enough to hit it.

**3. `deploy_website`/`publish_website` (this session's own
website-publishing tooling).** Checked and ruled out: that pipeline is
built around a Node/Vite static-build + optional Node backend model
(`run_command="node dist/index.cjs"` style), not a natural fit for a
Python/pyroomacoustics backend or a Streamlit frontend. Not used.

## Recommended path if you want an actual public URL

The most direct fix is almost certainly on the Vercel side, not the
code: check the team/account's deploy permissions for new projects
(Vercel dashboard -> team settings -> roles/permissions), or create
the project once via the Vercel web dashboard (which may not hit the
same restriction the CLI did) and then use the CLI only for subsequent
deployments to that already-created project. Once a project exists and
one dashboard-created deployment succeeds, deploying the FastAPI
backend there directly is a reasonable next step -- watch for the
pyroomacoustics package-size risk above. Cloud Run itself would need
that connector added to this environment; short of that, the Docker
image can be built and pushed manually to any container host (Cloud
Run, Fly.io, Render, a VM) once its build is verified locally.
