import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";

const CONTROL =
  "w-full rounded-md border border-line-strong bg-surface px-3 py-2 text-ink placeholder:text-ink-muted";

export function TextField({
  label,
  hint,
  error,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & {
  label: ReactNode;
  hint?: ReactNode;
  error?: ReactNode;
}) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium text-ink">
        {label}
      </label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={hint || error ? `${id}-note` : undefined}
        className={`${CONTROL} ${error ? "border-danger" : ""}`}
        {...props}
      />
      {(hint || error) && (
        <p id={`${id}-note`} className={`text-sm ${error ? "text-danger" : "text-ink-muted"}`}>
          {error ?? hint}
        </p>
      )}
    </div>
  );
}

export function SelectField({
  label,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & { label: ReactNode }) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium text-ink">
        {label}
      </label>
      <select id={id} className={CONTROL} {...props}>
        {children}
      </select>
    </div>
  );
}
