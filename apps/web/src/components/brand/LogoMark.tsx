/** Nested Imigongo diamonds. Legible down to 16 px; the favicon uses the same geometry. */
export function LogoMark({ size = 28, title }: { size?: number; title?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
      aria-label={title}
    >
      <path d="M16 1 31 16 16 31 1 16Z" fill="var(--ink)" />
      <path d="M16 7 25 16 16 25 7 16Z" fill="var(--clay)" />
      <path d="M16 12 20 16 16 20 12 16Z" fill="var(--paper)" />
    </svg>
  );
}
