/** The tour's position, kept in sessionStorage so it survives page changes and sign-ins. */
const KEY = "irerero_tour_step";
const EVENT = "irerero-tour";

export function readStep(): number | null {
  try {
    const value = sessionStorage.getItem(KEY);
    return value === null ? null : Number(value);
  } catch {
    return null;
  }
}

export function writeStep(step: number | null) {
  try {
    if (step === null) sessionStorage.removeItem(KEY);
    else sessionStorage.setItem(KEY, String(step));
  } catch {
    // Without storage the tour still runs within the current page.
  }
  window.dispatchEvent(new Event(EVENT));
}

export function subscribe(callback: () => void) {
  window.addEventListener(EVENT, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}
