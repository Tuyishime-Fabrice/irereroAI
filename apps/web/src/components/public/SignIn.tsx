"use client";

import { useTranslations } from "next-intl";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { homeFor } from "@/components/shell/roles";
import { useSession } from "@/components/shell/SessionProvider";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/Field";
import { Panel } from "@/components/ui/Panel";
import { api, type Me, type Schemas } from "@/lib/api/client";

type Mode = "staff" | "caregiver" | "parent";
const MODES: Mode[] = ["staff", "caregiver", "parent"];

async function post(path: string, body?: unknown): Promise<Me | null> {
  const response = await fetch(`/api/${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) return null;
  return ((await response.json()) as { user: Me }).user;
}

export function SignIn() {
  const t = useTranslations("signIn");
  const router = useRouter();
  const params = useSearchParams();
  const { setUser } = useSession();
  const initial = params.get("as");
  const [mode, setMode] = useState<Mode>(
    MODES.includes(initial as Mode) ? (initial as Mode) : "staff",
  );
  const [fields, setFields] = useState({
    email: "",
    password: "",
    totp: "",
    phone: "",
    centre: "",
    code: "",
  });
  const [codeSent, setCodeSent] = useState<string | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [demo, setDemo] = useState<Schemas["DemoConfig"] | null>(null);

  useEffect(() => {
    api.GET("/demo/config").then(({ data }) => data && setDemo(data));
  }, []);

  function done(user: Me | null) {
    setBusy(false);
    if (!user) {
      setError(t("failed"));
      return;
    }
    setUser(user);
    router.push(params.get("next") ?? homeFor(user.role));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    if (mode === "staff") {
      done(
        await post("auth/login", {
          email: fields.email,
          password: fields.password,
          totp_code: fields.totp || null,
        }),
      );
    } else if (mode === "caregiver") {
      done(await post("auth/caregiver", { phone: fields.phone, centre_code: fields.centre }));
    } else if (codeSent === undefined) {
      const { data } = await api.POST("/auth/otp/request", { body: { phone: fields.phone } });
      setBusy(false);
      if (!data) setError(t("badPhone"));
      else setCodeSent(data.demo_code ?? null);
    } else {
      done(await post("auth/otp/verify", { phone: fields.phone, code: fields.code }));
    }
  }

  const set = (key: keyof typeof fields) => (e: { target: { value: string } }) =>
    setFields({ ...fields, [key]: e.target.value });

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,480px)_1fr]">
      <Panel className="p-5">
        <div
          role="tablist"
          aria-label={t("who")}
          className="mb-5 grid grid-cols-3 gap-1 rounded-md bg-paper p-1"
        >
          {MODES.map((m) => (
            <button
              key={m}
              role="tab"
              type="button"
              aria-selected={mode === m}
              onClick={() => {
                setMode(m);
                setError(null);
                setCodeSent(undefined);
              }}
              className={`min-h-10 rounded-md text-sm font-medium ${mode === m ? "bg-surface text-ink shadow-[0_0_0_1px_var(--line)]" : "text-ink-muted"}`}
            >
              {t(`mode.${m}`)}
            </button>
          ))}
        </div>
        <form onSubmit={submit} className="flex flex-col gap-4">
          {mode === "staff" && (
            <>
              <TextField
                label={t("email")}
                type="email"
                autoComplete="username"
                required
                value={fields.email}
                onChange={set("email")}
              />
              <TextField
                label={t("password")}
                type="password"
                autoComplete="current-password"
                required
                value={fields.password}
                onChange={set("password")}
              />
              <TextField
                label={t("totp")}
                inputMode="numeric"
                autoComplete="one-time-code"
                value={fields.totp}
                onChange={set("totp")}
                hint={t("totpHint")}
              />
            </>
          )}
          {mode === "caregiver" && (
            <>
              <TextField
                label={t("phone")}
                type="tel"
                autoComplete="tel"
                required
                value={fields.phone}
                onChange={set("phone")}
                hint={t("phoneHint")}
              />
              <TextField
                label={t("centreCode")}
                required
                value={fields.centre}
                onChange={set("centre")}
                hint={t("centreHint")}
              />
            </>
          )}
          {mode === "parent" && (
            <>
              <TextField
                label={t("phone")}
                type="tel"
                autoComplete="tel"
                required
                value={fields.phone}
                onChange={set("phone")}
                hint={t("phoneHint")}
                disabled={codeSent !== undefined}
              />
              {codeSent !== undefined && (
                <>
                  {codeSent && (
                    <p
                      role="status"
                      className="rounded-md border border-clay bg-paper p-3 text-sm text-ink"
                    >
                      {t("demoCode")}{" "}
                      <span className="tabular text-lg font-semibold">{codeSent}</span>
                    </p>
                  )}
                  <TextField
                    label={t("code")}
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    required
                    value={fields.code}
                    onChange={set("code")}
                  />
                </>
              )}
              <p className="text-xs text-ink-muted">{t("parentPrivacy")}</p>
            </>
          )}
          {error && (
            <p role="alert" className="text-sm text-danger">
              {error}
            </p>
          )}
          <Button type="submit" variant="primary" size="lg" disabled={busy}>
            {mode === "parent" && codeSent === undefined ? t("sendCode") : t("submit")}
          </Button>
        </form>
      </Panel>

      {demo && (
        <Panel className="border-clay p-5">
          <h2 className="font-display text-xl text-ink">{t("demoTitle")}</h2>
          <p className="mt-1 text-sm text-ink-muted">{t("demoLead")}</p>
          <p className="mt-3 text-sm">
            {t("demoPassword")} <span className="tabular font-semibold">{demo.password}</span> ·{" "}
            {t("demoAdminCode")}{" "}
            <span className="tabular font-semibold">{demo.admin_totp_code}</span>
          </p>
          <ul className="mt-4 flex flex-col gap-2">
            {demo.accounts.map((account) => (
              <li
                key={account.role}
                className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-line bg-paper px-3 py-2"
              >
                <span className="text-sm">
                  <span className="font-medium text-ink">{t(`roles.${account.role}`)}</span>
                  <span className="block text-xs text-ink-muted">
                    {account.email ?? account.phone}
                    {account.centre_code ? ` · ${account.centre_code}` : ""}
                  </span>
                </span>
                <Button
                  onClick={async () => {
                    setBusy(true);
                    done(await post(`demo/login/${account.role}`));
                  }}
                  disabled={busy}
                >
                  {t("demoUse")}
                </Button>
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  );
}
