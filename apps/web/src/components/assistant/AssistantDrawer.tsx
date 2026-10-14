"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { CloseIcon } from "@/components/ui/icons";
import { api, type Schemas } from "@/lib/api/client";

export type AssistantSubject = { kind: "recommendation" | "alert"; id: string; title: string };
const QUESTIONS = ["why", "sources", "uncertainty", "who_decides"] as const;

/**
 * "Why this suggestion?": answers built only from platform records, each naming the tables
 * it used. Phase 1 answers come from templates; no language model is called.
 */
export function AssistantDrawer({
  subject,
  onClose,
}: {
  subject: AssistantSubject | null;
  onClose: () => void;
}) {
  const t = useTranslations("assistant");
  const locale = useLocale();
  const [answers, setAnswers] = useState<Schemas["AnswerOut"][]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const node = dialog.current;
    if (!node) return;
    if (subject && !node.open) node.showModal();
    if (!subject && node.open) node.close();
  }, [subject]);

  async function ask(text: string) {
    if (!subject) return;
    setBusy(true);
    const { data } = await api.POST("/assistant/ask", {
      body: {
        subject: subject.kind,
        subject_id: subject.id,
        question: text,
        language: locale === "rw" ? "rw" : "en",
      },
    });
    if (data) setAnswers((list) => [...list, data]);
    setBusy(false);
  }

  return (
    <dialog
      ref={dialog}
      onClose={() => {
        setAnswers([]);
        onClose();
      }}
      aria-labelledby="assistant-title"
      className="fixed inset-y-0 right-0 left-auto m-0 h-full max-h-none w-full max-w-md border-l border-line bg-surface p-0 text-ink backdrop:bg-ink/30"
    >
      <div className="flex h-full flex-col">
        <header className="flex items-start justify-between gap-3 border-b border-line p-4">
          <div>
            <p className="text-xs font-semibold tracking-wide text-clay uppercase">{t("label")}</p>
            <h2 id="assistant-title" className="font-semibold">
              {subject?.title}
            </h2>
          </div>
          <button
            type="button"
            onClick={() => dialog.current?.close()}
            aria-label={t("close")}
            className="rounded-md p-2 text-ink-muted hover:bg-paper"
          >
            <CloseIcon />
          </button>
        </header>
        <div className="flex flex-1 flex-col gap-3 overflow-y-auto p-4" aria-live="polite">
          <p className="text-sm text-ink-muted">{t("intro")}</p>
          <div className="flex flex-wrap gap-2">
            {QUESTIONS.map((q) => (
              <Button key={q} variant="secondary" disabled={busy} onClick={() => ask(q)}>
                {t(`questions.${q}`)}
              </Button>
            ))}
          </div>
          {answers.map((answer, i) => (
            <article key={i} className="rounded-md border border-line bg-paper p-3">
              <p className="text-xs text-ink-muted">{t(`questions.${answer.question}`)}</p>
              <p className="mt-1 text-sm text-ink">{answer.text}</p>
              {answer.tables.length > 0 && (
                <p className="mt-2 text-xs text-ink-muted">
                  {t("from")} <span className="tabular">{answer.tables.join(", ")}</span>
                </p>
              )}
            </article>
          ))}
        </div>
        <form
          className="flex gap-2 border-t border-line p-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (question.trim()) void ask(question.trim());
            setQuestion("");
          }}
        >
          <label className="sr-only" htmlFor="assistant-question">
            {t("ask")}
          </label>
          <input
            id="assistant-question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={t("placeholder")}
            className="min-w-0 flex-1 rounded-md border border-line-strong bg-surface px-3"
          />
          <Button type="submit" variant="primary" disabled={busy}>
            {t("ask")}
          </Button>
        </form>
        <p className="px-4 pb-4 text-xs text-ink-muted">{t("templatesNote")}</p>
      </div>
    </dialog>
  );
}
