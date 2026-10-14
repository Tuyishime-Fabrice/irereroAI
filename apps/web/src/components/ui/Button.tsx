import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger" | "ghost";

const STYLES: Record<Variant, string> = {
  primary: "bg-kivu text-white border-kivu hover:bg-[#164a50]",
  secondary: "bg-surface text-ink border-line-strong hover:bg-paper",
  danger: "bg-surface text-danger border-danger hover:bg-[#fbeeec]",
  ghost: "bg-transparent text-kivu border-transparent hover:bg-kivu-tint",
};

export function Button({
  variant = "secondary",
  size = "md",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "md" | "lg" }) {
  const sizing = size === "lg" ? "min-h-12 px-5 text-base" : "min-h-10 px-4 text-sm";
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center gap-2 rounded-md border font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${sizing} ${STYLES[variant]} ${className}`}
      {...props}
    />
  );
}
