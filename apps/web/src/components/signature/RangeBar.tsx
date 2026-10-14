import { formatRange, type RangeLike, formatNumber } from "@/lib/format/numbers";

/** An estimate with its interval: band for the range, tick for the estimate. */
export function RangeBar({
  value,
  max,
  label,
  format = formatNumber,
}: {
  value: RangeLike;
  max: number;
  label?: string;
  format?: (v: number) => string;
}) {
  const scale = (v: number) => `${Math.max(0, Math.min(100, (v / (max || 1)) * 100))}%`;
  const text = formatRange(value, format);
  return (
    <span
      className="inline-flex w-full min-w-28 flex-col gap-1"
      role="img"
      aria-label={label ? `${label}: ${text}` : text}
    >
      <span className="tabular text-sm text-ink" aria-hidden>
        {text}
      </span>
      <span aria-hidden className="relative block h-2 w-full rounded-sm bg-line">
        <span
          className="absolute inset-y-0 rounded-sm bg-[repeating-linear-gradient(135deg,var(--kivu)_0_2px,transparent_2px_5px)] opacity-60"
          style={{
            left: scale(value.low),
            width: `calc(${scale(value.high)} - ${scale(value.low)})`,
          }}
        />
        <span
          className="absolute -top-0.5 h-3 w-[3px] -translate-x-1/2 rounded-sm bg-kivu"
          style={{ left: scale(value.estimate) }}
        />
      </span>
    </span>
  );
}
