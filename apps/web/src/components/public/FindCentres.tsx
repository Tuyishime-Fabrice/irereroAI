"use client";

import type { FeatureCollection } from "geojson";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { PointMap } from "@/components/map/PointMap";
import { useProvenance } from "@/components/shell/ProvenanceProvider";
import { useSession } from "@/components/shell/SessionProvider";
import { Button } from "@/components/ui/Button";
import { SelectField } from "@/components/ui/Field";
import { PinIcon } from "@/components/ui/icons";
import { Panel } from "@/components/ui/Panel";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { api, type Schemas } from "@/lib/api/client";

import { CentreSummary } from "./CentreSummary";

type Place = { lon: number; lat: number };
type Filters = {
  age: "" | "0_2" | "3_6";
  meals: boolean;
  fee: "" | Schemas["FeeBand"];
  radius: number;
};
const DEFAULT_DISTRICT = "D-GICUMBI";
const FEES: Schemas["FeeBand"][] = ["free", "under_1000", "from_1000_to_5000", "over_5000"];

export function FindCentres() {
  const t = useTranslations("find");
  const { user } = useSession();
  const [districts, setDistricts] = useState<Schemas["District"][]>([]);
  const [district, setDistrict] = useState(DEFAULT_DISTRICT);
  const [sector, setSector] = useState("");
  const [outlines, setOutlines] = useState<FeatureCollection | null>(null);
  const [place, setPlace] = useState<Place | null>(null);
  const [filters, setFilters] = useState<Filters>({ age: "", meals: false, fee: "", radius: 5 });
  const [response, setResponse] = useState<{
    key: string;
    data: Schemas["Envelope_FindResult_"] | null;
  } | null>(null);
  const [requested, setRequested] = useState<{
    key: string;
    data: Schemas["DemandRecorded"];
  } | null>(null);
  const [savedKey, setSavedKey] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [locating, setLocating] = useState(false);
  const queryKey = place ? JSON.stringify({ place, filters, attempt }) : null;
  const current = response && response.key === queryKey ? response : null;
  const result = current?.data ?? null;
  const status = !queryKey ? "idle" : !current ? "loading" : current.data ? "idle" : "error";
  useProvenance(result?.provenance);

  useEffect(() => {
    api.GET("/public/places").then(({ data }) => data && setDistricts(data));
  }, []);
  useEffect(() => {
    api
      .GET("/public/outlines", { params: { query: { district } } })
      .then(({ data }) => data && setOutlines(data as unknown as FeatureCollection));
  }, [district]);

  useEffect(() => {
    if (!place || !queryKey) return;
    let active = true;
    api
      .GET("/public/centres", {
        params: {
          query: {
            lon: place.lon,
            lat: place.lat,
            radius_km: filters.radius,
            age_band: filters.age || undefined,
            meals: filters.meals,
            max_fee: filters.fee || undefined,
          },
        },
      })
      .then(({ data }) => active && setResponse({ key: queryKey, data: data ?? null }))
      .catch(() => active && setResponse({ key: queryKey, data: null }));
    return () => {
      active = false;
    };
  }, [queryKey, place, filters]);

  const sectors = useMemo(
    () => districts.find((d) => d.code === district)?.sectors ?? [],
    [districts, district],
  );
  const centres = result?.data.centres ?? [];

  async function requestCentre() {
    if (!place) return;
    const { data } = await api.POST("/public/demand", {
      body: { lon: place.lon, lat: place.lat, age_band: filters.age || null },
    });
    if (data && queryKey) setRequested({ key: queryKey, data });
  }

  async function saveSearch() {
    if (!place) return;
    const label = sectors.find((s) => s.code === sector)?.name ?? t("myPlace");
    const { response: saved } = await api.POST("/parent/searches", {
      body: { label, lon: place.lon, lat: place.lat, filters: { ...filters } },
    });
    if (saved.ok) setSavedKey(queryKey);
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
    <div className="grid gap-6 lg:grid-cols-[360px_1fr] lg:grid-rows-[auto_1fr]">
      <Panel className="flex flex-col gap-3 self-start p-4 lg:col-start-1 lg:row-start-1">
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

      <Panel className="order-3 flex flex-col gap-3 self-start p-4 lg:order-none lg:col-start-1 lg:row-start-2">
        <h2 className="font-semibold text-ink">{t("filters")}</h2>
        <SelectField
          label={t("age")}
          value={filters.age}
          onChange={(e) => setFilters({ ...filters, age: e.target.value as Filters["age"] })}
        >
          <option value="">{t("anyAge")}</option>
          <option value="0_2">{t("ages.young")}</option>
          <option value="3_6">{t("ages.old")}</option>
        </SelectField>
        <SelectField
          label={t("maxFee")}
          value={filters.fee}
          onChange={(e) => setFilters({ ...filters, fee: e.target.value as Filters["fee"] })}
        >
          <option value="">{t("anyFee")}</option>
          {FEES.map((fee) => (
            <option key={fee} value={fee}>
              {t(`fee.${fee}`)}
            </option>
          ))}
        </SelectField>
        <SelectField
          label={t("distance")}
          value={filters.radius}
          onChange={(e) => setFilters({ ...filters, radius: Number(e.target.value) })}
        >
          {[2, 5, 10].map((km) => (
            <option key={km} value={km}>
              {t("withinKm", { km })}
            </option>
          ))}
        </SelectField>
        <label className="flex min-h-10 items-center gap-2 text-sm text-ink">
          <input
            type="checkbox"
            checked={filters.meals}
            onChange={(e) => setFilters({ ...filters, meals: e.target.checked })}
            className="h-5 w-5 accent-[var(--kivu)]"
          />
          {t("mealsOnly")}
        </label>
      </Panel>

      <div className="flex flex-col gap-4 lg:col-start-2 lg:row-span-2 lg:row-start-1">
        <PointMap
          outlines={outlines}
          points={centres.map((c) => ({ id: c.code, lon: c.lon, lat: c.lat, label: c.name }))}
          place={place}
          onPick={(lon, lat) => {
            setSector("");
            setPlace({ lon, lat });
          }}
          onSelect={(code) =>
            document
              .getElementById(`centre-${code}`)
              ?.scrollIntoView({ behavior: "smooth", block: "center" })
          }
        />
        <section aria-live="polite" aria-label={t("results")}>
          {!place && <EmptyState title={t("pickFirst")} />}
          {place && status === "loading" && <LoadingState />}
          {place && status === "error" && <ErrorState onRetry={() => setAttempt((n) => n + 1)} />}
          {place && status === "idle" && result && centres.length > 0 && (
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="font-semibold text-ink">{t("found", { count: centres.length })}</h2>
                {user?.role === "parent" ? (
                  <Button variant="ghost" onClick={saveSearch} disabled={savedKey === queryKey}>
                    {savedKey === queryKey ? t("saved") : t("save")}
                  </Button>
                ) : (
                  <Link href="/sign-in?as=parent" className="text-sm text-kivu underline">
                    {t("signInToSave")}
                  </Link>
                )}
              </div>
              {centres.map((centre) => (
                <div key={centre.code} id={`centre-${centre.code}`}>
                  <CentreSummary centre={centre} />
                </div>
              ))}
            </div>
          )}
          {place && status === "idle" && result && centres.length === 0 && (
            <Panel>
              <EmptyState title={t("noneTitle")}>
                <p>{t("noneText")}</p>
                {result.data.demand_recorded && <p className="mt-2">{t("counted")}</p>}
                <div className="mt-4">
                  {requested?.key === queryKey ? (
                    <p role="status" className="font-medium text-success">
                      {t("requested", { sector: requested.data.sector_name })}
                    </p>
                  ) : (
                    <Button variant="primary" size="lg" onClick={requestCentre}>
                      {t("request")}
                    </Button>
                  )}
                </div>
                <p className="mt-3 text-xs">{t("privacy")}</p>
              </EmptyState>
            </Panel>
          )}
        </section>
      </div>
    </div>
  );
}
