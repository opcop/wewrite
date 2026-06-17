import type { HTMLAttributes } from "react";
import { cn } from "./cn";
type Tone = "neutral" | "ok" | "warn" | "danger";
const TONES: Record<Tone, string> = {
  neutral: "bg-surface-2 text-muted",
  ok: "bg-success/15 text-success",
  warn: "bg-danger/10 text-danger",
  danger: "bg-danger/15 text-danger",
};
export function Badge({ tone = "neutral", className, ...props }: HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  return <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs", TONES[tone], className)} {...props} />;
}
