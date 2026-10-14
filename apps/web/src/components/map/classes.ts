export const NEED_COLOURS = ["#F6E7D3", "#EBC28E", "#D98E52", "#B4542F", "#6E2A1A"] as const;
/** Readable label colour on each step (ink on the light steps, white on the dark ones). */
export const NEED_LABEL = ["#1E1B18", "#1E1B18", "#1E1B18", "#FFFFFF", "#FFFFFF"] as const;

/** Five quantile breaks, so each colour step holds about the same number of areas. */
export function quantileBreaks(values: number[]): number[] {
  const sorted = [...values].sort((a, b) => a - b);
  if (!sorted.length) return [];
  return [0.2, 0.4, 0.6, 0.8].map(
    (q) => sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))] as number,
  );
}

export function classOf(value: number, breaks: number[]): number {
  return breaks.filter((b) => value >= b).length;
}
