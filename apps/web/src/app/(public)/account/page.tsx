import { getTranslations } from "next-intl/server";

import { ParentAccount } from "@/components/public/ParentAccount";
import { PageTitle } from "@/components/ui/PageTitle";

export default async function AccountPage() {
  const t = await getTranslations("account");
  return (
    <>
      <PageTitle title={t("title")} lead={t("lead")} />
      <ParentAccount />
    </>
  );
}
