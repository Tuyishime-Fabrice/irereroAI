"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { useSession } from "@/components/shell/SessionProvider";
import { Button } from "@/components/ui/Button";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { EmptyState, LoadingState } from "@/components/ui/States";
import { api, type Schemas } from "@/lib/api/client";

/** A parent's saved searches and the self-service delete the privacy design promises. */
export function ParentAccount() {
  const t = useTranslations("account");
  const router = useRouter();
  const { user, loading, setUser } = useSession();
  const [searches, setSearches] = useState<Schemas["SavedSearchOut"][] | null>(null);
  const [confirming, setConfirming] = useState(false);

  const load = useCallback(() => {
    api.GET("/parent/searches").then(({ data }) => setSearches(data ?? []));
  }, []);
  useEffect(() => {
    if (user?.role === "parent") load();
  }, [user, load]);

  if (loading) return <LoadingState />;
  if (user?.role !== "parent") {
    return (
      <EmptyState title={t("signInFirst")}>
        <Link href="/sign-in?as=parent&next=/account" className="text-kivu underline">
          {t("signIn")}
        </Link>
      </EmptyState>
    );
  }
  return (
    <div className="grid max-w-3xl gap-6">
      <Panel>
        <PanelHeader title={t("searches")} />
        {searches === null ? (
          <LoadingState />
        ) : searches.length === 0 ? (
          <EmptyState title={t("noSearches")}>
            <Link href="/find" className="text-kivu underline">
              {t("goFind")}
            </Link>
          </EmptyState>
        ) : (
          <ul className="divide-y divide-line">
            {searches.map((s) => (
              <li key={s.id} className="flex items-center justify-between gap-3 px-4 py-3">
                <span className="text-ink">{s.label}</span>
                <Button
                  variant="danger"
                  onClick={async () => {
                    await api.DELETE("/parent/searches/{search_id}", {
                      params: { path: { search_id: s.id } },
                    });
                    load();
                  }}
                >
                  {t("delete")}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Panel>
      <Panel className="border-danger p-5">
        <h2 className="font-semibold text-ink">{t("deleteTitle")}</h2>
        <p className="mt-1 text-sm text-ink-muted">{t("deleteText")}</p>
        {confirming ? (
          <div className="mt-4 flex gap-2">
            <Button
              variant="danger"
              onClick={async () => {
                await api.DELETE("/parent/account");
                await fetch("/api/auth/logout", { method: "POST" });
                setUser(null);
                router.push("/");
              }}
            >
              {t("deleteConfirm")}
            </Button>
            <Button onClick={() => setConfirming(false)}>{t("cancel")}</Button>
          </div>
        ) : (
          <Button variant="danger" className="mt-4" onClick={() => setConfirming(true)}>
            {t("deleteAccount")}
          </Button>
        )}
      </Panel>
    </div>
  );
}
