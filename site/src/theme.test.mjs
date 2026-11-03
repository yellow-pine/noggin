// The header's Theme bar (src/components/ThemeSelect.astro, #806, #819): which Preset a page opens in and the CSS that
// shows only its pictures and text, from the site's macros.json (npm test)
import { expect, test } from "vitest";
import { AXES, PRESETS, css, picked } from "./theme.mjs";

test("the bar's Presets are the model's, Cansin's build first, the default, each a value on every axis", () => {
  expect(Object.keys(PRESETS)).toEqual(["cansins-build", "morty", "bart"]);
  expect(PRESETS["cansins-build"]).toEqual({
    label: "Cansin's build", "skeleton-shape": "mechanical", "skeleton-palette": "black", "skin-shape": "cansin", "skin-palette": "cansin",
  });
  expect(AXES["skeleton-palette"]).toEqual(["anatomical", "robot", "black"]);
});

test("the address picks the Preset first, then what the reader picked last, never the default alone (#883)", () => {
  expect(picked("?preset=bart", "morty")).toBe("bart");
  expect(picked("?stage=2", "cansins-build")).toBe("cansins-build");
  expect(picked("", null)).toBeUndefined();
  expect(picked("?preset=lisa", "homer")).toBeUndefined();  // a Preset the model lacks neither
});

test("the CSS hides what is marked for other Presets than the page's, all but the default's when none is picked", () => {
  const rules = css();
  expect(rules).toContain(':root:not([data-preset]) [data-presets]:not([data-presets~="cansins-build"])');
  expect(rules).toContain(':root[data-preset="morty"] [data-presets]:not([data-presets~="morty"])');
  expect(rules).toMatch(/\{ display: none !important; \}$/);
});
