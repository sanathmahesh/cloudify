import type { Metadata } from "next";
import { Instrument_Serif, Inter, Montserrat } from "next/font/google";
import "./globals.css";

const instrumentSerif = Instrument_Serif({
  weight: "400",
  style: "italic",
  variable: "--font-instrument-serif",
  subsets: ["latin"],
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const montserrat = Montserrat({
  weight: ["900"],
  variable: "--font-montserrat",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Cloudify — Migrate to the Cloud in One Command",
  description:
    "AI-powered migration of Spring Boot + React apps to Google Cloud Platform. Automated, safe, and fast.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${instrumentSerif.variable} ${inter.variable} ${montserrat.variable}`}>
      <body className="font-sans bg-bg-primary text-text-secondary antialiased">
        {children}
      </body>
    </html>
  );
}
