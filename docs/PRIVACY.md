# Privacy and data protection

> **Not legal advice.** This note records how the platform is designed, mapped to the main duties
> in Rwanda's Law No. 058/2021 of 13/10/2021 relating to the protection of personal data and
> privacy. Before any real deployment, a qualified lawyer and the data protection officer of the
> deploying institution must review it, and the controller must register with the National Cyber
> Security Authority (NCSA) as the law requires.

## What the platform holds

The platform plans and tracks ECD services from counts and areas. It never stores records about
an individual child: no names, photos, dates of birth, IDs or measurements.

| Data | Who it is about | Where | Why |
| --- | --- | --- | --- |
| Weekly centre reports: enrolment by age band and sex, attendance, meals, water, waiting list, referrals, children with a known disability | Centres (aggregate counts) | `weekly_report` | Tracking and early warning |
| Staff accounts: name, work email, password hash (Argon2id), TOTP secret for admins, role and scope | Staff | `user_account` | Sign-in and access control |
| Caregiver accounts: name, mobile number, centre | Caregivers | `user_account` | Sign-in for weekly reports |
| Parent accounts: mobile number, saved searches (a 500 m grid cell and filters) | Parents | `user_account`, `saved_search` | Saved searches, if the parent wants them |
| One-time codes: phone and code hash, attempts, expiry | Parents | `otp_challenge` | Parent sign-in |
| Centre requests and empty searches: 500 m grid cell, sector, age band | No one (never linked to an account) | `demand_signal` | Showing where parents want a centre |
| Audit log: who (account id and role), what, before and after, reason | Staff | `audit_log` | Accountability for every decision |

Signing in is never needed to search for a centre.

## How the law's principles are applied

**Lawful, fair and transparent processing.** The Find page states what is stored. Parents are
told at sign-in that only their phone number and the searches they save are kept, and that they
can delete them.

**Purpose limitation and data minimisation.**
- Counts and areas only. The report form has no field that could hold a child's identity.
- Parent locations are snapped to a 500 m grid cell (EPSG:32735) by the database before anything
  is written. The raw coordinate is never stored or logged
  (`packages/contract/src/irerero_contract/grid.py`;
  `test_centre_request_stores_only_the_grid_cell`).
- Demand signals carry no account id, so a request cannot be traced back to a parent.

**Accuracy.** Reports go through shared validation rules on the phone and the server, and
unusual values must be confirmed. Officers record verification visits. Each centre shows a
reliability score, so planners can see how much to trust it.

**Storage limitation.** Refresh tokens and one-time codes expire (7 days and 10 minutes by
default). Deleting a parent account removes the phone number, saved searches, sessions and codes
(`test_parent_can_delete_their_account`). Before go-live, Phase 2 must add scheduled purging of
expired codes and tokens, and a retention period for demand signals and audit rows that the
controller sets.

**Security.**
- Passwords and one-time codes are hashed with Argon2id. Admins need TOTP as a second factor.
- Tokens live in httpOnly, SameSite=Lax cookies that client JavaScript never sees. Access tokens are
  short-lived, and refresh tokens rotate and can be revoked.
- Access is enforced by the API: role checks on every route, and every centre or area resolved up
  to sector and district and checked against the user's scope (`apps/api/tests/test_rbac.py`).
- The audit log is append-only: database triggers reject updates, deletes and truncation
  (`test_audit_log_cannot_be_rewritten`).
- Secrets are never committed (detect-secrets runs in pre-commit and CI). The API refuses to start
  with the default signing key when demo mode is off.

**Small numbers.** Public pages and the CSV export withhold any count from 1 to 4 (shown as
"<5"), so a small centre's figures cannot single out a child or family
(`apps/api/src/irerero_api/suppression.py`). Staff see unsuppressed counts only within their
scope. Counts of children with a disability at one centre can still be small; Phase 2 should
decide whether staff views also suppress them.

## Data subject rights

| Right | How |
| --- | --- |
| Information | Sign-in and Find pages explain what is kept and why. |
| Access | A parent sees their saved searches on the account page. Phase 1 has no self-service export for staff or caregivers; requests go to the controller. |
| Rectification | An admin corrects a person's role or scope, and the change is audited. Phase 1 has no screen for editing names or contact details. |
| Erasure | Parents delete their own account in one step. Staff and caregiver accounts are deactivated rather than deleted, because audit rows must keep pointing at who decided; a request for erasure of those goes to the controller. |
| Objection | Parents can use Find without an account. |

## Official microdata

NISR and DHS microdata licences forbid redistribution. Raw files go in `data/raw/`, which is
gitignored with every other data folder and with `*.dta`, `*.sav`, `*.tif` and `*.pbf`. A
pre-commit and CI guard rejects data formats and large files anywhere in the repository. Only
derived area-level estimates with intervals enter the database, each linked to the pipeline run
and file checksums that produced it.

## Before a real deployment

1. Register the controller (and any processor) with NCSA.
2. Host the database in Rwanda, or get NCSA authorisation for storage outside Rwanda.
3. Turn demo mode off (`DEMO_MODE=false`), set a strong `JWT_SECRET`, and serve only over HTTPS
   with Secure cookies (`INSECURE_COOKIES` unset).
4. Connect a real SMS gateway for one-time codes under a processing agreement, and require a
   one-time code for caregivers too. In Phase 1 they sign in with phone and centre code only.
5. Set and implement retention periods (see Storage limitation).
6. Write a breach response procedure that meets the law's notification deadlines to NCSA and to
   the people affected.
7. Run a data protection impact assessment covering the weekly reports and demand signals.
