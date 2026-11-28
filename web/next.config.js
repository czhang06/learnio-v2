/** @type {import('next').NextConfig} */
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Question images through this app's own origin: Vercel's CDN keeps each
    // one (the API marks them immutable, with s-maxage), so after the first
    // view they load from a nearby edge instead of the API on Render.
    return [{ source: "/q-images/:name", destination: API_URL + "/api/images/:name" }];
  },
};

module.exports = nextConfig;
