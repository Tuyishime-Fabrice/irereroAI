/** The 6 px Imigongo band: top of the app shell and above page titles only. */
export function ZigzagBand({ className = "" }: { className?: string }) {
  return <div aria-hidden className={`zigzag-band w-full ${className}`} />;
}
