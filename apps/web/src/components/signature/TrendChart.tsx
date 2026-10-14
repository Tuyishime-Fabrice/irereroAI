"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type Series = { key: string; label: string; colour: string; dashed?: boolean };

/** The one chart style: thin lines on the paper grid, mono figures. Always paired with a table. */
export function TrendChart({
  data,
  series,
  height = 180,
  title,
}: {
  data: Record<string, number | string | null>[];
  series: Series[];
  height?: number;
  title: string;
}) {
  return (
    <figure aria-label={title}>
      <div style={{ height }} aria-hidden inert>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
            <CartesianGrid stroke="var(--line)" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11, fill: "var(--ink-muted)" }}
              stroke="var(--line)"
            />
            <YAxis
              tick={{ fontSize: 11, fill: "var(--ink-muted)" }}
              stroke="var(--line)"
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{
                background: "var(--surface)",
                border: "1px solid var(--line)",
                borderRadius: 6,
                fontSize: 12,
              }}
            />
            {series.map((s) => (
              <Line
                key={s.key}
                type="linear"
                dataKey={s.key}
                name={s.label}
                stroke={s.colour}
                strokeWidth={2}
                strokeDasharray={s.dashed ? "4 3" : undefined}
                dot={{ r: 2 }}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="mt-1 flex flex-wrap gap-4 text-xs text-ink-muted">
        {series.map((s) => (
          <span key={s.key} className="inline-flex items-center gap-1.5">
            <span aria-hidden className="h-0.5 w-4" style={{ background: s.colour }} />
            {s.label}
          </span>
        ))}
      </figcaption>
      <table className="sr-only">
        <caption>{title}</caption>
        <thead>
          <tr>
            <th scope="col">Week</th>
            {series.map((s) => (
              <th key={s.key} scope="col">
                {s.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={String(row.label)}>
              <th scope="row">{row.label}</th>
              {series.map((s) => (
                <td key={s.key}>{row[s.key] ?? "–"}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
