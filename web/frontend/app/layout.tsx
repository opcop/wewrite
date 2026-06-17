import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";
import { ToastProvider, TooltipProvider } from "@/components/ui";

export const metadata: Metadata = {
  title: "WeWrite",
  description: "AI 内容分发平台：一句话生成内容，智能改写后一键分发到公众号、小红书、抖音。",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>
        <div className="app-root isolate min-h-screen bg-bg text-text">
          <TooltipProvider>
            <ToastProvider>
              <header className="sticky top-0 z-40 flex items-center justify-between border-b border-border bg-surface/80 px-6 py-3 backdrop-blur">
                <div className="font-semibold tracking-tight">
                  We<span className="text-accent">Write</span>
                  <span className="ml-2 text-sm font-normal text-muted">· 内容分发平台</span>
                </div>
                <nav className="flex gap-1 text-sm">
                  <Link className="rounded px-3 py-1.5 text-muted transition-colors hover:bg-surface-2 hover:text-text" href="/">创作</Link>
                  <Link className="rounded px-3 py-1.5 text-muted transition-colors hover:bg-surface-2 hover:text-text" href="/settings">设置</Link>
                </nav>
              </header>
              <main className="mx-auto max-w-3xl px-6 py-8">{children}</main>
            </ToastProvider>
          </TooltipProvider>
        </div>
      </body>
    </html>
  );
}
