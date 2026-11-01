// The browser smoke test (smoke.pw.mjs) on the built site, in the installed Chrome: npm run smoke, after make site.
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testMatch: '*.pw.mjs',
  timeout: 90_000,
  use: {
    baseURL: 'http://localhost:4321/noggin/',
    channel: 'chrome',
    // SwiftShader draws the WebGL where there is no GPU (CI's runners)
    launchOptions: { args: ['--enable-unsafe-swiftshader'] },
  },
  webServer: { command: 'npx astro preview --port 4321 --ignore-lock', url: 'http://localhost:4321/noggin/', reuseExistingServer: false },
});
