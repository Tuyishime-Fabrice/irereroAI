"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { AssistantDrawer, type AssistantSubject } from "@/components/assistant/AssistantDrawer";
import { useProvenance } from "@/components/shell/ProvenanceProvider";
import { DecisionCard } from "@/components/signature/DecisionCard";
import { PageTitle } from "@/components/ui/PageTitle";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { api, type Schemas } from "@/lib/api/client";
import { useApi } from "@/lib/useApi";

import { useSectorCode } from "./useSector";

/** Suggestions from the latest district plan that fall in the officer's sector. */
export function LocalSuggestions() {
  const t = useTranslations("sector");
  const sector = useSectorCode();
  const loaded = useApi(sector && `local:${sector}`, async () => {
    if (!sector) return null;
    const { data, response } = await api.GET("/local-suggestions", {
      params: { query: { sector } },
    });
    return response.ok ? { envelope: data ?? null } : null;
  });
  const [override, setOverride] = useState<Schemas["Envelope_ScenarioOut_"] | null>(null);
  const [asking, setAsking] = useState<AssistantSubject | null>(null);
  const envelope = override ?? loaded.data?.envelope ?? null;
  useProvenance(envelope?.provenance);
  if (loaded.loading && !envelope) return <LoadingState />;
  if (loaded.error) return <ErrorState onRetry={loaded.reload} />;
  const recs = envelope
    ? [...envelope.data.recommendations, ...envelope.data.rejected].filter(
        (r) => r.sector_code === sector,
      )
    : [];

  return (
    <>
      <PageTitle title={t("suggestionsTitle")} lead={t("suggestionsLead")} />
      {!envelope || recs.length === 0 ? (
        <EmptyState title={t("noSuggestions")} />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {recs.map((rec) => (
            <DecisionCard
              key={rec.id}
              recommendation={rec}
              maxReached={100}
              canDecide={rec.action === "support"}
              onAsk={() => setAsking({ kind: "recommendation", id: rec.id, title: rec.site_name })}
              onDecide={async (decision) => {
                const { data } = await api.POST("/recommendations/{recommendation_id}/decision", {
                  params: { path: { recommendation_id: rec.id } },
                  body: decision,
                });
                if (!data) throw new Error("not saved");
                setOverride(data);
              }}
            />
          ))}
        </div>
      )}
      <p className="mt-4 text-sm text-ink-muted">{t("suggestionsNote")}</p>
      <AssistantDrawer subject={asking} onClose={() => setAsking(null)} />
    </>
  );
}
