import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  server: {
    host: true, // bind 0.0.0.0 so it's reachable via the EC2 public IP
    port: 3001,
    allowedHosts: true, // allow access via the EC2 public DNS/IP host header
    proxy: { "/api": { target: "http://localhost:8001", changeOrigin: true } },
  },
});
