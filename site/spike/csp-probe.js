async (page) => {
  const base = 'http://localhost:4329/noggin';
  const out = {};
  await page.addInitScript(() => {
    window.__v = [];
    document.addEventListener('securitypolicyviolation', e => window.__v.push(`${e.effectiveDirective} blocked ${e.blockedURI || 'inline'} @${e.sourceFile ? e.sourceFile.split('/').pop() : ''}:${e.lineNumber} sample=${(e.sample||'').slice(0,40)}`));
  });
  const consoleErr = [];
  page.on('console', m => { if (m.type() === 'error' || /Content Security Policy/.test(m.text())) consoleErr.push(`[${page.url().replace(base,'')}] ${m.text().slice(0,200)}`); });
  for (const p of ['/', '/other/', '/viewer/']) {
    await page.goto(base + p, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);
    out[p] = {
      violations: await page.evaluate(() => window.__v),
      ghFacts: await page.locator('#gh-facts').first().textContent(),
      mermaidSvg: await page.locator('pre.mermaid svg, .mermaid svg').count(),
      themeProvider: await page.evaluate(() => typeof window.StarlightThemeProvider),
      viewer: p === '/viewer/' ? await page.locator('#status').textContent() : undefined,
    };
  }
  await page.goto(base + '/', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: /search/i }).first().click();
  await page.locator('dialog input[type=search], .pagefind-ui__search-input').first().fill('servo');
  await page.waitForTimeout(2000);
  out.search = {
    results: await page.locator('.pagefind-ui__result').count(),
    first: await page.locator('.pagefind-ui__result-link').first().textContent().catch(() => null),
    violations: await page.evaluate(() => window.__v),
  };
  out.cspConsole = consoleErr.filter(m => /Content Security Policy/.test(m));
  out.otherConsoleErrors = consoleErr.filter(m => !/Content Security Policy/.test(m));
  return JSON.stringify(out);
}
