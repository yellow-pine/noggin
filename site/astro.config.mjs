// The site (docs/adr/0009, 0013): Starlight's default look over the repo's Markdown, read in place
// (src/content.config.ts), and the web viewer's page (src/pages/viewer.astro). `make site` builds it into dist/.
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { satteri } from '@astrojs/markdown-satteri';
import mermaid from 'astro-mermaid';
import starlightGitHubAlerts from 'starlight-github-alerts';
import { inlineScriptHashes } from './src/csp.mjs';
import { markdown } from './src/markdown.mjs';
import { BASE, PAGES, REPO, SITE, id } from './src/pages.mjs';

export default defineConfig({
  site: SITE,
  base: BASE,
  markdown: { processor: satteri({ mdastPlugins: markdown }) },
  // The site's own files alone (docs/adr/0013). Scripts: Astro hashes what it bundles, inlineScriptHashes the inline
  // rest. Styles can't be hashed: Expressive Code's style="" attributes and the <style>s Mermaid injects at run time.
  // The viewer's Draco decoder compiles WASM in a Blob worker and GLTFLoader fetches the GLB's textures as blobs; the
  // header asks api.github.com for the repo's stars and forks. Starlight's icons are data: URLs.
  security: {
    csp: {
      directives: [
        "default-src 'self'",
        "connect-src 'self' blob: https://api.github.com",
        "worker-src 'self' blob:",
        `img-src 'self' data: blob: ${SITE}${BASE}/images/`, // the pictures' absolute URLs, in previews too
      ],
      scriptDirective: { resources: ["'self'", "'wasm-unsafe-eval'"] },
      styleDirective: {
        resources: [
          { resource: "'self'", kind: 'element' },
          { resource: "'unsafe-inline'", kind: 'element' },
          { resource: "'unsafe-inline'", kind: 'attribute' },
        ],
      },
    },
  },
  integrations: [
    mermaid(),
    starlight({
      title: 'noggin',
      social: [{ icon: 'github', label: 'GitHub', href: REPO }],
      editLink: { baseUrl: `${REPO}/edit/main/site/` }, // a page's file path is relative to site/
      markdown: { processedDirs: ['..'] }, // asides and heading anchors on the repo's Markdown
      components: { SocialIcons: './src/components/SocialIcons.astro', Footer: './src/components/Footer.astro' },
      plugins: [starlightGitHubAlerts()],
      customCss: ['./src/styles/custom.css'],
      sidebar: [
        { label: 'Home', link: '/' },
        {
          label: 'Build',
          items: [
            'docs/build/parts',
            ...[...PAGES].filter((p) => p.startsWith('docs/build/stage-')).sort().map(id), // one guide per Stage
            'docs/build/wiring',
            'docs/build/flashing',
            'docs/build/calibration',
            { label: 'Face (planned)', slug: 'docs/face-design' },
          ],
        },
        {
          label: 'Use',
          items: ['docs/use/noggin-service', 'docs/use/hooks', 'docs/use/gestures', 'docs/use/tuning'],
        },
        { label: 'Viewer', link: '/viewer/' },
        'docs/how-it-works',
        {
          label: 'Model',
          items: ['docs/pictures', { label: 'Reports', link: '/reports/' }, 'docs/model-notes'],
        },
        {
          label: 'Reference',
          items: [
            { label: 'Glossary', slug: 'glossary' },
            // every ADR, in order: Starlight's autogenerate reads src/content/docs only
            {
              label: 'Decisions',
              collapsed: true,
              items: [...PAGES].filter((p) => p.startsWith('docs/adr/')).sort().map(id),
            },
            'contributing',
            'docs/credits',
          ],
        },
      ],
    }),
    inlineScriptHashes,
  ],
});
