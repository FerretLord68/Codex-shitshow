const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./tests/e2e",
  timeout: 30000,
  use: {
    baseURL: process.env.E2E_BASE_URL || "https://codex-shitshow.fejlgoblin.ovh",
    locale: "da-DK",
    colorScheme: "light",
  },
  reporter: [["list"], ["html", { outputFolder: "playwright-report", open: "never" }]],
});

