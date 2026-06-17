import type { InputHTMLAttributes } from "react";
import { cn } from "./cn";
export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "w-full h-10 px-3 rounded-md bg-surface-2 text-text border border-border placeholder:text-muted",
        "focus:outline-none focus:border-accent transition-colors", className,
      )}
      {...props}
    />
  );
}
