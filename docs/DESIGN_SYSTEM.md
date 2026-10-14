# Design system: Imigongo

IrereroAI should look like a serious Rwandan public-sector product, not a generic AI dashboard.
The identity draws on Imigongo, the geometric black, white and earth-red art of eastern Rwanda,
used with restraint: a 6 px zigzag band, one spiral in empty states, and the hatching that marks
uncertain estimates on maps. Nothing else is decorated.

Run the web app in development (or build with `NEXT_PUBLIC_DESIGN_PAGE=true`) and open
`/design` to see every token and component with sample values.

## Rules

- No gradients, glass effects, sparkle icons for AI, emoji, stock photos of children or heavy
  shadows. Cards have a 1 px border and a 6 px radius.
- Sentence case everywhere. AI output is called a "Suggestion", never an "AI decision".
- 8 px spacing grid. Touch targets are at least 40 px (48 px in the parent and caregiver flows).
- Colour is never the only signal: severities carry a word and an icon, uncertainty carries
  hatching and a table column, chart series carry labels.

## Colour tokens

Defined once in `apps/web/src/styles/tokens.css` and exposed to Tailwind as `bg-paper`,
`text-ink` and so on.

| Token | Value | Use |
| --- | --- | --- |
| `--paper` | `#F6F1E9` | App background |
| `--surface` | `#FFFDF9` | Cards, panels |
| `--ink` | `#1E1B18` | Text, Imigongo black |
| `--ink-muted` | `#6B6259` | Secondary text |
| `--line` | `#E3D9CB` | Dividers and card borders |
| `--line-strong` | `#8F8478` | Borders of inputs and controls |
| `--clay` | `#B4472B` | Brand accent, simulated-data label |
| `--ochre` | `#C98B2B` | Warning and "edited" fills and borders |
| `--ochre-text` | `#855A12` | Warning and "edited" text |
| `--kivu` | `#1D5C63` | Primary actions, links, "approved" |
| `--success` | `#2F7D4F` | Resolved, healthy |
| `--danger` | `#B3261E` | Critical alerts, reject |

Two additions to the brief, both for WCAG 2.2 AA:

- **`--ochre-text`**: ochre is 2.6:1 on paper, too light for text. Ochre stays for fills, borders
  and the reliability meter; text in the warning and edited states uses `--ochre-text` (5.4:1).
- **`--line-strong`**: `--line` is 1.4:1 against the surface, fine for dividers but not for the
  edge of an input, which needs 3:1. Inputs, selects and secondary buttons use `--line-strong` (3.6:1).

`--success` is 4.48:1 on paper and 4.96:1 on the surface, so success text sits on surfaces only.

`apps/web/src/styles/contrast.test.ts` checks every text and control pairing in both themes on
every CI run.

### Projector theme

A high-contrast theme for live presentations in bright rooms: white background, black text,
darker accents. Toggle "Projector" in the top bar; the choice is remembered in the browser.

### Need scale

Five steps from sand to burnt earth for choropleths: `#F6E7D3`, `#EBC28E`, `#D98E52`, `#B4542F`,
`#6E2A1A`. Luminance falls steadily, so the order reads in greyscale and for the common forms of
colour blindness. Labels on the two darkest steps are white, on the others ink. Steps are
quantiles, so each holds about the same number of areas.

## Uncertainty as Imigongo hatching

Our visual signature and our honesty statement. On every choropleth, an area whose estimate has
a wide range is overlaid with a fine zigzag hatch; the hatch gets denser as the range widens.

| Level | Relative half-width of the widest interval | Hatch |
| --- | --- | --- |
| 0 | below 15% | none |
| 1 | 15% to 20% | one zigzag row per tile |
| 2 | 20% to 25% | two rows |
| 3 | 25% and above | three rows |

The hatch is drawn at runtime (`components/map/hatch.ts`) as a dark line on a light halo, so it
stays visible on every step of the scale. The legend explains it in one line, and the table
version of every map has a "certainty" column with the same levels in words.

## Typography

- **Fraunces** for page titles and big numbers.
- **IBM Plex Sans** for the interface.
- **IBM Plex Mono** with tabular figures for data tables and ranges (`.tabular`).

Fonts are bundled at build time by `next/font`, so the app works offline.

## Logo

The mark is three nested Imigongo diamonds (ink, clay, paper) and works at 16 px as the favicon
(`app/icon.svg`). The wordmark is "Irerero" in Fraunces with "AI" in Plex Mono small capitals.

## Signature components

All live in `apps/web/src/components/signature/` (the map in `components/map/`). Each is built
once and reused.

| Component | What it shows |
| --- | --- |
| `DecisionCard` | Rank, action, target, impact with ranges, top drivers, cost range, source chips, full explanation, and Approve, Edit and Reject. Reject requires a reason code; "other" also requires a note. |
| `DriverBars` | The top three reasons as bars, relative to the strongest, in the current language. |
| `RangeBar` | An estimate as a tick on a hatched interval band, with the numbers in mono. |
| `SourceChip` | Source and year, coloured by origin. Hover, tap or focus reveals the table, origin and what that origin means. |
| `HatchedChoropleth` | Areas in the need scale with uncertainty hatching, point layers for centres, parent demand and candidate sites, a legend, an offline fallback, and a table alternative. |
| `WeekScrubber` | Week 1 to 12 slider with play, to replay how alerts and coverage changed as reports arrived. |
| `AlertRow` | Severity (word, icon and colour), signal, centre, reason in plain words, age, status, assignee and an action slot. |
| `ReliabilityMeter` | Five segments plus the percentage and a word. |
| `ImpactCounter` | Countable outcomes with ranges, optional difference from the baseline, and the note that nothing here predicts a change in stunting. |
| `SmsPreview` | A basic phone showing the coded SMS and the reply, next to what was parsed. |
| `SimulatedWatermark` | The honesty label: a pill in the top bar whenever simulated records are on screen, an inline tag, and a stamp for printed pages. |
| `TrendChart` | The one chart style (Recharts), always with a screen-reader table and a text legend. |

### How the simulated label works

Every API response carries `provenance.origins`. Components that show data call
`useProvenance(response.provenance)`; the shell reads the union of origins on screen and shows
the SIMULATED DATA pill whenever it includes `simulated`. A page cannot show simulated data
without the label unless it skips that call, which code review should catch.

## Language

English and Kinyarwanda message files in `apps/web/messages/`. Every Kinyarwanda string is a
draft until reviewed; see [i18n-review.md](i18n-review.md). In Kinyarwanda mode the top bar
shows a "draft translation" label until the review is done.
