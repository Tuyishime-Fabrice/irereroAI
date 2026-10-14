/**
 * Imigongo zigzag hatching drawn at runtime: denser hatching means a wider estimate range.
 * Images are added to the map as patterns hatch-1 (some doubt) to hatch-3 (wide range).
 */
export const HATCH_LEVELS = [0.15, 0.2, 0.25] as const;

export function hatchLevel(uncertainty: number | null | undefined): number {
  if (uncertainty === null || uncertainty === undefined) return 0;
  return HATCH_LEVELS.filter((threshold) => uncertainty >= threshold).length;
}

export function hatchImage(level: number, size = 24): ImageData {
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("Canvas is not available");
  const rows = level + 1;
  const step = size / rows;
  // A light halo under a dark line keeps the zigzag visible on every step of the scale.
  for (const [colour, width] of [
    ["rgba(255, 253, 249, 0.55)", 2.4],
    ["rgba(30, 27, 24, 0.75)", 1.1],
  ] as const) {
    context.strokeStyle = colour;
    context.lineWidth = width;
    for (let row = 0; row < rows; row += 1) {
      const y = step * row + step / 2;
      context.beginPath();
      context.moveTo(0, y + 3);
      for (let x = 0; x <= size; x += 6) {
        context.lineTo(x + 3, y - 3);
        context.lineTo(x + 6, y + 3);
      }
      context.stroke();
    }
  }
  return context.getImageData(0, 0, size, size);
}
