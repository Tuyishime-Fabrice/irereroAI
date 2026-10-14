const whole = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });

export function formatNumber(value: number | null | undefined): string {
  return value === null || value === undefined ? "–" : whole.format(Math.round(value));
}

export function formatShare(value: number | null | undefined): string {
  return value === null || value === undefined ? "–" : `${Math.round(value * 100)}%`;
}

/** 25 000 000 -> "25.0 M"; amounts below a million are written in full. */
export function formatRwf(value: number, compact = false): string {
  if (compact && value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)} M RWF`;
  }
  return `${formatNumber(value)} RWF`;
}

export type RangeLike = { estimate: number; low: number; high: number };

export function formatRange(range: RangeLike, format: (v: number) => string = formatNumber) {
  const low = format(range.low);
  const high = format(range.high);
  return low === high ? format(range.estimate) : `${format(range.estimate)} (${low}–${high})`;
}
