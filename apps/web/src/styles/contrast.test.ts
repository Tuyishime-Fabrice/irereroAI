import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const css = readFileSync(join(__dirname, "tokens.css"), "utf8");

function tokens(selector: string): Record<string, string> {
  const block = css.slice(css.indexOf(selector));
  const body = block.slice(block.indexOf("{") + 1, block.indexOf("}"));
  return Object.fromEntries(
    [...body.matchAll(/--([\w-]+):\s*(#[0-9a-fA-F]{6})/g)].map((m) => [m[1], m[2]]),
  );
}

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  }) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

// [foreground, background, minimum ratio]: text needs 4.5:1, controls and large marks 3:1.
const PAIRS: [string, string, number][] = [
  ["ink", "paper", 4.5],
  ["ink-muted", "paper", 4.5],
  ["ink-muted", "surface", 4.5],
  ["clay", "surface", 4.5],
  ["ochre-text", "paper", 4.5],
  ["kivu", "paper", 4.5],
  ["kivu", "kivu-tint", 4.5],
  ["danger", "surface", 4.5],
  ["success", "surface", 4.5],
  ["line-strong", "surface", 3],
];

describe.each([":root {", ':root[data-theme="projector"]'])("tokens in %s", (selector) => {
  const theme = { ...tokens(":root {"), ...tokens(selector) };
  it.each(PAIRS)("%s on %s meets %s:1", (fg, bg, minimum) => {
    expect(contrast(theme[fg] as string, theme[bg] as string)).toBeGreaterThanOrEqual(minimum);
  });
  it("white text on primary buttons meets 4.5:1", () => {
    expect(contrast("#ffffff", theme.kivu as string)).toBeGreaterThanOrEqual(4.5);
  });
});
