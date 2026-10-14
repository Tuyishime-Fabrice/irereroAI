import { describe, expect, it } from "vitest";

import { formatRange, formatRwf, formatShare } from "./numbers";

describe("number formatting", () => {
  it("collapses a range with no spread", () => {
    expect(formatRange({ estimate: 60, low: 60, high: 60 })).toBe("60");
    expect(formatRange({ estimate: 1234, low: 1100, high: 1400 })).toBe("1,234 (1,100–1,400)");
  });

  it("formats francs and shares", () => {
    expect(formatRwf(25_000_000, true)).toBe("25.0 M RWF");
    expect(formatRwf(800_000, true)).toBe("800,000 RWF");
    expect(formatShare(0.388)).toBe("39%");
  });
});
