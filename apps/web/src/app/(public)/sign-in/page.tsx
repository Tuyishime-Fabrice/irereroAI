import { getTranslations } from "next-intl/server";
import { Suspense } from "react";

import { SignIn } from "@/components/public/SignIn";
import { PageTitle } from "@/components/ui/PageTitle";

export async function generateMetadata() {
  const t = await getTranslations("signIn");
  return { title: t("title") };
}

export default async function SignInPage() {
  const t = await getTranslations("signIn");
  return (
    <>
      <PageTitle title={t("title")} lead={t("lead")} />
      <Suspense>
        <SignIn />
      </Suspense>
    </>
  );
}
