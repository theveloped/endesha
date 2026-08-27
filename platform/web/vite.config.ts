import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import wasm from "vite-plugin-wasm";
import tailwindcss from "@tailwindcss/vite";

// wasm(): @eclipse-zenoh/zenoh-ts ships a wasm-bindgen ESM-integration
// module (zenoh_keyexpr_wrapper_bg.wasm) that Vite cannot load natively.
// The plugin emits top-level await, which Vite 8's baseline browser target
// supports — no vite-plugin-top-level-await needed (it requires rollup,
// incompatible with rolldown-vite).
//
// zenoh-ts is excluded from prebundling (the wasm import must stay an ESM
// import), so its CJS transitive deps must be prebundled explicitly for
// named-export interop in dev.
export default defineConfig({
  plugins: [react(), wasm(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    // Multi-page: the operator UI and headless render-only camera bundle.
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, "index.html"),
        headless: path.resolve(__dirname, "headless.html"),
      },
    },
  },
  optimizeDeps: {
    exclude: ["@eclipse-zenoh/zenoh-ts"],
    include: ["channel-ts", "typed-duration", "base64-arraybuffer", "uuid"],
  },
});
