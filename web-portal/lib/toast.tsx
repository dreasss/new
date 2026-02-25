import { createContext, ReactNode, useContext, useMemo, useState } from "react";

type ToastKind = "success" | "error" | "info";

export type ToastItem = {
  id: string;
  kind: ToastKind;
  text: string;
};

type ToastContextValue = {
  items: ToastItem[];
  push: (kind: ToastKind, text: string) => void;
  remove: (id: string) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const value = useMemo<ToastContextValue>(
    () => ({
      items,
      push(kind, text) {
        const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
        setItems((prev) => [...prev, { id, kind, text }]);
        setTimeout(() => {
          setItems((prev) => prev.filter((item) => item.id !== id));
        }, 4500);
      },
      remove(id) {
        setItems((prev) => prev.filter((item) => item.id !== id));
      },
    }),
    [items],
  );

  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
