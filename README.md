# IrereroAI

An AI planning and action platform for early childhood development (ECD) in Rwanda, built for
the NISR 2026 Big Data Hackathon, Track 3 (Open Innovation).

> In my district, which sectors need action first, what is holding ECD back there, and are we
> on track for the NST2 target of 65% pre-primary enrolment by 2028/29?

**Scope: the formal pre-primary gap.** Children aged 3 to 5 attending nursery or pre-primary
school, as counted by the 2022 Census (Table 2.5) and MINEDUC. Census, MINEDUC and NCDA
enrolment figures are never added together. IrereroAI complements NCDA's ECD Mapping System and
is built to consume its data.

Four modules form one loop: **PLAN** (where to put pre-primary places) → **DIAGNOSE** (what is
holding ECD back) → **LEARN** (caregiver check-ins and training, pilot Muhanga) → **TRACK** (are
we on track for 2029).

> Work in progress. The data layer is in place; the modules and the full documentation follow.

## Quick start

Requires Python 3.11 and [uv](https://docs.astral.sh/uv/).

```bash
make install   # dependencies
make sources   # create data/raw/<dataset>/ and list which files are present
make data      # build the analysis tables (demo data stands in for missing files)
make test
```

## Data

[DATA_SOURCES.md](DATA_SOURCES.md) lists each of the 12 datasets: file name, format, required
columns, geographic level, reference period, licence and the module that uses it. Put a real file
in `data/raw/<dataset>/` and run `make data`; nothing else changes.

**Never present simulated data as real.** While a file is missing, the build reads a stand-in
from `data/demo/`, and every value from it carries the status *simulated*. The only real data in
the repository are the simplified geoBoundaries shapes (CC BY 4.0, from NISR open data). No NISR
microdata is committed.

Every number carries a status: observed, published estimate, model estimate, user input or
simulated.

## Team

Contact: fabricetuyishime2050@gmail.com
