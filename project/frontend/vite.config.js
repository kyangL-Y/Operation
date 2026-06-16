import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 1234,
    proxy: {
      "/api": {
        target: process.env.VITE_PROXY_TARGET || "http://localhost:8080",
        changeOrigin: true
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          const mammothDeps = [
            "node_modules/mammoth",
            "node_modules/jszip",
            "node_modules/xmlbuilder",
            "node_modules/underscore",
            "node_modules/@xmldom",
            "node_modules/bluebird",
            "node_modules/dingbat-to-unicode",
            "node_modules/lop",
            "node_modules/base64-js",
            "node_modules/argparse",
            "node_modules/path-is-absolute"
          ];
          const pdfjsDeps = [
            "node_modules/pdfjs-dist",
            "node_modules/node-readable-to-web-readable-stream",
            "node_modules/@napi-rs/canvas"
          ];

          if (id.includes("node_modules/echarts")) {
            return "echarts";
          }
          if (pdfjsDeps.some((dep) => id.includes(dep))) {
            return "pdfjs";
          }
          if (mammothDeps.some((dep) => id.includes(dep))) {
            return "mammoth";
          }
          if (id.includes("node_modules/axios")) {
            return "axios";
          }
          if (id.includes("node_modules/vue") || id.includes("node_modules/vue-router")) {
            return "vue-vendor";
          }
          if (id.includes("node_modules")) {
            return "vendor";
          }
        }
      }
    }
  }
});
