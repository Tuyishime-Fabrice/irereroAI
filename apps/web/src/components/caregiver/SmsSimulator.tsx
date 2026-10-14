"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { SmsPreview } from "@/components/signature/SmsPreview";
import { Button } from "@/components/ui/Button";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { api, type Schemas } from "@/lib/api/client";

/** Shows the same weekly report as a coded SMS for basic phones, and what the system reads. */
export function SmsSimulator() {
  const t = useTranslations("sms");
  const report = useTranslations("report");
  const [format, setFormat] = useState<Schemas["SmsFormat"] | null>(null);
  const [text, setText] = useState("");
  const [result, setResult] = useState<Schemas["SmsResult"] | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.GET("/sms/format").then(({ data }) => {
      if (!data) return;
      setFormat(data);
      setText(data.example);
    });
  }, []);

  async function sendSms() {
    setBusy(true);
    const { data } = await api.POST("/sms/simulate", { body: { text } });
    setResult(data ?? null);
    setBusy(false);
  }

  const reply = result
    ? result.status === "format_error"
      ? t(`reply.format_error`, {
          problem: t(`formatError.${result.format_error ?? "wrong_count"}`, {
            detail: result.format_detail ?? "",
          }),
        })
      : t(`reply.${result.status}`)
    : undefined;

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-5">
      <div>
        <h1 className="font-display text-3xl text-ink">{t("title")}</h1>
        <p className="text-ink-muted">{t("lead")}</p>
      </div>
      <Panel className="p-5">
        <SmsPreview
          message={text}
          reply={reply}
          parsed={
            <div className="flex flex-col gap-3">
              <label className="flex flex-col gap-1 text-sm font-medium text-ink">
                {t("message")}
                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  rows={3}
                  className="tabular rounded-md border border-line-strong bg-surface p-3 text-base"
                />
              </label>
              <Button variant="primary" onClick={sendSms} disabled={busy || !text.trim()}>
                {t("send")}
              </Button>
              {result?.parsed && (
                <table className="w-full text-sm">
                  <caption className="mb-1 text-left font-semibold text-ink">{t("parsed")}</caption>
                  <tbody>
                    {Object.entries(result.parsed)
                      .filter(([key]) => key !== "confirmed" && key !== "channel")
                      .map(([key, value]) => (
                        <tr key={key} className="border-t border-line">
                          <th scope="row" className="py-1 text-left font-normal text-ink-muted">
                            {t(`field.${key}`)}
                          </th>
                          <td className="tabular py-1 text-right">
                            {typeof value === "boolean"
                              ? value
                                ? report("yes")
                                : report("no")
                              : key === "main_problem"
                                ? report(`problems.${value}`)
                                : String(value)}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              )}
              {result?.validation &&
                [...result.validation.errors, ...result.validation.warnings].map((issue) => (
                  <p key={issue.code} className="text-sm text-danger">
                    {report(`issue.${issue.code}`)}
                  </p>
                ))}
            </div>
          }
        />
      </Panel>
      {format && (
        <Panel>
          <PanelHeader title={t("formatTitle")} />
          <div className="p-4 text-sm">
            <p className="tabular rounded-md bg-paper p-3">{format.example}</p>
            <ol className="mt-3 grid gap-1 sm:grid-cols-2">
              {format.fields.map((field, i) => (
                <li key={field} className="text-ink">
                  <span className="tabular text-ink-muted">{i + 1}.</span>{" "}
                  {t(
                    `field.${field === "centre" ? "centre_code" : field === "week" ? "week_start" : field}`,
                  )}
                </li>
              ))}
            </ol>
            <p className="mt-3 text-ink-muted">
              {t("problemCodes")}{" "}
              {format.problems.map((p, i) => `${i} = ${report(`problems.${p}`)}`).join(", ")}
            </p>
            <p className="mt-1 text-ink-muted">{t("okNote")}</p>
          </div>
        </Panel>
      )}
    </div>
  );
}
