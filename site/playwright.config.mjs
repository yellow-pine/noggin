// The browser smoke test (smoke.pw.mjs) on the built site, in the installed Chrome: npm run smoke, after make site.
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testMatch: '*.pw.mjs',
  fullyParallel: true, // the viewer's software-drawn gesture beside the other tests, not before them (#386)
  reporter: 'list', // each test's time in CI's log too
  timeout: 90_000,
  use: {
    baseURL: 'http://localhost:4321/noggin/',
    channel: 'chrome',
    // SwiftShader draws the WebGL where there is no GPU (CI's runners)
    launchOptions: { args: ['--enable-unsafe-swiftshader'] },
  },
  webServer: { command: 'npx astro preview --port 4321 --ignore-lock', url: 'http://localhost:4321/noggin/', reuseExistingServer: false },
});
