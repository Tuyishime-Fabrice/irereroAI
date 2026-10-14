"use client";

import type { FeatureCollection } from "geojson";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { PointMap } from "@/components/map/PointMap";
import { useProvenance } from "@/components/shell/ProvenanceProvider";
import { Button } from "@/components/ui/Button";
import { SelectField } from "@/components/ui/Field";
import { PinIcon } from "@/components/ui/icons";
import { Panel } from "@/components/ui/Panel";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { api, type Schemas } from "@/lib/api/client";
import { formatNumber } from "@/lib/format/numbers";

type Place = { lon: number; lat: number };
type AgeBand = "" | "0_2" | "3_6";
const DEFAULT_DISTRICT = "D-GICUMBI";

function freePlaces(count: Schemas["PublicCount"], t: (key: string) => string): string {
  if (count.suppressed) return t("fewPlaces");
  return formatNumber(count.value);
}

/** A parent picks a place, sees the nearest verified centres, and can ask for one closer. */
export function RequestCentre() {
  const t = useTranslations("request");
  const params = useSearchParams();
  // A link can open the page on a sector, e.g. /request?sector=S-GICUMBI-MIYOVE.
  const linkedSector = params.get("sector");
  const [districts, setDistricts] = useState<Schemas["District"][]>([]);
  const [district, setDistrict] = useState(
    linkedSector ? `D-${linkedSector.split("-")[1]}` : DEFAULT_DISTRICT,
  );
  const [sector, setSector] = useState(linkedSector ?? "");
  const [outlines, setOutlines] = useState<FeatureCollection | null>(null);
  const [place, setPlace] = useState<Place | null>(null);
  const [age, setAge] = useState<AgeBand>("");
  const [nearby, setNearby] = useState<{
    key: string;
    data: Schemas["Envelope_list_PublicCentre__"] | null;
  } | null>(null);
  const [requested, setRequested] = useState<{
    key: string;
    data: Schemas["DemandRecorded"];
  } | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [locating, setLocating] = useState(false);
  const placeKey = place ? `${place.lon},${place.lat}` : null;
  const queryKey = placeKey ? `${placeKey}:${attempt}` : null;
  const current = nearby && nearby.key === queryKey ? nearby : null;
  const status = !queryKey ? "idle" : !current ? "loading" : current.data ? "idle" : "error";
  useProvenance(current?.data?.provenance);

  useEffect(() => {
    api.GET("/public/places").then(({ data }) => {
      if (!data) return;
      setDistricts(data);
      const linked = data.flatMap((d) => d.sectors).find((s) => s.code === linkedSector);
      if (linked) setPlace({ lon: linked.lon, lat: linked.lat });
    });
  }, [linkedSector]);
  useEffect(() => {
    api
      .GET("/public/outlines", { params: { query: { district } } })
      .then(({ data }) => data && setOutlines(data as unknown as FeatureCollection));
  }, [district]);
  useEffect(() => {
    if (!place || !queryKey) return;
    let active = true;
    api
      .GET("/public/nearby", { params: { query: { lon: place.lon, lat: place.lat } } })
      .then(({ data }) => active && setNearby({ key: queryKey, data: data ?? null }))
      .catch(() => active && setNearby({ key: queryKey, data: null }));
    return () => {
      active = false;
    };
  }, [queryKey, place]);

  const sectors = useMemo(
    () => districts.find((d) => d.code === district)?.sectors ?? [],
    [districts, district],
  );
  const centres = current?.data?.data ?? [];

  async function request() {
    if (!place || !placeKey) return;
    const { data } = await api.POST("/public/demand", {
      body: { lon: place.lon, lat: place.lat, age_band: age || null },
    });
    if (data) setRequested({ key: placeKey, data });
  }

  function useMyLocation() {
    if (!navigator.geolocation) return;
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocating(false);
        setSector("");
        setPlace({ lon: position.coords.longitude, lat: position.coords.latitude });
      },
      () => setLocating(false),
      { maximumAge: 60_000, timeout: 10_000 },
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
      <Panel className="flex flex-col gap-3 self-start p-4">
        <h2 className="font-semibold text-ink">{t("where")}</h2>
        <SelectField
          label={t("district")}
          value={district}
          onChange={(e) => {
            setDistrict(e.target.value);
            setSector("");
            setPlace(null);
            setOutlines(null);
          }}
        >
          {districts.map((d) => (
            <option key={d.code} value={d.code}>
              {d.name}
            </option>
          ))}
        </SelectField>
        <SelectField
          label={t("sector")}
          value={sector}
          onChange={(e) => {
            setSector(e.target.value);
            const chosen = sectors.find((s) => s.code === e.target.value);
            setPlace(chosen ? { lon: chosen.lon, lat: chosen.lat } : null);
          }}
        >
          <option value="">{t("chooseSector")}</option>
          {sectors.map((s) => (
            <option key={s.code} value={s.code}>
              {s.name}
            </option>
          ))}
        </SelectField>
        <Button onClick={useMyLocation} disabled={locating}>
          <PinIcon /> {locating ? t("locating") : t("useLocation")}
        </Button>
        <p className="text-xs text-ink-muted">{t("mapHint")}</p>
      </Panel>

      <div className="flex flex-col gap-4">
        <PointMap
          outlines={outlines}
          points={centres.map((c) => ({ id: c.code, lon: c.lon, lat: c.lat, label: c.name }))}
          place={place}
          onPick={(lon, lat) => {
            setSector("");
            setPlace({ lon, lat });
          }}
        />
        <section aria-live="polite" aria-label={t("results")}>
          {!place && <EmptyState title={t("pickFirst")} />}
          {place && status === "loading" && <LoadingState />}
          {place && status === "error" && <ErrorState onRetry={() => setAttempt((n) => n + 1)} />}
          {place && status === "idle" && (
            <div className="flex flex-col gap-4">
              <Panel>
                <h2 className="border-b border-line px-4 py-3 text-sm font-semibold text-ink">
                  {t("nearestTitle")}
                </h2>
                {centres.length === 0 ? (
                  <EmptyState title={t("noneNearby")} />
                ) : (
                  <ul>
                    {centres.map((c) => (
                      <li
                        key={c.code}
                        className="flex flex-wrap items-baseline justify-between gap-2 border-t border-line px-4 py-3 first:border-t-0"
                      >
                        <span>
                          <span className="font-medium text-ink">{c.name}</span>
                          <span className="block text-xs text-ink-muted">
                            {c.sector_name} · {t(`type.${c.type}`)}
                          </span>
                        </span>
                        <span className="tabular text-sm text-ink">
                          {t("walk", { minutes: c.walking_minutes, km: c.distance_km })}
                          <span className="block text-xs text-ink-muted">
                            {t("free", { places: freePlaces(c.free_places, t) })}
                          </span>
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </Panel>
              <Panel className="flex flex-col gap-3 p-4">
                <h2 className="font-semibold text-ink">{t("askTitle")}</h2>
                <p className="text-sm text-ink-muted">{t("askLead")}</p>
                {requested?.key === placeKey ? (
                  <p role="status" className="font-medium text-success">
                    {t("requested", { sector: requested.data.sector_name })}
                  </p>
                ) : (
                  <div className="flex flex-wrap items-end gap-3">
                    <SelectField
                      label={t("age")}
                      value={age}
                      onChange={(e) => setAge(e.target.value as AgeBand)}
                    >
                      <option value="">{t("anyAge")}</option>
                      <option value="0_2">{t("ages.young")}</option>
                      <option value="3_6">{t("ages.old")}</option>
                    </SelectField>
                    <Button
                      data-tour="request-centre"
                      variant="primary"
                      size="lg"
                      onClick={request}
                    >
                      {t("request")}
                    </Button>
                  </div>
                )}
                <p className="text-xs text-ink-muted">{t("privacy")}</p>
              </Panel>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
