import type { TextareaHTMLAttributes } from "react";
import { cn } from "./cn";
export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "w-full px-3 py-2 rounded-md bg-surface-2 text-text border border-border placeholder:text-muted",
        "focus:outline-none focus:border-accent transition-colors resize-y", className,
      )}
      {...props}
    />
  );
}
