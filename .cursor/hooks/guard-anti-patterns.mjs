import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");

const banned = [
  { re: /eslint-disable/, reason: "eslint-disable is forbidden" },
  { re: /@ts-ignore/, reason: "@ts-ignore is forbidden" },
  { re: /@ts-nocheck/, reason: "@ts-nocheck is forbidden" },
  { re: /--no-verify/, reason: "--no-verify is forbidden" },
  { re: /terraform\s+apply\b/, reason: "terraform apply is forbidden" },
  { re: /terraform\s+destroy\b/, reason: "terraform destroy is forbidden" },
  { re: /sentry\.io/, reason: "sentry.io host is forbidden" },
  { re: /\bCountly\b/i, reason: "Countly is forbidden" },
  { re: /\bit\.skip\s*\(/, reason: "it.skip is forbidden in new diff" },
  { re: /\bdescribe\.skip\s*\(/, reason: "describe.skip is forbidden in new diff" },
  { re: /\bxtest\s*\(/, reason: "xtest is forbidden in new diff" },
  { re: /\bxit\s*\(/, reason: "xit is forbidden in new diff" },
  { re: /\bas any\b/, reason: "as any is forbidden in new diff" },
  { re: /:\s*any\b/, reason: ": any is forbidden in new diff" },
  { re: /fallback-secret/, reason: "jwt fallback-secret is forbidden in new diff" },
];

const localhostUrlRe = /https?:\/\/(localhost|127\.0\.0\.1)/i;

function normalizePath(file) {
  return file.replace(/\\/g, "/").replace(/^\.\//, "");
}

function pathAllowlisted(file) {
  const p = normalizePath(file);
  if (p.startsWith("Server/tests/e2e/")) {
    return true;
  }
  if (/(^|\/)conftest\.py$/.test(p)) {
    return true;
  }
  if (p === ".env.example" || p.endsWith("/.env.example")) {
    return true;
  }
  if (p === "docker-compose.yml" || p.endsWith("/docker-compose.yml")) {
    return true;
  }
  if (p === "docker-compose.env.example" || p.endsWith("/docker-compose.env.example")) {
    return true;
  }
  if (/(^|\/)[^/]*prometheus[^/]*\.ya?ml$/.test(p)) {
    return true;
  }
  if (p.startsWith(".cursor/")) {
    return true;
  }
  if (p.startsWith("dag/")) {
    return true;
  }
  if (p.endsWith(".md") || p.endsWith(".mdc")) {
    return true;
  }
  if (p === "Server/schema.sql" || p.endsWith("/schema.sql")) {
    return true;
  }
  return false;
}

function parseAddedByFile(diff) {
  const files = [];
  let current = null;
  for (const raw of diff.split(/\r?\n/)) {
    const plusFile = raw.match(/^\+\+\+ b\/(.+)$/);
    if (plusFile) {
      current = { file: plusFile[1], lines: [] };
      files.push(current);
      continue;
    }
    if (raw.startsWith("+++ ") && raw.includes("/dev/null")) {
      current = null;
      continue;
    }
    if (!current) {
      continue;
    }
    if (raw.startsWith("+++") || raw.startsWith("---")) {
      continue;
    }
    if (raw.startsWith("+")) {
      current.lines.push(raw.slice(1));
    }
  }
  return files;
}

const diff = spawnSync("git", ["diff", "HEAD"], {
  cwd: repoRoot,
  encoding: "utf8",
});

if (diff.status !== 0 && diff.status !== null) {
  process.stderr.write("guard-anti-patterns: git diff failed\n");
  process.exit(1);
}

const text = diff.stdout || "";
const hits = [];
for (const { file, lines } of parseAddedByFile(text)) {
  if (pathAllowlisted(file)) {
    continue;
  }
  for (const line of lines) {
    for (const rule of banned) {
      if (rule.re.test(line)) {
        hits.push(file + ": " + rule.reason + ": " + line.trim().slice(0, 160));
      }
    }
    if (localhostUrlRe.test(line)) {
      hits.push(
        file +
          ": hardcoded localhost url is forbidden, use environment variables: " +
          line.trim().slice(0, 160)
      );
    }
  }
}

if (hits.length) {
  process.stderr.write(hits.join("\n") + "\n");
  process.exit(1);
}

process.exit(0);
