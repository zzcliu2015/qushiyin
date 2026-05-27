import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "去水印处理台",
  description: "面向已授权短视频素材的网页处理工具"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}

