"use client";

import type { Provenance } from "@/lib/api/client";

import { useProvenance } from "./ProvenanceProvider";

/** Lets a server component report the provenance of the data it rendered. */
export function RegisterProvenance({ provenance }: { provenance: Provenance }) {
  useProvenance(provenance);
  return null;
}
