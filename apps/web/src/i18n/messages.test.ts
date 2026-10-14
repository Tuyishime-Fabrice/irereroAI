import { describe, expect, it } from "vitest";

import en from "../../messages/en.json";
import rw from "../../messages/rw.json";

function keys(tree: object, prefix = ""): string[] {
  return Object.entries(tree).flatMap(([key, value]) =>
    typeof value === "object" && value !== null
      ? keys(value, `${prefix}${key}.`)
      : [`${prefix}${key}`],
  );
}

describe("messages", () => {
  it("has the same keys in English and Kinyarwanda", () => {
    expect(keys(rw).sort()).toEqual(keys(en).sort());
  });

  it("has no empty strings", () => {
    const empty = (tree: object): boolean =>
      Object.values(tree).some((v) => (typeof v === "string" ? !v.trim() : empty(v as object)));
    expect(empty(en)).toBe(false);
    expect(empty(rw)).toBe(false);
  });
});
