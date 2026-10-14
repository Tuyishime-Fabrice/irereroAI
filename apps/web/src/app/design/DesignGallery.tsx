"use client";

import { useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { Logo } from "@/components/brand/Logo";
import { LogoMark } from "@/components/brand/LogoMark";
import { ZigzagBand } from "@/components/brand/ZigzagBand";
import { HatchedChoropleth } from "@/components/map/HatchedChoropleth";
import { LocaleToggle } from "@/components/shell/LocaleToggle";
import { ThemeToggle } from "@/components/shell/ThemeToggle";
import { AlertRow } from "@/components/signature/AlertRow";
import { DecisionCard } from "@/components/signature/DecisionCard";
import { DriverBars } from "@/components/signature/DriverBars";
import { ImpactCounter } from "@/components/signature/ImpactCounter";
import { RangeBar } from "@/components/signature/RangeBar";
import { ReliabilityMeter } from "@/components/signature/ReliabilityMeter";
import { SimulatedWatermark } from "@/components/signature/SimulatedWatermark";
import { SmsPreview } from "@/components/signature/SmsPreview";
import { SourceChip } from "@/components/signature/SourceChip";
import { TrendChart } from "@/components/signature/TrendChart";
import { WeekScrubber } from "@/components/signature/WeekScrubber";
import { Button } from "@/components/ui/Button";
import { PageTitle } from "@/components/ui/PageTitle";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { EmptyState } from "@/components/ui/States";
import { formatNumber } from "@/lib/format/numbers";

import {
  SAMPLE_ALERT,
  SAMPLE_AREAS,
  SAMPLE_DRIVERS,
  SAMPLE_OUTCOMES,
  SAMPLE_RECOMMENDATION,
  SAMPLE_SOURCE,
  SAMPLE_WEEKS,
} from "./samples";

const TOKENS = [
  "paper",
  "surface",
  "ink",
  "ink-muted",
  "line",
  "line-strong",
  "clay",
  "ochre",
  "ochre-text",
  "kivu",
  "success",
  "danger",
  "need-1",
  "need-2",
  "need-3",
  "need-4",
  "need-5",
];

function Specimen({ name, children }: { name: string; children: ReactNode }) {
  return (
    <Panel>
      <PanelHeader title={<span className="font-mono">{name}</span>} />
      <div className="p-4">{children}</div>
    </Panel>
  );
}

export function DesignGallery() {
  const t = useTranslations("design");
  const [week, setWeek] = useState(SAMPLE_WEEKS[11] as string);
  return (
    <div>
      <ZigzagBand />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <Logo />
          <div className="flex gap-2">
            <ThemeToggle />
            <LocaleToggle />
          </div>
        </div>
        <PageTitle title={t("title")} lead={t("lead")} />
        <p className="mb-6 text-sm text-ink-muted">{t("sample")}</p>

        <h2 className="mb-3 font-display text-xl">{t("colours")}</h2>
        <div className="mb-8 grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-6">
          {TOKENS.map((token) => (
            <div key={token} className="rounded-md border border-line bg-surface p-2 text-xs">
              <div
                className="mb-2 h-10 rounded-sm border border-line"
                style={{ background: `var(--${token})` }}
              />
              <span className="font-mono">--{token}</span>
            </div>
          ))}
        </div>

        <h2 className="mb-3 font-display text-xl">{t("type")}</h2>
        <div className="mb-8 flex flex-col gap-2 rounded-md border border-line bg-surface p-4">
          <p className="font-display text-4xl">Fraunces 38.8%</p>
          <p>IBM Plex Sans — sentence case for every label and heading.</p>
          <p className="tabular">IBM Plex Mono 1,234 (1,100–1,400)</p>
          <div className="flex items-center gap-4">
            <LogoMark size={16} /> <LogoMark size={32} /> <Logo size={36} />
          </div>
          <div className="flex flex-wrap gap-2 pt-2">
            <Button variant="primary">Primary</Button>
            <Button>Secondary</Button>
            <Button variant="danger">Reject</Button>
            <Button variant="ghost">Ghost</Button>
          </div>
        </div>

        <h2 className="mb-3 font-display text-xl">{t("components")}</h2>
        <div className="grid gap-4 lg:grid-cols-2">
          <Specimen name="DecisionCard">
            <DecisionCard
              recommendation={SAMPLE_RECOMMENDATION}
              maxReached={100}
              canDecide
              onDecide={async () => undefined}
              onAsk={() => undefined}
            />
          </Specimen>
          <div className="flex flex-col gap-4">
            <Specimen name="DriverBars">
              <DriverBars drivers={SAMPLE_DRIVERS} />
            </Specimen>
            <Specimen name="RangeBar">
              <RangeBar value={{ estimate: 1234, low: 1100, high: 1400 }} max={2000} />
            </Specimen>
            <Specimen name="SourceChip">
              <SourceChip source={SAMPLE_SOURCE} />
            </Specimen>
            <Specimen name="ReliabilityMeter">
              <div className="flex flex-col gap-2">
                <ReliabilityMeter score={0.92} />
                <ReliabilityMeter score={0.67} />
                <ReliabilityMeter score={0.42} />
              </div>
            </Specimen>
            <Specimen name="SimulatedWatermark">
              <div className="flex flex-col items-start gap-3">
                <SimulatedWatermark force />
                <SimulatedWatermark force variant="inline" />
                <div className="w-full">
                  <SimulatedWatermark force variant="stamp" />
                </div>
              </div>
            </Specimen>
          </div>
          <Specimen name="ImpactCounter">
            <ImpactCounter outcomes={SAMPLE_OUTCOMES} />
          </Specimen>
          <Specimen name="AlertRow">
            <AlertRow alert={SAMPLE_ALERT} action={<Button>Open</Button>} />
          </Specimen>
          <Specimen name="WeekScrubber">
            <WeekScrubber weeks={SAMPLE_WEEKS} value={week} onChange={setWeek} />
          </Specimen>
          <Specimen name="SmsPreview">
            <SmsPreview
              message="IR ECD-GIC-001 39 6 5 12 13 30 2 2 5 5 Y 1 1 0"
              reply="Murakoze. Raporo yakiriwe."
            />
          </Specimen>
          <Specimen name="TrendChart">
            <TrendChart
              title="Sample trend"
              data={SAMPLE_WEEKS.map((w, i) => ({
                label: `W${i + 1}`,
                enrolled: 40 + (i % 3),
                attendance: 34 - (i > 8 ? 12 : 0),
              }))}
              series={[
                { key: "enrolled", label: "Enrolled", colour: "var(--ink)" },
                { key: "attendance", label: "Attendance", colour: "var(--kivu)" },
              ]}
            />
          </Specimen>
          <Specimen name="Empty state">
            <EmptyState title="Nothing here yet" />
          </Specimen>
        </div>
        <div className="mt-4">
          <Specimen name="HatchedChoropleth">
            <HatchedChoropleth
              areas={SAMPLE_AREAS}
              title="Sample measure"
              format={formatNumber}
              height={320}
            />
          </Specimen>
        </div>
      </main>
    </div>
  );
}
