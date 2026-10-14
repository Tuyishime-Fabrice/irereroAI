import { getTranslations } from "next-intl/server";
import { Suspense } from "react";

import { FindCentres } from "@/components/public/FindCentres";
import { PageTitle } from "@/components/ui/PageTitle";

export async function generateMetadata() {
  const t = await getTranslations("find");
  return { title: t("title") };
}

export default async function FindPage() {
  const t = await getTranslations("find");
  return (
    <>
      <PageTitle title={t("title")} lead={t("lead")} />
      <Suspense>
        <FindCentres />
      </Suspense>
    </>
  );
}
