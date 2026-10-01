import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "https://a8d-audio-converter-1285a4af.fastapicloud.dev/api/:path*",
      },
    ];
  },
};

export default nextConfig;
