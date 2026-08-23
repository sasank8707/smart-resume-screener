import { useEffect, useState } from "react";

export interface Toast {
  id: number;
  kind: "success" | "error";
  message: string;
}

type Listener = (toasts: Toast[]) => void;

let toasts: Toast[] = [];
let listeners: Listener[] = [];
let nextId = 1;

function emit() {
  listeners.forEach((listener) => listener([...toasts]));
}

export function notify(kind: Toast["kind"], message: string, ttl = 4200) {
  const toast: Toast = { id: nextId++, kind, message };
  toasts = [...toasts, toast];
  emit();
  window.setTimeout(() => {
    toasts = toasts.filter((t) => t.id !== toast.id);
    emit();
  }, ttl);
}

export const notifySuccess = (message: string) => notify("success", message);
export const notifyError = (message: string) =>
  notify("error", message, 6000);

export function useToasts(): Toast[] {
  const [current, setCurrent] = useState<Toast[]>(toasts);
  useEffect(() => {
    listeners.push(setCurrent);
    return () => {
      listeners = listeners.filter((l) => l !== setCurrent);
    };
  }, []);
  return current;
}
