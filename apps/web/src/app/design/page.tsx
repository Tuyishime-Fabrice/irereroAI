import { notFound } from "next/navigation";

import { DesignGallery } from "./DesignGallery";

export const metadata = { title: "Design system" };

export default function DesignPage() {
  if (process.env.NODE_ENV === "production" && process.env.NEXT_PUBLIC_DESIGN_PAGE !== "true") {
    notFound();
  }
  return <DesignGallery />;
}
