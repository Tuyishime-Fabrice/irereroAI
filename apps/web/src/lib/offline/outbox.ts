/**
 * Reports waiting to be sent, kept in IndexedDB so they survive closing the app offline.
 * Sending happens from the page when the app opens and whenever the phone comes back online.
 */
import type { Schemas } from "@/lib/api/client";

export type ReportBody = Schemas["ReportIn"];
export type QueuedStatus = "waiting" | "sending" | "needs_attention";
export type QueuedReport = {
  id: string;
  body: ReportBody;
  queuedAt: string;
  status: QueuedStatus;
  issues?: Schemas["Issue"][];
};

const DB = "irerero-outbox";
const STORE = "reports";

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE, { keyPath: "id" });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function run<T>(
  mode: IDBTransactionMode,
  work: (store: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  const db = await open();
  return new Promise((resolve, reject) => {
    const request = work(db.transaction(STORE, mode).objectStore(STORE));
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export const listQueued = () =>
  run<QueuedReport[]>("readonly", (s) => s.getAll() as IDBRequest<QueuedReport[]>);
export const saveQueued = (item: QueuedReport) => run("readwrite", (s) => s.put(item));
export const removeQueued = (id: string) => run("readwrite", (s) => s.delete(id));

export async function enqueue(body: ReportBody): Promise<QueuedReport> {
  const item: QueuedReport = {
    id: `${body.centre_code}:${body.week_start}`,
    body: { ...body, channel: "offline" },
    queuedAt: new Date().toISOString(),
    status: "waiting",
  };
  await saveQueued(item);
  return item;
}

export type SendResult = "sent" | "duplicate" | "invalid" | "offline";

export async function send(
  body: ReportBody,
): Promise<{ result: SendResult; issues?: Schemas["Issue"][] }> {
  let response: Response;
  try {
    response = await fetch("/api/reports", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    return { result: "offline" };
  }
  if (response.status === 201) return { result: "sent" };
  if (response.status === 409) return { result: "duplicate" };
  if (response.status === 422) {
    const detail = (await response.json().catch(() => null)) as Schemas["ValidationOut"] | null;
    return { result: "invalid", issues: [...(detail?.errors ?? []), ...(detail?.warnings ?? [])] };
  }
  return { result: "offline" };
}

/** Try to send everything waiting. Returns how many were sent. */
export async function flush(): Promise<number> {
  let sent = 0;
  for (const item of await listQueued()) {
    if (item.status === "needs_attention") continue;
    await saveQueued({ ...item, status: "sending" });
    const { result, issues } = await send(item.body);
    if (result === "sent" || result === "duplicate") {
      await removeQueued(item.id);
      sent += 1;
    } else if (result === "invalid") {
      await saveQueued({ ...item, status: "needs_attention", issues });
    } else {
      await saveQueued({ ...item, status: "waiting" });
      break;
    }
  }
  return sent;
}
