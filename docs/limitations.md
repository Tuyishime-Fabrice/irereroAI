# Limitations

## Data

- **The demo build is simulated.** Every value from a missing file is simulated, labelled with
  a red SIMULATED badge and left out of exports by default. Only the boundaries are real:
  geoBoundaries shapes, CC BY 4.0, from NISR open data, simplified, without NISR codes.
- **Home-based ECD may be missing.** Census "nursery attendance" may not count home-based ECD,
  so the gap is the *formal* pre-primary gap. Census, MINEDUC and NCDA figures are never added
  together.
- **The crosswalk is unreviewed.** Its rows come from geoBoundaries spellings. Each source's
  spellings and the NISR codes must be reviewed (`reviewed = yes`) before real files are
  loaded.
- **The census PDF parser was written without a real profile at hand.** Check the first parsed
  district by hand. The build's sum checks catch most misreads, and a hand-typed CSV in the
  same format works too.

## Estimates

- **Constant age structure.** The 3-5 share of the population is held at its 2022 value to
  2029. Falling fertility would lower it, so 2029 child counts, and places needed, may be
  overstated.
- **Attendance in 2026** moves the census 2022 rate by the district's MINEDUC trend. A sector
  whose trend differs from its district's is mis-estimated.
- **Ranges omit some error.** Where a source gives no range, a documented assumption sets it:
  3% for the projection and 5% for drift in sector shares. Ranges do not include census
  enumeration error.

## Distance

- **OSM does not say which schools have pre-primary.** Every school and kindergarten counts.
- **Straight-line distance** understates the walk, so it is labelled *indicative*. Children
  more than 500 m from any road keep their straight-line distance.
- **Even grid.** While WorldPop is missing, children are spread evenly over the sector, which
  ignores where people actually live.

## Models and rules

- **Associations, not causes.** The peer model's drivers explain its expectation, not what
  would change attendance.
- **Clustered residuals.** Significant Moran's I means nearby sectors share unmodelled factors.
  Read DEMAND flags in clustered areas with care.
- **Short trend.** Five yearbook points make a short series. The 2029 range assumes the linear
  trend continues and does not include structural breaks: fee policy, new data definitions,
  COVID-era disruption.
- **Thresholds are conventions.** 30% beyond 1 km, worst quarter nationally, and the national
  top half for a "large gap" are documented choices, not standards. They are set in
  `irerero/config.py`.
- **District context.** Capacity and stunting are district values applied to every sector of
  the district.

## LEARN

- **Simulated pilot.** Caregivers, check-ins and progress for Muhanga are simulated (seed 2026),
  with planted problems to show the triggers, and exist only in demo mode. No real caregiver
  check-ins or course progress are connected yet; the LEARN screens say so.
- **NCDA extract.** The real extract (34,448 active services, October 2026) is loaded but shown
  only when the data-sharing agreement allows (`IRERERO_NCDA_DISPLAY`). It has no capacity and
  counts children aged 3 to 6, so free places are not computed from it, and it is not a live
  feed or a proven-complete register.
- **Draft content.** Lesson text is a placeholder citing its source until the team finalises
  it. Quiz questions and Kinyarwanda labels are drafts awaiting review.
- **Quiz scores** measure course knowledge, not teaching quality. Caregivers are never ranked.

## Product

- **Demo roles.** The role picker uses fictional accounts; a deployment needs real sign-in.
- **SQLite** is local. Set `DATABASE_URL` to Postgres (Supabase or Neon) so plans, check-ins
  and the audit log survive restarts on Streamlit Community Cloud.
