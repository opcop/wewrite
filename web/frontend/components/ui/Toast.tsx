"use client";
import { Toast } from "@base-ui/react/toast";
import type { ReactNode } from "react";
import { cn } from "./cn";

/**
 * Inner list that reads from the nearest Toast.Provider context and maps
 * each toast to a Toast.Root. Must be rendered inside Toast.Viewport.
 */
function ToastList() {
  const { toasts } = Toast.useToastManager();
  return (
    <>
      {toasts.map((toast) => (
        <Toast.Root
          key={toast.id}
          toast={toast}
          className={cn(
            "relative flex w-full flex-col gap-1 rounded-lg border border-border",
            "bg-surface px-4 py-3 shadow-xl text-sm text-text",
            "data-[ending-style]:opacity-0 data-[ending-style]:translate-x-4",
            "data-[starting-style]:opacity-0 data-[starting-style]:translate-x-4",
            "transition-all duration-200",
            toast.type === "error" && "border-red-500/60 bg-red-950/30",
          )}
        >
          <Toast.Content className="flex flex-col gap-0.5">
            {toast.title && (
              <Toast.Title className="font-semibold leading-snug" />
            )}
            <Toast.Description className="text-muted leading-snug" />
          </Toast.Content>
          <Toast.Close
            className={cn(
              "absolute right-2 top-2 rounded p-0.5 text-muted",
              "hover:text-text hover:bg-surface-2 transition-colors",
            )}
            aria-label="关闭"
          >
            ✕
          </Toast.Close>
        </Toast.Root>
      ))}
    </>
  );
}

/**
 * ToastProvider must be mounted once near the root of your app (e.g. in layout.tsx).
 * It manages toast state and renders the viewport portal at the bottom-right.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  return (
    <Toast.Provider>
      {children}
      <Toast.Portal>
        <Toast.Viewport
          className={cn(
            "fixed bottom-4 right-4 z-[100] flex w-80 flex-col gap-2",
            "outline-none",
          )}
        >
          <ToastList />
        </Toast.Viewport>
      </Toast.Portal>
    </Toast.Provider>
  );
}

/**
 * Hook for triggering toasts from any client component.
 *
 * Usage:
 *   const toast = useToast();
 *   toast.error("Something went wrong");
 *   toast.notice("Saved successfully");
 */
export function useToast() {
  const manager = Toast.useToastManager();
  return {
    error: (text: string) =>
      manager.add({ title: "出错了", description: text, type: "error" }),
    notice: (text: string) =>
      manager.add({ description: text }),
  };
}
