import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  projects: [{ name: "Microsoft Edge", use: { browserName: "chromium", channel: "msedge" } }],
});
