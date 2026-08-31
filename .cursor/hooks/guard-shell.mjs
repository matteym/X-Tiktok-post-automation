import { stdin, stdout } from "node:process";

function reply(payload) {
  stdout.write(jsonString(payload));
}

function jsonString(value) {
  return JSON.stringify(value);
}

function deny(command, reason) {
  reply({
    permission: "deny",
    user_message: reason,
    agent_message: reason + ". command was: " + command,
  });
}

function allow() {
  reply({ permission: "allow" });
}

function looksLikeGit(command) {
  return /\bgit(\.exe)?\b/i.test(command);
}

let raw = "";
for await (const chunk of stdin) {
  raw += chunk;
}

let command = "";
try {
  const input = raw.trim() ? JSON.parse(raw) : {};
  command = String(input.command || "");
} catch {
  command = raw;
}

if (/\bterraform(\.exe)?\b/i.test(command) && /\b(apply|destroy)\b/i.test(command)) {
  deny(command, "terraform apply and destroy are blocked by project hooks");
  process.exit(0);
}

if (!looksLikeGit(command)) {
  allow();
  process.exit(0);
}

if (/\bpush\b/i.test(command)) {
  deny(command, "git push is blocked by project hooks");
  process.exit(0);
}

if (/--no-verify\b/i.test(command) || /--no-gpg-sign\b/i.test(command)) {
  deny(command, "git --no-verify is blocked by project hooks");
  process.exit(0);
}

if (/(^|[\s/\\])\.env(\s|$)/.test(command) || /[\s/\\]\.env\./.test(command)) {
  deny(command, "commands that mention .env are blocked by project hooks");
  process.exit(0);
}

allow();
