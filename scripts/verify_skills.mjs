// Fails unless every skill restored into .agents/skills hashes to its computedHash in skills-lock.json.
// skills@1.7.4 experimental_install never checks it; the hash is its computeSkillFolderHash (dist/cli.mjs L1137-1164):
// sha256 over each file's relative path then content, sorted by localeCompare, skipping .git and node_modules.
import { createHash } from "node:crypto";
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";

function files(base, dir = base, out = []) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, e.name);
    if (e.isDirectory() && e.name !== ".git" && e.name !== "node_modules") files(base, full, out);
    else if (e.isFile()) out.push([relative(base, full).split("\\").join("/"), readFileSync(full)]);
  }
  return out;
}

function hash(dir) {
  const h = createHash("sha256");
  for (const [path, content] of files(dir).sort(([a], [b]) => a.localeCompare(b))) h.update(path).update(content);
  return h.digest("hex");
}

const { skills } = JSON.parse(readFileSync("skills-lock.json", "utf8"));
let bad = 0;
for (const [name, { computedHash }] of Object.entries(skills)) {
  let got;
  try {
    got = hash(join(".agents/skills", name));
  } catch (e) {
    got = e.code;
  }
  if (got !== computedHash) {
    console.error(`${name}: ${got}, lock says ${computedHash}`);
    bad++;
  }
}
process.exit(bad ? 1 : 0);
