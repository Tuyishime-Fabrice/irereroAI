const MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];

/** Month key (in the "months" messages) and day of a week's Monday, e.g. ("sep", 21). */
export function weekParts(isoDate: string): { monthKey: string; day: number } {
  const [, month, day] = isoDate.split("-").map(Number);
  return { monthKey: MONTHS[(month ?? 1) - 1] ?? "jan", day: day ?? 1 };
}

export function weekNumber(weeks: string[], isoDate: string): number {
  return weeks.indexOf(isoDate) + 1;
}
