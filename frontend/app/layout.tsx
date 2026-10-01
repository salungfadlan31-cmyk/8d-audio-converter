import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "8D Audio Converter – Transform Your Music Into 8D Experience",
  description:
    "Convert your songs into immersive 8D, slow and reverb audio. Upload MP3 or WAV files and get studio-quality 8D audio in seconds.",
  keywords: ["8D audio", "8D converter", "slow reverb", "audio effect", "music converter"],
  openGraph: {
    title: "8D Audio Converter",
    description: "Transform Your Music Into 8D Experience",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        {/* Animated background orbs */}
        <div className="bg-animated" aria-hidden="true">
          <div className="bg-orb bg-orb-1" />
          <div className="bg-orb bg-orb-2" />
          <div className="bg-orb bg-orb-3" />
        </div>
        <div style={{ position: "relative", zIndex: 1 }}>
          {children}
        </div>
      </body>
    </html>
  );
}
