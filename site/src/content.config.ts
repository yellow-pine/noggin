// The docs collection is the repo's Markdown read in place (docs/adr/0012): every page keeps its path, title and links
// as GitHub shows them, with no front matter.
import { readFileSync } from 'node:fs';
import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { docsSchema } from '@astrojs/starlight/schema';
import { PATTERN, ROOT, id } from './pages.mjs';

const pages = glob({ base: ROOT, pattern: PATTERN, generateId: ({ entry }) => id(entry) });

export const collections = {
  docs: defineCollection({
    schema: docsSchema(),
    loader: {
      name: 'repo-markdown',
      // Starlight wants a title in front matter: ours is the page's H1, which each page opens with (site.test.mjs);
      // the landing page is a splash, no sidebar
      load: (context) =>
        pages.load({
          ...context,
          parseData: ({ data, ...entry }) =>
            context.parseData({
              ...entry,
              data: {
                title: readFileSync(entry.filePath!, 'utf8').match(/^# (.+)$/m)?.[1],
                ...(entry.id === 'index' && { template: 'splash' }),
                ...data,
              },
            }),
        }),
    },
  }),
};
