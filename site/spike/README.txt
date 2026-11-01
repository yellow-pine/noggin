PROTOTYPE (#332), throwaway, never merged. Question: does Astro's hash-based CSP cover Starlight + Pagefind + astro-mermaid + three.js/Draco + a fetch to api.github.com?
Run: npm ci && npm run build && npx astro preview --port 4329, then run csp-probe.js with Playwright (page => ...) in Chrome.
hashcheck.mjs lists inline <script>/<style> bodies whose sha256 is missing from the CSP meta. ablate.sh drops one CSP token from the built pages to see what breaks.
Verdict: https://github.com/yellow-pine/noggin/issues/331 (comment).
