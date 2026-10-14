/** The single Imigongo spiral, used only in empty states. */
export function Spiral({ size = 56 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 56 56" aria-hidden>
      <path
        d="M28 28h6v-6H22v12h18V16H16v24h30V10H10v36h42"
        fill="none"
        stroke="var(--clay)"
        strokeWidth="2.5"
        strokeLinejoin="miter"
      />
    </svg>
  );
}
