// The site (docs/adr/0009, 0013): Starlight over the repo's Markdown, read in place (src/content.config.ts), in the
// site's own look (src/styles/custom.css, #603), the web viewer's page (src/pages/viewer.astro) and the sim reports'
// (src/pages/reports.astro). `just site` builds it into dist/.
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { satteri } from '@astrojs/markdown-satteri';
import mermaid from 'astro-mermaid';
import starlightGitHubAlerts from 'starlight-github-alerts';
import { inlineScriptHashes } from './src/csp.mjs';
import { markdown } from './src/markdown.mjs';
import { BASE, HOME, PAGES, REPO, SITE, id } from './src/pages.mjs';

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
        `img-src 'self' data: blob: ${SITE}${HOME}/images/`, // the pictures' absolute URLs, in previews and Docs versions too
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
    // the diagrams in the site's colours (#603), on a paper card in either theme (src/styles/custom.css)
    mermaid({
      theme: 'base',
      autoTheme: false,
      mermaidConfig: {
        themeVariables: {
          fontFamily: 'system-ui, sans-serif',
          primaryColor: '#F7CED7', // Milky Pink
          primaryTextColor: '#202020',
          primaryBorderColor: '#2B2B2E',
          secondaryColor: '#FFB673', // Apricot
          tertiaryColor: '#FDF0F3',
          lineColor: '#5F5F5F', // the pictures' Line Art
          noteBkgColor: '#FFB673',
          noteTextColor: '#202020',
          noteBorderColor: '#2B2B2E',
          edgeLabelBackground: '#FCFCFC',
        },
      },
    }),
    starlight({
      title: 'noggin',
      // its icon: Starlight's default, public/favicon.svg, Yellow Pine's pine; no render of the Mech (#640)
      social: [{ icon: 'github', label: 'GitHub', href: REPO }],
      editLink: { baseUrl: `${REPO}/edit/main/site/` }, // a page's file path is relative to site/
      markdown: { processedDirs: ['..'] }, // asides and heading anchors on the repo's Markdown
      components: {
        SiteTitle: './src/components/SiteTitle.astro',
        PageTitle: './src/components/PageTitle.astro',
        SocialIcons: './src/components/SocialIcons.astro',
        Footer: './src/components/Footer.astro',
      },
      plugins: [starlightGitHubAlerts()],
      customCss: ['@fontsource/rubik/700.css', './src/styles/custom.css'], // #603: the headings' Rubik, the site's own
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
            'docs/build/tests',
            { label: 'Shells (planned)', slug: 'docs/face-design' },
          ],
        },
        {
          label: 'Use',
          items: ['docs/use/noggin-service', 'docs/use/hooks', 'docs/use/gestures', 'docs/use/tuning'],
        },
        'docs/how-it-works',
        {
          label: 'Model',
          // main's sim reports, which a Docs version (docs/adr/0014) links on the live site
          items: [
            'docs/pictures',
            { label: 'Viewer', link: '/viewer/' },
            { label: 'Reports', link: BASE === HOME ? '/reports/' : `${SITE}${HOME}/reports/` },
            'docs/model-notes',
          ],
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
            'docs/ci-cd',
            'docs/credits',
          ],
        },
      ],
    }),
    inlineScriptHashes,
  ],
});
