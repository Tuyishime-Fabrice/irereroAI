/** Illustrative values for the design gallery only. Never shown as data anywhere else. */
import type { Schemas } from "@/lib/api/client";

export const SAMPLE_SOURCE: Schemas["SourceOut"] = {
  table: "need_estimate",
  source: "Sample source for the design gallery",
  reference_year: 2026,
  origin: "simulated",
};

export const SAMPLE_DRIVERS: Schemas["DriverOut"][] = [
  {
    feature: "parent_demand",
    label_en: "Parents asked for a centre here",
    label_rw: "Ababyeyi basabye irerero hano",
    contribution: 0.45,
  },
  {
    feature: "stunting_risk",
    label_en: "High stunting risk",
    label_rw: "Ibyago byinshi byo kugwingira",
    contribution: 0.35,
  },
  {
    feature: "uncovered_children",
    label_en: "Many children without a place nearby",
    label_rw: "Abana benshi badafite umwanya hafi",
    contribution: 0.2,
  },
];

const range = (estimate: number, low: number, high: number) => ({ estimate, low, high });

export const SAMPLE_RECOMMENDATION: Schemas["RecommendationOut"] = {
  id: "00000000-0000-0000-0000-000000000001",
  rank: 1,
  action: "build",
  site_id: "SAMPLE",
  site_name: "Sample village site",
  sector_code: "SAMPLE",
  sector_name: "Sample sector",
  centre_code: null,
  lon: 30,
  lat: -1.5,
  children_reached: range(60, 52, 60),
  high_risk_children_reached: range(30, 24, 36),
  mothers_under3_reached: range(5, 3, 7),
  children_supported: 0,
  cost: range(18_000_000, 13_500_000, 22_500_000),
  drivers: SAMPLE_DRIVERS,
  sources: [SAMPLE_SOURCE],
  status: "proposed",
  explanation_en: "Sample explanation text for the design gallery.",
  explanation_rw: "Ibisobanuro by'urugero.",
  decisions: [],
};

export const SAMPLE_OUTCOMES: Schemas["OutcomesOut"] = {
  children_reached: range(355, 355, 355),
  uncovered_remaining: range(68_400, 59_300, 77_400),
  high_risk_reached: range(166, 132, 200),
  mothers_under3_reached: range(16, 10, 22),
  children_supported: 157,
  cost_rwf: 115_900_000,
  actions: { build: 5, support: 3, upgrade: 1 },
};

/** Abstract squares, clearly not geography. */
export const SAMPLE_AREAS = [0, 1, 2, 3, 4, 5].map((i) => {
  const x = 30 + (i % 3) * 0.05;
  const y = -1.5 - Math.floor(i / 3) * 0.05;
  return {
    id: `sample-${i}`,
    name: `Sample shape ${i + 1}`,
    value: 400 + i * 300,
    uncertainty: [0.05, 0.1, 0.16, 0.21, 0.27, 0.12][i] ?? 0,
    geometry: {
      type: "Polygon" as const,
      coordinates: [
        [
          [x, y],
          [x + 0.045, y],
          [x + 0.045, y - 0.045],
          [x, y - 0.045],
          [x, y],
        ],
      ],
    },
  };
});

export const SAMPLE_WEEKS = Array.from({ length: 12 }, (_, i) => {
  const d = new Date(Date.UTC(2026, 6, 6 + i * 7));
  return d.toISOString().slice(0, 10);
});
