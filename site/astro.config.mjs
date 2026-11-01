// PROTOTYPE (#332): throwaway spike, never merged. Does Astro's hash-based CSP cover Starlight?
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import mermaid from 'astro-mermaid';

export default defineConfig({
  site: 'https://yellowpine.com',
  base: '/noggin',
  security: {
    csp: {
      directives: [
        "default-src 'self'",
        "connect-src 'self' blob: https://api.github.com",
        "worker-src 'self' blob:",
        "img-src 'self' data: blob:",
      ],
      scriptDirective: {
        resources: ["'self'", "'wasm-unsafe-eval'"],
        // Starlight's is:inline scripts (ThemeProvider, MobileMenuToggle, ThemeSelect, SidebarPersister x2):
        // Astro doesn't hash is:inline, so they're listed by hand; they change with Starlight upgrades.
        hashes: [
          'sha256-VWo5Wp4aqSj6nSgMpeAp9cKieaoIfwFUAunAVugI5gA=',
          'sha256-f/zAUE74ucc3JYp4r4QQvkJofoQdkOIhHYK+jeZ6eko=',
          'sha256-GkZBRnvSuhtx/cvzvukVkX2JJZW+DdPlVr7BX8Tefqo=',
          'sha256-wX2yOADeV+NMngflD5uYi3vl50SHC4sfM1EmylVjlX4=',
          'sha256-7eCV4jtsr4t4knb3c4FCRPeu7GGZeOUGE3XvWix0XOQ=',
        ],
      },
      // Styles can't be hashed: style="" attributes (Expressive Code/Shiki, Starlight) and <style> elements
      // Mermaid and astro-mermaid inject at runtime.
      styleDirective: {
        resources: [
          "'self'",
          { resource: "'unsafe-inline'", kind: 'attribute' },
          { resource: "'self'", kind: 'element' },
          { resource: "'unsafe-inline'", kind: 'element' },
        ],
      },
    },
  },
  integrations: [
    mermaid(),
    starlight({
      title: 'noggin spike',
      social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/yellow-pine/noggin' }],
      components: { SocialIcons: './src/components/SocialIcons.astro' },
      sidebar: [{ label: 'Pages', items: ['index', 'other', { label: 'Viewer', link: '/viewer/' }] }],
    }),
  ],
});
