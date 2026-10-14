"use client";

import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/Button";
import { SelectField, TextField } from "@/components/ui/Field";
import { PageTitle } from "@/components/ui/PageTitle";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { api, type Schemas } from "@/lib/api/client";
import { useApi } from "@/lib/useApi";

const ROLES: Schemas["Role"][] = [
  "caregiver",
  "sector_officer",
  "district_planner",
  "national_analyst",
  "admin",
];
const EMPTY = {
  role: "sector_officer" as Schemas["Role"],
  scope_code: "",
  display_name: "",
  email: "",
  phone: "",
  password: "",
};

/** Accounts with their role and scope. Every change is audited and ends the user's sessions. */
export function Users() {
  const t = useTranslations("admin");
  const roles = useTranslations("shell.role");
  const users = useApi("admin:users", async () => (await api.GET("/admin/users")).data ?? null);
  const [form, setForm] = useState(EMPTY);
  const [message, setMessage] = useState<string | null>(null);
  if (users.loading) return <LoadingState />;
  if (!users.data) return <ErrorState onRetry={users.reload} />;

  async function create(event: FormEvent) {
    event.preventDefault();
    const { data, error } = await api.POST("/admin/users", {
      body: {
        role: form.role,
        scope_code: form.scope_code || null,
        display_name: form.display_name,
        email: form.email || null,
        phone: form.phone || null,
        password: form.password || null,
      },
    });
    if (!data) {
      setMessage(
        typeof error === "object" && error && "detail" in error
          ? String(error.detail)
          : t("createFailed"),
      );
      return;
    }
    setMessage(data.totp_secret ? t("createdAdmin", { secret: data.totp_secret }) : t("created"));
    setForm(EMPTY);
    users.reload();
  }

  async function toggle(user: Schemas["UserOut"]) {
    await api.PATCH("/admin/users/{user_id}", {
      params: { path: { user_id: user.id } },
      body: { is_active: !user.is_active },
    });
    users.reload();
  }

  const set = (key: keyof typeof EMPTY) => (e: { target: { value: string } }) =>
    setForm({ ...form, [key]: e.target.value });
  return (
    <>
      <PageTitle title={t("usersTitle")} lead={t("usersLead")} />
      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <Panel className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-ink-muted">
              <tr>
                <th scope="col" className="px-4 py-2">
                  {t("name")}
                </th>
                <th scope="col" className="px-4 py-2">
                  {t("role")}
                </th>
                <th scope="col" className="px-4 py-2">
                  {t("scope")}
                </th>
                <th scope="col" className="px-4 py-2">
                  {t("login")}
                </th>
                <th scope="col" className="px-4 py-2">
                  {t("state")}
                </th>
              </tr>
            </thead>
            <tbody>
              {users.data.map((u) => (
                <tr key={u.id} className="border-t border-line">
                  <th scope="row" className="px-4 py-2 font-normal">
                    {u.display_name}
                  </th>
                  <td className="px-4 py-2">
                    {roles(u.role)}
                    {u.has_totp && (
                      <span className="ml-1 text-xs text-ink-muted">· {t("twoFactor")}</span>
                    )}
                  </td>
                  <td className="tabular px-4 py-2 text-xs">
                    {u.scope_code ?? t(`level.${u.scope_level}`)}
                  </td>
                  <td className="px-4 py-2 text-xs">{u.email ?? u.phone}</td>
                  <td className="px-4 py-2">
                    <Button
                      variant={u.is_active ? "secondary" : "primary"}
                      onClick={() => toggle(u)}
                    >
                      {u.is_active ? t("deactivate") : t("activate")}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
        <Panel className="self-start">
          <PanelHeader title={t("newUser")} />
          <form onSubmit={create} className="flex flex-col gap-3 p-4">
            <SelectField label={t("role")} value={form.role} onChange={set("role")}>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {roles(r)}
                </option>
              ))}
            </SelectField>
            <TextField
              label={t("scope")}
              value={form.scope_code}
              onChange={set("scope_code")}
              hint={t("scopeHint")}
            />
            <TextField
              label={t("name")}
              required
              value={form.display_name}
              onChange={set("display_name")}
            />
            <TextField label={t("email")} type="email" value={form.email} onChange={set("email")} />
            <TextField label={t("phone")} type="tel" value={form.phone} onChange={set("phone")} />
            <TextField
              label={t("password")}
              type="password"
              autoComplete="new-password"
              value={form.password}
              onChange={set("password")}
              hint={t("passwordHint")}
            />
            <Button type="submit" variant="primary">
              {t("create")}
            </Button>
            {message && (
              <p role="status" className="text-sm text-ink">
                {message}
              </p>
            )}
          </form>
        </Panel>
      </div>
    </>
  );
}
