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
              <div className="topbar">
                <div className="brand">
                  We<span>Write</span> · 内容分发平台
                </div>
                <nav className="navlinks">
                  <Link href="/">创作</Link>
                  <Link href="/settings">设置</Link>
                </nav>
              </div>
              <div className="container">{children}</div>
            </ToastProvider>
          </TooltipProvider>
        </div>
      </body>
    </html>
  );
}
