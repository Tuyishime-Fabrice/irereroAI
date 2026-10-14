"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { api, type Schemas } from "@/lib/api/client";

import { useSession } from "./SessionProvider";
import { useWorkspace } from "./Workspace";

/** National, district or sector view, limited to what the signed-in scope allows. */
export function ScopeSwitcher() {
  const t = useTranslations("shell");
  const { user } = useSession();
  const { area, setArea } = useWorkspace();
  const [districts, setDistricts] = useState<Schemas["District"][]>([]);

  useEffect(() => {
    api.GET("/public/places").then(({ data }) => data && setDistricts(data));
  }, []);
  if (
    !user ||
    user.scope_level === "sector" ||
    user.scope_level === "centre" ||
    user.scope_level === "none"
  ) {
    return null;
  }
  const options: { code: string; label: string }[] = [];
  if (user.scope_level === "national") {
    options.push({ code: "RW", label: t("national") });
    for (const d of districts) options.push({ code: d.code, label: d.name });
  } else {
    const own = districts.find((d) => d.code === user.scope_code);
    if (own) {
      options.push({ code: own.code, label: own.name });
      for (const s of own.sectors) options.push({ code: s.code, label: `· ${s.name}` });
    }
  }
  return (
    <label className="flex items-center gap-2 text-xs text-ink-muted">
      {t("scope")}
      <select
        value={area ?? user.scope_code ?? "RW"}
        onChange={(e) => setArea(e.target.value)}
        className="min-h-8 max-w-44 rounded-md border border-line-strong bg-surface px-2 text-sm text-ink"
      >
        {options.map((o) => (
          <option key={o.code} value={o.code}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
