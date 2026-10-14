"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";

import {
  enqueue,
  flush,
  listQueued,
  removeQueued,
  type QueuedReport,
  type ReportBody,
} from "./outbox";

function subscribeOnline(callback: () => void) {
  window.addEventListener("online", callback);
  window.addEventListener("offline", callback);
  return () => {
    window.removeEventListener("online", callback);
    window.removeEventListener("offline", callback);
  };
}

/** The offline queue with live online status; sends automatically when the phone reconnects. */
export function useOutbox() {
  const online = useSyncExternalStore(
    subscribeOnline,
    () => navigator.onLine,
    () => true,
  );
  const [items, setItems] = useState<QueuedReport[]>([]);
  const [lastSent, setLastSent] = useState(0);

  const refresh = useCallback(async () => setItems(await listQueued()), []);
  const sync = useCallback(async () => {
    const sent = await flush();
    if (sent) setLastSent(sent);
    await refresh();
  }, [refresh]);

  useEffect(() => {
    void listQueued().then(setItems);
  }, []);
  useEffect(() => {
    if (!online) return;
    let active = true;
    void flush().then(async (sent) => {
      const queued = await listQueued();
      if (!active) return;
      if (sent) setLastSent(sent);
      setItems(queued);
    });
    return () => {
      active = false;
    };
  }, [online]);

  return {
    online,
    items,
    lastSent,
    sync,
    add: async (body: ReportBody) => {
      await enqueue(body);
      await refresh();
    },
    discard: async (id: string) => {
      await removeQueued(id);
      await refresh();
    },
  };
}
