// The header's Theme bar (src/components/ThemeSelect.astro, #806): which Theme a page opens in and the CSS that shows
// only its pictures and text, from the site's macros.json (npm test)
import { expect, test } from "vitest";
import { THEMES, chosen, css } from "./theme.mjs";

test("the bar's categories and values are the model's, each category's first its default", () => {
  expect(THEMES).toEqual({ skeleton: ["realistic", "mechanical"], skin: ["morty", "bart"] });
  expect(chosen("", null)).toEqual({ skeleton: "realistic", skin: "morty" });
});

test("the address picks the Theme first, then what the reader picked last, a value the model lacks neither", () => {
  expect(chosen("?skeleton=mechanical&skin=bart", { skeleton: "realistic" })).toEqual({ skeleton: "mechanical", skin: "bart" });
  expect(chosen("?stage=2", { skeleton: "mechanical", skin: "bart" })).toEqual({ skeleton: "mechanical", skin: "bart" });
  expect(chosen("?skeleton=wooden", { skin: "lisa" })).toEqual({ skeleton: "realistic", skin: "morty" });
});

test("the CSS hides each value's pictures and text unless the page is in it, the default's when none is picked", () => {
  const rules = css();
  expect(rules).toContain(':root:not([data-skeleton="mechanical"]) [data-skeleton="mechanical"]');
  expect(rules).toContain(':root[data-skeleton]:not([data-skeleton="realistic"]) [data-skeleton="realistic"]');
  expect(rules).toContain(':root:not([data-skin="bart"]) [data-skin="bart"]');
  expect(rules).toMatch(/\{ display: none !important; \}$/);
});
