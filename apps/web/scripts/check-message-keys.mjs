// Fails when code asks for a message key that does not exist or that is a group, not a string.
// Checks literal keys: const t = useTranslations("ns") / getTranslations("ns"), then t("key").
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const messages = JSON.parse(readFileSync("messages/en.json", "utf8"));
const lookup = (path) =>
  path
    .split(".")
    .reduce((node, part) => (node && typeof node === "object" ? node[part] : undefined), messages);
const files = [];
const walk = (dir) => {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) walk(path);
    else if (/\.tsx?$/.test(name) && !name.endsWith(".d.ts")) files.push(path);
  }
};
walk("src");

const problems = [];
for (const file of files) {
  const source = readFileSync(file, "utf8");
  const namespaces = new Map();
  for (const m of source.matchAll(
    /const (\w+) = (?:await )?(?:useTranslations|getTranslations)\((?:"([\w.]+)")?\)/g,
  )) {
    namespaces.set(m[1], m[2] ?? "");
  }
  for (const [fn, ns] of namespaces) {
    for (const m of source.matchAll(new RegExp(`\\b${fn}\\("([\\w.]+)"`, "g"))) {
      const key = ns ? `${ns}.${m[1]}` : m[1];
      if (typeof lookup(key) !== "string") problems.push(`${file}: ${key}`);
    }
  }
}
if (problems.length) {
  console.error(problems.join("\n"));
  process.exit(1);
}
console.log(`message keys ok in ${files.length} files`);
