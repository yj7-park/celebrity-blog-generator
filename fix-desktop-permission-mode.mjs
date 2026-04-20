#!/usr/bin/env node

// Fix for Claude Desktop ignoring ~/.claude/settings.json permission config.
//
// Claude Desktop persists the permission mode in Electron Local Storage (LevelDB),
// then passes it as --permission-mode <value> to the Claude Code subprocess.
// This overrides settings.json's defaultMode. This script modifies the stored value.
//
// Usage:
//   node fix-desktop-permission-mode.mjs [mode]
//
// Supported modes: bypassPermissions, acceptEdits, auto, plan, default

import { ClassicLevel } from "classic-level";
import { join } from "path";
import { homedir } from "os";

const VALID_MODES = ["bypassPermissions", "acceptEdits", "auto", "plan", "default"];
const DB_PATH = join(homedir(), "Library", "Application Support", "Claude", "Local Storage", "leveldb");
const targetMode = process.argv[2] || "bypassPermissions";

if (!VALID_MODES.includes(targetMode)) {
  console.error(`Invalid mode: "${targetMode}". Valid: ${VALID_MODES.join(", ")}`);
  process.exit(1);
}

async function main() {
  let db;
  try {
    db = new ClassicLevel(DB_PATH, { keyEncoding: "buffer", valueEncoding: "buffer" });
    await db.open();
  } catch (err) {
    if (err.message?.includes("lock")) {
      console.error("Database is locked. Quit Claude Desktop (Cmd+Q) before running this.");
      process.exit(1);
    }
    throw err;
  }

  let updated = false;

  for await (const [key, value] of db.iterator()) {
    const keyStr = key.toString("utf8");
    if (!keyStr.includes("permission-mode")) continue;

    const valStr = value.toString("utf8");
    const prefix = valStr.startsWith("\x01") ? "\x01" : "";
    const jsonStr = prefix ? valStr.slice(1) : valStr;

    let parsed;
    try { parsed = JSON.parse(jsonStr); } catch { parsed = null; }

    const currentMode = parsed?.value ?? "(unreadable)";
    console.log(`${currentMode} → ${targetMode}`);

    const newValue = parsed && typeof parsed === "object"
      ? { ...parsed, value: targetMode, timestamp: Date.now() }
      : { value: targetMode, tabId: "", timestamp: Date.now() };

    await db.put(key, Buffer.from(prefix + JSON.stringify(newValue)));
    updated = true;
  }

  if (!updated) {
    // Create entry using Electron's localStorage key format
    const fullKey = Buffer.from("_https://claude.ai\x00\x01LSS-cc-landing-draft-permission-mode");
    const newValue = Buffer.from("\x01" + JSON.stringify({ value: targetMode, tabId: "", timestamp: Date.now() }));
    await db.put(fullKey, newValue);
    console.log(`(none) → ${targetMode}`);
  }

  await db.close();
  console.log(`Done. Open Claude Desktop — the permission dropdown should now show "${targetMode}".`);
}

main().catch((err) => { console.error(err.message); process.exit(1); });