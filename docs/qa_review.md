# QA review: IrereroAI (24 October 2026)

A full review of the demo build at commit `3d7593e`: the idea and methods, every screen and
button for every role, the exports, the code and the pipeline. Everything below was **run and
observed**, not just read. Line references point at the code as reviewed.

> **Status (25 October 2026).** Fixed, each with a test that fails on the old code: H1, H2, H3,
> M1, M2, M3, M4 and M6. M5: the PDF table now uses the same suppression as the CSV. Whether a 0
> should still be exported as "fewer than 10" is left to the team, because the README and
> methodology state the rule as "counts of children under 10". The low items and the
> methodology points are not changed yet.

## How it was tested

| Area | What was done | Result |
| --- | --- | --- |
| CI, locally | secrets scan, file-size guard, `ruff check`, `ruff format --check`, `irerero.data --check`, `irerero.docs --check`, demo build, `pytest` | All pass. Build 8.6 s; **106 tests** pass in 31 s |
| Scripted journeys | Streamlit `AppTest` scripts clicking the real widgets: planner (rank, basket, create plan, approve, edit, reject, status), caregiver (check-in, lessons, quiz, certificate), officer (confirm, set aside), admin (role form) | 3 high and 6 medium bugs below |
| Robustness | Planner and analyst switched through **all 30 districts on all 5 district screens** | 0 exceptions |
| Browser | Headless Chromium at 1280, 1440, 1920 and 390 px (mobile), every role and page, console errors, layout overflow | No app errors; layout issues below |
| Exports | Downloaded the brief PDF and CSV with "Include simulated" off and on, extracted the text | 1 leak and 1 inconsistency below |
| Security | Entered `<img src=x onerror=alert(1)>` as a rejection reason | Rendered as text: escaping holds |
| Numbers | Re-computed the README's model table, coverage and back-test from the built database | All match the README |
| Speed | Timed each screen | 0.1 to 0.3 s per interaction; 8 s cold start with the build |

## Overall verdict

This is a strong, unusually honest hackathon project. Its strengths:

- The question is clear and tied to NST2.
- The scope is tight: formal pre-primary only, with the definition on every screen.
- Uncertainty is shown everywhere: ranges, conformal intervals, rank stability and a back-test.
- People make the decisions, and every decision goes to an append-only audit log.
- Privacy is designed in: counts only, averages over at least 3 caregivers, small-number suppression.
- Simulated values are labelled consistently.

The code is clean and typed, and the app never crashed during testing.

The weaknesses are in the **flows between screens** (buttons that report success but lead
nowhere), **one break of the "simulated values are left out of exports" promise**, and **three
methodological points** that a careful judge or a real planner would raise.

---

## 1. Bugs, by severity

### High

**H1. "Add to plan" does nothing once a plan exists.**
On *District priorities* (`app/views/priorities.py:175`) and *Sector diagnosis*
(`app/views/sector.py:162`), the button shows a success message ("Cyeza added. Open Action plans
to create or review the plan."). But the basket is only read by the **Create plan** form
(`app/views/plan.py:248`), and that form is hidden once a plan exists. Reproduced: create a plan,
then add Cyeza from *Sector diagnosis*. Cyeza never enters the plan, and nothing in the UI can add
it. There is no `add_item` in `irerero/track/plans.py`.
*Fix:* add `plans.add_items(...)` (planner-only, audited as `plan_item.add`), and show
"Add N sectors to the current plan" on *Action plans* when the basket is not empty.

**H2. The PDF leaks simulated LEARN figures when simulated values are excluded.**
With "Include simulated values" **off**, the downloaded PDF says "Values withheld: simulated."
It then prints `LEARN pilot: 50 of 72 required courses completed, 21 overdue (simulated).`
Cause: `training_line` is appended unconditionally (`app/views/brief.py:199`). This breaks the
promise in the README and the export panel.
*Fix:* drop `training_line` unless `include` is on or the LEARN data is real. Add a test that
extracts the PDF text and asserts that no simulated figure appears.

**H3. After passing a quiz, the certificate disappears.**
On *Caregiver learning*, the "Open a course" selectbox (`app/views/caregiver.py:184`) has no
`key`, and its options are re-sorted by status. When a course becomes *completed*, it moves to the
end of the list, the widget resets, and a **different course** opens. Reproduced: pass
safeguarding 5/5, then rerun. The selection jumps to another assignment and shows 0 certificate
buttons. The certificate appears only if the caregiver finds the course again.
*Fix:* give the selectbox a `key` and keep the selection, or `st.rerun()` after a pass with the
completed course preselected. Also show the download button right away in the success message.

### Medium

**M1. Approving silently drops an edited "Places" value.**
The decision form always shows "Places (for an edit)". If a planner changes it from 1,026 to 7
and picks **approve**, the item is saved with 1,026 and no warning (`app/views/plan.py:351`;
`plans.decide` uses `places` only for `edit`).
*Fix:* if the value changed and the decision is not *edit*, show an error, or switch to *edit*
and ask for the reason.

**M2. A check-in correction can flip "No water" back to "Yes".**
The form pre-fills the counts from the last check-in, but **water** always defaults to "Yes" and
**main challenge** to "None" (`app/views/caregiver.py:99-108`). Reproduced: the last check-in had
`water_available=False, main_challenge=no_water`, and the form showed "Yes · Yego". A caregiver
who opens the form to correct one number can unknowingly overwrite a real WASH problem.
*Fix:* pre-fill both from `last`, as the numbers already are.

**M3. The target text contradicts the target slider.**
With the target set to 80%, the Overview callout still says "65% by 2028/29"
(`app/views/national.py:24`). The *Action plans* banner says "NST2 target: 65% … by 2028/29"
(`app/views/plan.py:71`), while the subtitle and status on the same screen use 80%.
*Fix:* label the callout "NST2 target 65%" and show "Your target: 80%" separately when they
differ.

**M4. In the what-if, the chosen sectors change nothing.**
The projection reached 40.2% whether the plan sectors, one sector or all 12 sectors were chosen
(`app/views/plan.py:150-164`). Only the sentence and a warning change. A planner will believe
siting matters to the forecast.
*Fix:* either remove the selector, or cap the rooms by each chosen sector's gap and apply a fill
rate (see methodology point 3).

**M5. Small-number suppression is applied inconsistently.**
- In the CSV, `places` counts as a child count (`irerero/brief.py:12`), so **0 places** (a sector
  already at target) is exported as "fewer than 10". That hides a useful fact and protects no
  one: places needed is a planning figure, not a count of real children.
- The PDF table does not go through `suppress()` at all (`app/views/brief.py:193`), so the PDF and
  CSV disagree whenever a value is under 10.

*Fix:* suppress child counts only, and send the PDF table through the same `export()` path.

**M6. The ranking table is still clipped on laptop screens.**
Commit `0a93f08` ("fit the priority ranking table without horizontal scrolling") holds only at
1920 px. The table is 641 px wide in a 517 px panel at 1280 px, and in a 627 px panel at 1440 px.
The "Top-3 stable" column is cut off.
*Fix:* shorten the headers or drop the "> 1 km" column under about 1500 px, or give the main
column more width (`st.columns([2.6, 1])`).

### Low

- **L1.** Clicking "Add to plan" with nothing selected shows a green "0 sector(s) ready"
  (`priorities.py:175`). Disable the button when the selection is empty.
- **L2.** A sector already at target (Shyogwe, "At target · 0 places") can be added as a plan
  item. Warn or block.
- **L3.** After submitting a check-in, the "This month's check-in" KPI still says **Due** until
  the next interaction, because the KPIs are drawn above the form. `st.rerun()` after a
  successful submit.
- **L4.** The quiz accepts a submission with no answers ("0 of 5"). Ask the caregiver to answer
  all five first.
- **L5.** The admin role form saves any free-text district or sector ID (it saved
  `NOT-A-DISTRICT`), cannot clear a field, and has no effect on the demo picker. Use selectboxes
  of real IDs, and say plainly that the demo picker ignores it.
- **L6.** The top-bar **bell** (`irerero/ui/theme.py:384`) has a "Notifications" tooltip but does
  nothing, and the breadcrumbs are not links. Either wire the bell up (pending decisions, overdue
  courses, centres to follow up) or remove it. A dead control looks unfinished to judges.
- **L7.** On mobile (390 px), the ranking table scrolls sideways, so Places, Bottleneck and
  Stability start off-screen. The floating logo and sidebar toggle also overlap content while
  scrolling. Caregivers are the users most likely to be on a phone; their form works, but
  "Children present" shows `31.00` (use `step=1` or `format="%d"`).
- **L8.** The README says "99 tests" twice; there are 106.

---

## 2. Feedback on the idea and the methods

**1. One target is applied to two different measures.**
PLAN and DIAGNOSE apply the target to **census-based attendance of 3 to 5 year olds**. TRACK
applies it to **MINEDUC gross enrolment** (pupils, including over-age children, per child aged 3
to 5). The NST2 65% is a gross rate. Applied to a net-style attendance rate, it overstates the
places needed and makes the screens hard to reconcile. Muhanga reads 26% attending on the brief,
27.9% enrolment on *Action plans*, and 20% for Cyeza; Rwanda reads 32.5% on the Overview. A
planner will ask which one is "the" number.
*Suggestion:* say on PLAN which measure the target is applied to, or convert it (GER to NER ratio
by district). Add one line in the brief that reconciles the two.

**2. The bottleneck rules hardly discriminate.**
At 65%, **272 of 416 sectors (65%) are SUPPLY**, and 67 of those are the "none of the above"
default. **88% of sectors** pass the "30% of children beyond 1 km" test, so it separates almost
nothing, partly because distance is straight-line to OSM schools that don't mark pre-primary.
Because the first rule that applies wins, CAPACITY is the main bottleneck in only 8 sectors.
*Suggestions:*
- Replace the fallback SUPPLY with **"Unclear: needs local review"**, which is more honest and
  more useful.
- Set the distance threshold as a percentile, or calibrate it once real data is loaded.
- Show co-occurring bottlenecks as equals (several labels), not first match wins.

**3. The what-if assumes every new place is filled.**
That contradicts DEMAND sectors, where the diagnosis says children don't attend even though a
school is near. Also, the trend already includes past growth in places, so added rooms may count
twice.
*Suggestion:* site rooms by sector, cap them at the sector's gap, and apply a fill rate that is
lower for DEMAND sectors.

**4. The calendar has moved on.**
It is October 2026, so 2025/26 is over, but it is still treated as a projection year. "Places a
year still needed" divides by 4 years (`app/views/plan.py:90-91`, `len(PROJECTION_YEARS)`), so it understates
the yearly need by about a quarter.
*Suggestion:* derive the remaining years from today's date.

**5. Plans need a life cycle.**
There is one plan per district, items cannot be added or removed, and there are no versions.
District planning is revised every year, so support "add to the current plan" (H1), "start a new
version", and keep the old one read-only in the audit trail.

**6. Real data is the biggest lever.**
Everything except the boundaries is simulated. The pipeline is ready for real files, and a
census PDF parser already exists. Loading even census Table 2.5 and the MINEDUC yearbooks would
turn this from "the method works" into "here is what Muhanga should do".

**7. Keep doing these, because they are the project's edge:**
- the SIMULATED badges and the export exclusion
- "associated with, not caused by"
- rank stability
- the rule of keeping the simplest model within 1 point
- conformal intervals with coverage by urban and rural
- the no-ranking-of-caregivers rule

Few teams do this.

---

## 3. Engineering notes

- **Tests miss the cross-screen journeys**, which is where every high bug was. Add `AppTest`
  journeys for: basket → existing plan, PDF without simulated values (extract the text), quiz
  pass → certificate, and check-in correction keeps the water answer.
- **The audit log is append-only at the ORM level only** (`irerero/audit.py`). A bulk SQL
  `DELETE` or `UPDATE` skips the event hooks. For a real deployment, revoke UPDATE and DELETE on
  `audit_log` for the app's database role, or add a trigger.
- **`data.clear()` after each officer confirmation** (`app/views/officer.py:88`) empties every
  cached table, so the next screen recomputes everything. It is fast today; clear only what
  changed if the data grows.
- **The demo picker lets anyone be any role.** That is fine for the demo and is labelled, but
  `DEMO_MODE` defaults to `true` (`irerero/ui/roles.py:20`). Default it to `false` so a real
  deployment cannot open with it by accident.

## Suggested order of work

1. H2 (export leak) and H1 (add to an existing plan): these are trust and core-flow issues.
2. H3, M1 and M2: small fixes with high user impact.
3. M3 and the target-measure wording (methodology point 1).
4. "Unclear" in place of the default SUPPLY, and years left from today's date (methodology points
   2 and 4).
5. The rest, plus the journey tests.
