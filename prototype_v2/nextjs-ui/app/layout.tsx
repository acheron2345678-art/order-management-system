import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Nova Order Prototype",
  description: "Next.js comparison UI for the FastAPI prototype",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
