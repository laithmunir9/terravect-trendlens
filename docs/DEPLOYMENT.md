# Deployment — Streamlit Community Cloud

The owner authorized publishing the reviewed release candidate to public GitHub
and Streamlit Community Cloud on 15 November 2026. No NASA Space Apps submission
is authorized or automated. The prior local release review remains a historical record.

## Community Cloud settings

- Repository: `laithmunir9/terravect-trendlens`.
- Branch: `main`.
- Main file path: **`cloud/streamlit_app.py`**.
- Python: **3.12**, selected in Advanced settings.
- Secrets: **leave empty**. No Earthdata credentials are needed or permitted.

The dedicated entrypoint sets `TRENDLENS_PUBLIC=1` before running the existing app,
so startup does not depend on configuring a host environment variable. Community
Cloud checks the entrypoint directory for dependencies first; `cloud/requirements.txt`
includes `../requirements-public.txt`, excluding the optional local Earthdata client.
The root `requirements.txt` and `app.py` remain available for local authenticated use.
See the official [deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
and [dependency](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)
documentation.

In Community Cloud, choose **Create app**, select the repository and the settings
above, and deploy. Prefer subdomain `terravect-trendlens` if available. Public access
must be checked from a fresh unauthenticated browser after deployment. Authenticate
to GitHub/Streamlit and accept any required account terms in your own browser; never
commit cookies or tokens. Repository updates to this branch can redeploy the app.

Public mode starts with the labeled Giovanni browser snapshot and disables
authenticated Giovanni access both in the UI and before credential lookup. Live
POWER, the unchanged POWER comparison snapshots, and user-supplied CSVs remain available. No Earthdata account, token, OpenAI
key, or paid external API is needed. No silent fallback replaces failed live data.

## Validate locally

Use Python 3.12. The existing developer environment uses `requirements-dev.txt`.
For a clean public runtime:

```bash
python3.12 -m venv /tmp/trendlens-public-env
/tmp/trendlens-public-env/bin/python -m pip install -r requirements-public.txt
TRENDLENS_PUBLIC=1 /tmp/trendlens-public-env/bin/python -m streamlit run app.py \
  --server.address=127.0.0.1 --server.port=8513 --server.headless=true \
  --browser.gatherUsageStats=false
```

Do not run `scripts/earthdata_login.py` on a public host. Do not upload `.env`,
`.netrc`, `.urs_cookies`, `.streamlit/secrets.toml`, the local virtual environment,
browser profiles or logs. Do not configure Earthdata credentials in the host's
environment or mount the operator's home directory. Public mode blocks Giovanni
even if a token is accidentally present, but credentials still do not belong there.

## Container option

The Dockerfile copies only named app/data files and runs as a non-root user.
The Docker build context is an allowlist. These commands build and test locally,
not publish an image or create a public service:

```bash
docker build -t trendlens:release-candidate .
docker run --rm --name trendlens-preview -p 127.0.0.1:8513:8501 trendlens:release-candidate
```

Visit `http://127.0.0.1:8513`; check `/_stcore/health`. Confirm the Giovanni Abu Dhabi demo (24 complete years, 2002–2025), the POWER
comparison (25 shared years), and their downloads work with no NASA network access, that the source label says saved,
and that no authenticated Giovanni option appears. Select live POWER separately
to verify outbound HTTPS. Its outage must show an error rather than substitute data.

Docker build validation is **pending**: the local Docker daemon was unavailable
during this pass. A fresh Python 3.12 environment on macOS installed successfully
from `requirements-public.txt`, passed `pip check`, and ran both demos with network
calls forbidden and no `earthaccess` package installed. Its loopback browser smoke
check also passed. This is not a fully locked or tested Linux image. Before production,
build on the selected platform, retain the resolved dependency list and image digest,
and repeat the smoke checks. Installed dependency license/NOTICE files must remain
in the image. See the [Streamlit container guide](https://docs.streamlit.io/deploy/tutorials/docker).

## Other hosting options (not the selected deployment)

1. Resolve the submission blockers in `RELEASE_READINESS.md`; obtain approval for
   the specific host, public URL, and any hosting cost. Nothing in this document
   authorizes publication.
2. Use a container-capable host with HTTPS and WebSocket support. Run the image on
   container port 8501 with `TRENDLENS_PUBLIC=1`, no credentials, and no mounted home.
   For a Python host, install `requirements-public.txt`; run `python -m streamlit run
   app.py --server.address=0.0.0.0 --server.port="$PORT" --server.headless=true
   --browser.gatherUsageStats=false`, using the provider's port value.
3. Keep Streamlit's CORS/XSRF protections enabled. Disable detailed error tracebacks
   in the public app. Use a single instance for the demo unless session affinity is
   configured; uploads and Giovanni local results are browser-session memory.
4. Check `/_stcore/health` and test from a logged-out/incognito browser. A healthy
   endpoint alone does not prove that charts, downloads or source checks passed.
5. Retest both snapshots, comparison, exports, offline behavior, and a public POWER
   request. Check that no host/traceback/credential information is displayed.
6. Keep the prior image for rollback. Do not update source snapshots as part of a
   deploy; review any data refresh with its new hashes and retrieval timestamps.

The official submission permits a publicly accessible code/project link; a hosted
interactive app is not the only permitted final-project format. Either publication
route is distinct from submitting to NASA Space Apps. An app walkthrough is not the separate
required video/slide submission artifact.
