import type { SVGProps } from "react";

/** A small fixed set of line icons. Decorative unless given a title by the caller. */
function Icon({ children, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg
      width={18}
      height={18}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      {...props}
    >
      {children}
    </svg>
  );
}

export const BuildIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M3 11 12 4l9 7M5 10v10h14V10M10 20v-6h4v6" />
  </Icon>
);
export const UpgradeIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M12 19V5M6 11l6-6 6 6M5 21h14" />
  </Icon>
);
export const SupportIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M12 21s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 11c0 5.6-7 10-7 10Z" />
  </Icon>
);
export const AlertIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M12 3 2 20h20L12 3ZM12 10v4M12 17h.01" />
  </Icon>
);
export const CheckIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="m5 12 5 5 9-10" />
  </Icon>
);
export const CloseIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M6 6l12 12M18 6 6 18" />
  </Icon>
);
export const EditIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M4 20h4L19 9l-4-4L4 16v4ZM13 7l4 4" />
  </Icon>
);
export const InfoIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 11v6M12 7.5h.01" />
  </Icon>
);
export const PlayIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M7 5v14l12-7L7 5Z" />
  </Icon>
);
export const PauseIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M8 5v14M16 5v14" />
  </Icon>
);
export const PinIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M12 21s7-6 7-12a7 7 0 1 0-14 0c0 6 7 12 7 12Z" />
    <circle cx="12" cy="9" r="2.5" />
  </Icon>
);
export const QuestionIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14M12 17h.01" />
  </Icon>
);
export const CloudOffIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M3 3l18 18M8 18h9a4 4 0 0 0 1.6-7.7A6 6 0 0 0 9 7.6M5.5 10.2A4 4 0 0 0 7 18" />
  </Icon>
);
