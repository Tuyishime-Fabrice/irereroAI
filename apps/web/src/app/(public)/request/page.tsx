import { getTranslations } from "next-intl/server";
import { Suspense } from "react";

import { RequestCentre } from "@/components/public/RequestCentre";
import { PageTitle } from "@/components/ui/PageTitle";

export async function generateMetadata() {
  const t = await getTranslations("request");
  return { title: t("title") };
}

export default async function RequestPage() {
  const t = await getTranslations("request");
  return (
    <>
      <PageTitle title={t("title")} lead={t("lead")} />
      <Suspense>
        <RequestCentre />
      </Suspense>
    </>
  );
}
