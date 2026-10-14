import { LogoMark } from "./LogoMark";

export function Logo({ size = 28 }: { size?: number }) {
  return (
    <span className="inline-flex items-center gap-2" aria-label="IrereroAI">
      <LogoMark size={size} />
      <span aria-hidden className="font-display text-[22px] leading-none font-semibold text-ink">
        Irerero
        <span className="ml-0.5 font-mono text-[13px] font-medium tracking-wider text-clay uppercase">
          ai
        </span>
      </span>
    </span>
  );
}
