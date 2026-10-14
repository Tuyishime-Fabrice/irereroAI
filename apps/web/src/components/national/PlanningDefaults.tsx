"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { WeightsControl } from "@/components/district/WeightsControl";
import { Button } from "@/components/ui/Button";
import { SelectField, TextField } from "@/components/ui/Field";
import { PageTitle } from "@/components/ui/PageTitle";
import { Panel } from "@/components/ui/Panel";
import { LoadingState } from "@/components/ui/States";
import { api, type Schemas } from "@/lib/api/client";
import { formatRwf } from "@/lib/format/numbers";
import { useApi } from "@/lib/useApi";

/** Default budgets and weights that planning screens open with. Changes are audited. */
export function PlanningDefaults() {
  const t = useTranslations("defaults");
  const [area, setArea] = useState("RW");
  const places = useApi("places", async () => (await api.GET("/public/places")).data ?? null);
  const loaded = useApi(
    `defaults:${area}`,
    async () =>
      (await api.GET("/planning-defaults/{area}", { params: { path: { area } } })).data ?? null,
  );
  const [draft, setDraft] = useState<{ area: string; value: Schemas["PlanningDefaults"] } | null>(
    null,
  );
  const [saved, setSaved] = useState(false);
  if (!loaded.data) return <LoadingState />;
  const value = draft?.area === area ? draft.value : { ...loaded.data, area_code: area };
  const set = (v: Schemas["PlanningDefaults"]) => {
    setDraft({ area, value: v });
    setSaved(false);
  };

  return (
    <>
      <PageTitle title={t("title")} lead={t("lead")} />
      <Panel className="flex max-w-xl flex-col gap-4 p-5">
        <SelectField label={t("area")} value={area} onChange={(e) => setArea(e.target.value)}>
          <option value="RW">{t("national")}</option>
          {places.data?.map((d) => (
            <option key={d.code} value={d.code}>
              {d.name}
            </option>
          ))}
        </SelectField>
        {loaded.data.area_code !== area && (
          <p className="text-xs text-ink-muted">{t("inherited")}</p>
        )}
        <TextField
          label={t("budget")}
          inputMode="numeric"
          value={String(value.budget_rwf)}
          hint={formatRwf(value.budget_rwf, true)}
          onChange={(e) =>
            set({ ...value, budget_rwf: Number(e.target.value.replace(/\D/g, "")) || 0 })
          }
        />
        <WeightsControl value={value.weights} onChange={(weights) => set({ ...value, weights })} />
        <Button
          variant="primary"
          disabled={value.budget_rwf <= 0}
          onClick={async () => {
            const { data } = await api.PUT("/planning-defaults/{area}", {
              params: { path: { area } },
              body: value,
            });
            setSaved(Boolean(data));
            loaded.reload();
          }}
        >
          {t("save")}
        </Button>
        {saved && (
          <p role="status" className="text-sm text-success">
            {t("saved")}
          </p>
        )}
      </Panel>
    </>
  );
}
