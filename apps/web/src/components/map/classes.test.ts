import { describe, expect, it } from "vitest";

import { classOf, quantileBreaks } from "./classes";
import { hatchLevel } from "./hatch";

describe("map classes", () => {
  it("puts values into five steps", () => {
    const values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
    const breaks = quantileBreaks(values);
    expect(classOf(1, breaks)).toBe(0);
    expect(classOf(10, breaks)).toBe(4);
  });

  it("hatches only uncertain areas, denser when wider", () => {
    expect(hatchLevel(0.1)).toBe(0);
    expect(hatchLevel(0.16)).toBe(1);
    expect(hatchLevel(0.3)).toBe(3);
    expect(hatchLevel(null)).toBe(0);
  });
});
