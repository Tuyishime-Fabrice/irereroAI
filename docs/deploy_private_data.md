# Real data on the deployed app, kept private

The public repository holds no NISR, MINEDUC or other received data, and never will. To show
real figures on the deployed app (Streamlit Community Cloud), the team keeps a **private data
bundle** somewhere only the app can read, and gives the app three secrets. Without them the
app runs on the labelled demo data, as it always has.

## What is in the bundle, and what is not

| In the bundle (`make bundle`) | Never in the bundle |
| --- | --- |
| What `make intake` staged in `data/raw/<dataset>/`: census sector counts (weighted), district projections, NISR 2022 boundaries, EICV7 district rates, the MINEDUC district table, the school list, the NCDA extract in the `supply_extract` columns, and any dataset staged later | `data/raw/_received/`: every original, including the census 2022 sample records (person-level) and the full NCDA export |
| `MANIFEST.json`: the SHA-256 of every file | Tokens, passwords or any secret |

The census sample records stay on the machine that received them. The bundle holds aggregates,
plus the NCDA services (centre id, name, type, sector, point, enrolment aged 3 to 6, caregivers),
which the app shows only when `IRERERO_NCDA_DISPLAY` is on.

## Set it up (about 10 minutes, once)

1. **Make the bundle** on the machine that holds the staged files:

   ```bash
   make bundle
   ```

   It writes `data/bundle/irerero-data.zip` (gitignored, and refused by the pre-commit guard)
   and prints `IRERERO_DATA_SHA256 = ...`. Keep that line.

2. **Create a private repository** on GitHub, for example `irereroai-data`
   (github.com → New repository → **Private**). Upload `irerero-data.zip` to it (Add file →
   Upload files). Add only people who may see the data.

3. **Create a read-only token for that repository only**: GitHub → Settings → Developer
   settings → Personal access tokens → **Fine-grained tokens** → Generate new token.
   - Repository access: **Only select repositories** → `irereroai-data`
   - Permissions: **Contents: Read-only** (nothing else)
   - Expiry: the end of the hackathon, or shorter

4. **Add three secrets** to the app: share.streamlit.io → the app → **Settings → Secrets**:

   ```toml
   IRERERO_DATA_URL = "https://api.github.com/repos/<owner>/irereroai-data/contents/irerero-data.zip"
   IRERERO_DATA_TOKEN = "github_pat_..."
   IRERERO_DATA_SHA256 = "<the line printed by make bundle>"
   ```

5. **Reboot the app** (Manage app → Reboot). On first start it downloads the bundle, checks
   it, and builds the tables from it. The screens then show *model estimate* where the data
   are real and SIMULATED only where a stand-in remains.

## The school list (provisional)

The MINEDUC school locations can sit in the same private repository as a separate file; the app
fetches it with the **same token**, server side, and never sends the token to the browser.
Add one secret beside the three above (same place: the app → **Settings → Secrets**):

```toml
IRERERO_SCHOOLS_PATH = "schools/Rwandapreprimarydata_locatios.GeoJSON"
# optional: pin the file, as for the bundle (sha256sum of the file)
# IRERERO_SCHOOLS_SHA256 = "..."
```

The path is inside the repository named in `IRERERO_DATA_URL`. For a file somewhere else, set
the full address instead: `IRERERO_SCHOOLS_URL = "https://api.github.com/repos/<owner>/<repo>/contents/<path>"`
(it must be `https`; the token is sent only there). The token needs **Contents: Read-only** on
that repository, as for the bundle.

Reboot the app. On first start it downloads the file, checks that it is a GeoJSON
FeatureCollection (and its SHA-256 when given), keeps a copy in `data/raw/schools/`, and
rebuilds the distance layer from it. Each record is checked: points outside Rwanda, swapped
coordinates or missing geometry are counted and left out, never guessed.

**How to check it worked**

- Overview → map → **Distance to school**: orange points (139 with the current file) over the
  sector shares, and a PROVISIONAL note under the map.
- The fourth KPI reads **≤ …% Children > 1 km from a listed school**, badge PROVISIONAL.
- Data & methods → **School locations**: "139 of 139 records loaded …" with the counts of
  invalid coordinates, missing points, repeated points and missing properties.
- If the download or a check fails, every page shows "The school list was not loaded: …
  Distances keep their stand-in." (never the token or the address), and the app carries on.

Locally the same works with the variables in `.env`, or by staging the file:
`make intake FILES="Rwandapreprimarydata_locatios.GeoJSON"` then `make data`.

**Why provisional.** The file lists only the 139 standalone pre-primary schools; most
pre-primary classes are inside primary schools, which it does not list. So the share of
children more than 1 km from a *listed* school is an upper bound, shown with that label, and it
is not used as evidence in the bottleneck rules. A sector far from a listed school may still
have a school nearby. When the full MINEDUC register arrives, replace the file (same path) and
update `IRERERO_SCHOOLS_SHA256` if you set it; the app rebuilds on the next start.

## What the app checks before using the bundle

- The address is `https` (no plain-text download), and the token is sent only to it.
- The zip's SHA-256 equals `IRERERO_DATA_SHA256`, so a changed or swapped file is refused.
- Every file matches `MANIFEST.json`, and every path is a known dataset folder (no `..`, no
  absolute paths, no `_received`).
- If any check fails, nothing is written: the app shows a notice saying why (never the token
  or the address) and keeps the demo data.

## Updating the data

When new files arrive: `make intake FILES="..."`, `make data`, check the screens, then
`make bundle`. Upload the new zip, put its address and SHA-256 in the secrets, and reboot the
app. The app notices the new bundle and rebuilds.

**Order matters when the code changes too.** Merge the code first, let the app redeploy (it
keeps working on the old bundle), and only then point the secrets at the new bundle. A bundle
built for newer code can fail on older code; the app then keeps the demo data and says why.

### The 30 October 2026 update

The new bundle is `bundles/irerero-data-2026-10-30.zip` in the data repository, beside the
previous `irerero-data.zip` (left in place as the rollback).

1. Merge the branch `claude/gallant-lamport-od0yq7` into `main` in **both** repositories: the
   app (adds the NISR 2022 boundaries and the NCDA extract) and the data repository (adds the
   new bundle and files the originals under `sources/`). The app redeploys and still runs on
   the previous bundle.
2. In the app's **Settings → Secrets**, change two values and keep the rest:

   ```toml
   IRERERO_DATA_URL = "https://api.github.com/repos/Tuyishime-Fabrice/irereroai-data/contents/bundles/irerero-data-2026-10-30.zip"
   IRERERO_DATA_SHA256 = "6c9c8019e8ff8f1fd0a0e1c67aad9d36c8fa7796807d9c3df925b2ac10141e98"  # pragma: allowlist secret
   ```

   The token and `IRERERO_SCHOOLS_PATH` stay as they are (the school list did not change).
   Saving the secrets restarts the app.
3. Check: Overview map shows the 2022 boundaries ("Shyorongi" in Rulindo); Data & methods →
   NCDA connector says the extract is loaded but not shown. Only if the NCDA data-sharing
   agreement allows public display, add `IRERERO_NCDA_DISPLAY = "on"`.

**Rollback:** put back the previous two values (`.../contents/irerero-data.zip` and its SHA-256
`2dcb5360406aec7639574f14f726efbf819639db3ba9612b33c923cd42d716e3`) and save.

## Taking the data down

Delete the zip from the private repository and revoke the token (GitHub → Settings →
Personal access tokens), remove the secrets (with `IRERERO_SCHOOLS_PATH`), and reboot the app. It returns to the demo
data. Nothing has to change in the public repository.

## Before you switch it on

The deployed app shows these figures publicly on screen and in the district brief exports,
each with its source and status. That is the purpose of the app; still, confirm with NISR that
showing the sector-level counts derived from the census sample records is within the terms the
team received them under.
