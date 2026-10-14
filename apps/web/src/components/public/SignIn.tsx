"use client";

import { useTranslations } from "next-intl";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { HOME } from "@/components/shell/nav";
import { useSession } from "@/components/shell/SessionProvider";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/Field";
import { Panel } from "@/components/ui/Panel";
import { api, type Me, type Schemas } from "@/lib/api/client";

async function post(path: string, body?: unknown): Promise<Me | null> {
  const response = await fetch(`/api/${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) return null;
  return ((await response.json()) as { user: Me }).user;
}

/** Sign-in for district planners. Parents never need an account. */
export function SignIn() {
  const t = useTranslations("signIn");
  const router = useRouter();
  const params = useSearchParams();
  const { setUser } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [demo, setDemo] = useState<Schemas["DemoAccount"] | null>(null);

  useEffect(() => {
    api.GET("/demo/account").then(({ data }) => data && setDemo(data));
  }, []);

  function done(user: Me | null) {
    setBusy(false);
    if (!user) {
      setError(t("failed"));
      return;
    }
    setUser(user);
    router.push(params.get("next") ?? HOME);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    done(await post("auth/login", { email, password }));
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,480px)_1fr]">
      <Panel className="p-5">
        <form onSubmit={submit} className="flex flex-col gap-4">
          <TextField
            label={t("email")}
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <TextField
            label={t("password")}
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && (
            <p role="alert" className="text-sm text-danger">
              {error}
            </p>
          )}
          <Button type="submit" variant="primary" size="lg" disabled={busy}>
            {t("submit")}
          </Button>
          <p className="text-xs text-ink-muted">{t("parentsNote")}</p>
        </form>
      </Panel>

      {demo && (
        <Panel className="border-clay p-5">
          <h2 className="font-display text-xl text-ink">{t("demoTitle")}</h2>
          <p className="mt-1 text-sm text-ink-muted">{t("demoLead")}</p>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-md border border-line bg-paper px-3 py-2">
            <span className="text-sm">
              <span className="font-medium text-ink">{demo.display_name}</span>
              <span className="block text-xs text-ink-muted">
                {demo.email} · {t("demoPassword")}{" "}
                <span className="tabular font-semibold">{demo.password}</span>
              </span>
            </span>
            <Button
              onClick={async () => {
                setBusy(true);
                done(await post("demo/login"));
              }}
              disabled={busy}
            >
              {t("demoUse")}
            </Button>
          </div>
        </Panel>
      )}
    </div>
  );
}
