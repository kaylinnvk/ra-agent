import type { Metadata } from "next";
import { Poppins } from "next/font/google";
import type { ReactNode } from "react";
import { Analytics } from "@vercel/analytics/react";
import { BackToTop } from "@/components/BackToTop";
import "./globals.css";

const poppins = Poppins({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-poppins",
});

export const metadata: Metadata = {
  title: "RA Agent Logs",
  description: "Operational dashboard for RA scanner runs, source checks, and findings.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body className={poppins.variable}>
        {children}
        <BackToTop />
        <Analytics />
      </body>
    </html>
  );
}
