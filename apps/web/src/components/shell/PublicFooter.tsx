import { getTranslations } from "next-intl/server";
import Link from "next/link";

import { LogoMark } from "@/components/brand/LogoMark";

export async function PublicFooter() {
  const t = await getTranslations("public.footer");
  return (
    <footer className="no-print mt-16 border-t border-line bg-surface">
      <div className="mx-auto grid max-w-6xl gap-6 px-4 py-8 text-sm text-ink-muted sm:grid-cols-[auto_1fr]">
        <LogoMark size={32} />
        <div className="flex flex-col gap-2">
          <p>{t("honesty")}</p>
          <p>{t("layer")}</p>
          <p>
            <Link href="/methodology" className="text-kivu underline">
              {t("methodology")}
            </Link>{" "}
            · {t("hackathon")}
          </p>
        </div>
      </div>
    </footer>
  );
}
