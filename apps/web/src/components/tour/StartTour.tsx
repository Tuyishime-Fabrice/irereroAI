"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";

import { TOUR } from "./steps";
import { writeStep } from "./tourStore";

export function StartTour() {
  const t = useTranslations("tour");
  const router = useRouter();
  return (
    <Button
      variant="primary"
      size="lg"
      onClick={() => {
        writeStep(0);
        router.push(TOUR[0]?.path ?? "/");
      }}
    >
      {t("start")}
    </Button>
  );
}
