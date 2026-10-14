"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { SelectField } from "@/components/ui/Field";
import { PageTitle } from "@/components/ui/PageTitle";
import { Panel } from "@/components/ui/Panel";
import { EmptyState, LoadingState } from "@/components/ui/States";
import { api, type Schemas } from "@/lib/api/client";
import { useApi } from "@/lib/useApi";

const ACTIONS = ["", "recommendation", "scenario", "alert", "centre", "user", "planning_defaults"];
const ROLES: ("" | Schemas["Role"])[] = [
  "",
  "sector_officer",
  "district_planner",
  "national_analyst",
  "admin",
];

/** The append-only audit log, filtered by action and role. Nothing here can be edited. */
export function AuditLog() {
  const t = useTranslations("admin");
  const roles = useTranslations("shell.role");
  const [action, setAction] = useState("");
  const [role, setRole] = useState<"" | Schemas["Role"]>("");
  const log = useApi(
    `audit:${action}:${role}`,
    async () =>
      (
        await api.GET("/admin/audit", {
          params: { query: { action: action || undefined, actor_role: role || undefined } },
        })
      ).data ?? null,
  );
  return (
    <>
      <PageTitle title={t("auditTitle")} lead={t("auditLead")} />
      <div className="mb-4 grid max-w-xl gap-3 sm:grid-cols-2">
        <SelectField label={t("action")} value={action} onChange={(e) => setAction(e.target.value)}>
          {ACTIONS.map((a) => (
            <option key={a} value={a}>
              {a ? t(`actions.${a}`) : t("all")}
            </option>
          ))}
        </SelectField>
        <SelectField
          label={t("role")}
          value={role}
          onChange={(e) => setRole(e.target.value as typeof role)}
        >
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {r ? roles(r) : t("all")}
            </option>
          ))}
        </SelectField>
      </div>
      <Panel className="overflow-x-auto">
        {log.loading ? (
          <LoadingState />
        ) : !log.data?.length ? (
          <EmptyState title={t("noEntries")} />
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-ink-muted">
              <tr>
                <th scope="col" className="px-4 py-2">
                  {t("when")}
                </th>
                <th scope="col" className="px-4 py-2">
                  {t("who")}
                </th>
                <th scope="col" className="px-4 py-2">
                  {t("action")}
                </th>
                <th scope="col" className="px-4 py-2">
                  {t("change")}
                </th>
                <th scope="col" className="px-4 py-2">
                  {t("reason")}
                </th>
              </tr>
            </thead>
            <tbody>
              {log.data.map((entry) => (
                <tr key={entry.id} className="border-t border-line align-top">
                  <td className="tabular px-4 py-2 text-xs">
                    {entry.created_at.slice(0, 19).replace("T", " ")}
                  </td>
                  <td className="px-4 py-2">
                    {entry.actor_name}
                    <span className="block text-xs text-ink-muted">{roles(entry.actor_role)}</span>
                  </td>
                  <td className="tabular px-4 py-2 text-xs">
                    {entry.action}
                    <span className="block text-ink-muted">
                      {entry.entity_type} {entry.entity_id.slice(0, 18)}
                    </span>
                  </td>
                  <td className="tabular px-4 py-2 text-xs">
                    {entry.before && (
                      <span className="block text-ink-muted">− {JSON.stringify(entry.before)}</span>
                    )}
                    {entry.after && <span className="block">+ {JSON.stringify(entry.after)}</span>}
                  </td>
                  <td className="px-4 py-2 text-xs">{entry.reason ?? "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </>
  );
}
