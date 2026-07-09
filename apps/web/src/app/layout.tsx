import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppHeader } from "@/components/app-header";

import "./globals.css";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export const metadata: Metadata = {
  title: "Notebook",
  description: "个人 AI 知识库",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <AppHeader />
        {children}
        <script
          dangerouslySetInnerHTML={{
            __html: `window.NOTEBOOK_API_URL=${JSON.stringify(API_URL)};`,
          }}
        />
        <script defer src="/knowledge-list.js" />
      </body>
    </html>
  );
}
