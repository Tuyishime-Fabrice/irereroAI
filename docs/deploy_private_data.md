# Real data on the deployed app, kept private

The public repository holds no NISR, MINEDUC or other received data, and never will. To show
real figures on the deployed app (Streamlit Community Cloud), the team keeps a **private data
bundle** somewhere only the app can read, and gives the app three secrets. Without them the
app runs on the labelled demo data, as it always has.

## What is in the bundle, and what is not

| In the bundle (`make bundle`) | Never in the bundle |
| --- | --- |
| What `make intake` staged in `data/raw/<dataset>/`: census sector counts (weighted), district projections, COD-AB boundaries, EICV7 district rates, and any dataset staged later | `data/raw/_received/`: every original, including the census 2022 sample records (person-level) |
| `MANIFEST.json`: the SHA-256 of every file | Tokens, passwords or any secret |

The census sample records stay on the machine that received them. The bundle holds only the
same aggregates the app shows on screen.

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

## What the app checks before using the bundle

- The address is `https` (no plain-text download), and the token is sent only to it.
- The zip's SHA-256 equals `IRERERO_DATA_SHA256`, so a changed or swapped file is refused.
- Every file matches `MANIFEST.json`, and every path is a known dataset folder (no `..`, no
  absolute paths, no `_received`).
- If any check fails, nothing is written: the app shows a notice saying why (never the token
  or the address) and keeps the demo data.

## Updating the data

When new files arrive: `make intake FILES="..."`, `make data`, check the screens, then
`make bundle`. Upload the new zip over the old one, put the new SHA-256 in
`IRERERO_DATA_SHA256`, and reboot the app. The app notices the new bundle and rebuilds.

## Taking the data down

Delete the zip from the private repository and revoke the token (GitHub → Settings →
Personal access tokens), remove the three secrets, and reboot the app. It returns to the demo
data. Nothing has to change in the public repository.

## Before you switch it on

The deployed app shows these figures publicly on screen and in the district brief exports,
each with its source and status. That is the purpose of the app; still, confirm with NISR that
showing the sector-level counts derived from the census sample records is within the terms the
team received them under.
