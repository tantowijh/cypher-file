import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination:
          process.env.NEXT_PUBLIC_API_URL
            ? `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`
            : process.env.NODE_ENV === "development"
              ? "http://127.0.0.1:8000/api/:path*"
              : "http://backend:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;