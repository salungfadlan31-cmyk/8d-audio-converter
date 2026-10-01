import type { NextConfig } from "next";

// Routing /api/* dan /outputs/* ke backend ditangani oleh Vercel Services di vercel.json root.
// Tidak diperlukan rewrites Next.js ke URL backend eksternal.
// Untuk local dev gunakan: vercel dev (dari root project), bukan next dev langsung.
const nextConfig: NextConfig = {};

export default nextConfig;

