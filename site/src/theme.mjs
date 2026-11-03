// The site's Theme (docs/adr/0022, #806): one value of each category of the model's (model/geometry.py THEMES, via
// macros.json), picked in the header's bar (src/components/ThemeSelect.astro). A page marks what one value alone shows
// with data-<category>="<value>" (macros.py themed); the bar puts the Theme on <html> the same way and css() hides the
// rest, the defaults' showing where nothing is picked (no script).
import { theme } from "./macros.json";

export const THEMES = theme; // {category: [values]}, each category's first its default

// the address's Theme (?skeleton=mechanical&skin=bart), else what the reader picked last (stored), else the default
export function chosen(search, stored) {
  const link = new URLSearchParams(search);
  const pick = (c, values) => [link.get(c), stored?.[c]].find((v) => values.includes(v)) ?? values[0];
  return Object.fromEntries(Object.entries(THEMES).map(([c, values]) => [c, pick(c, values)]));
}

// one rule hiding every value's marked pictures and text but the page's
export function css() {
  const hidden = Object.entries(THEMES).flatMap(([c, [first, ...rest]]) => [
    ...rest.map((v) => `:root:not([data-${c}="${v}"]) [data-${c}="${v}"]`),
    `:root[data-${c}]:not([data-${c}="${first}"]) [data-${c}="${first}"]`,
  ]);
  return `${hidden.join(",\n")} { display: none !important; }`;
}
