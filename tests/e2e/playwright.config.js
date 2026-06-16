// @ts-check
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: '.',
  testMatch: '*.spec.js',
  timeout: 30_000,
  retries: 1,
  reporter: 'list',
  use: {
    baseURL: process.env.SEMPTIFY_URL || 'https://semptify.org',
    headless: true,
    ignoreHTTPSErrors: false,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
