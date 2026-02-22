import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NFL GM Simulator",
  description: "Operate any NFL front office with one shared toolkit.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-white antialiased">
        {children}
      </body>
    </html>
  );
}
