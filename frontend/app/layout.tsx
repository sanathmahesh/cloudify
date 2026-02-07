import type { Metadata } from "next";
import { Space_Grotesk, Inter, Montserrat } from "next/font/google";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  weight: ["400", "500", "600", "700"],
  variable: "--font-space-grotesk",
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
    <html lang="en" className={`${spaceGrotesk.variable} ${inter.variable} ${montserrat.variable}`}>
      <body className="font-sans bg-bg-primary text-text-secondary antialiased">
        {children}
      </body>
    </html>
  );
}
