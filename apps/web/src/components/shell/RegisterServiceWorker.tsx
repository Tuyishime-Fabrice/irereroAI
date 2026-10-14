"use client";

import { useEffect } from "react";

/** Installs the offline service worker for the caregiver app. */
export function RegisterServiceWorker() {
  useEffect(() => {
    if ("serviceWorker" in navigator && process.env.NODE_ENV === "production") {
      navigator.serviceWorker.register("/sw.js").catch(() => {
        // Without a service worker the app still works online; the queue still saves reports.
      });
    }
  }, []);
  return null;
}
