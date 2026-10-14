import { getTranslations } from "next-intl/server";

import { SourceChip } from "@/components/signature/SourceChip";
import { Panel } from "@/components/ui/Panel";

/** Published figures quoted from the team's brief, with their sources. Not computed here. */
const NUMBERS = [
  { key: "enrolment", value: "35% → 65%", source: "NST2 (2024–2029)", year: 2024 },
  { key: "stunting", value: "< 15%", source: "NST2 (2024–2029)", year: 2024 },
  { key: "gicumbi", value: "38.8%", source: "Rwanda DHS 2025", year: 2025 },
] as const;

export async function HeadlineNumbers() {
  const t = await getTranslations("landing.numbers");
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {NUMBERS.map((n) => (
        <Panel key={n.key} className="flex flex-col gap-2 p-5">
          <p className="font-display text-4xl text-clay">{n.value}</p>
          <p className="text-ink">{t(`${n.key}.text`)}</p>
          <div className="mt-auto pt-2">
            <SourceChip
              source={{
                table: "published_report",
                source: n.source,
                reference_year: n.year,
                origin: "official",
              }}
            />
          </div>
        </Panel>
      ))}
    </div>
  );
}
