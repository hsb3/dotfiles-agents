#!/usr/bin/env bun
// The agent-harness binary: hands argv to the command dispatcher and exits with its code.
import { consoleIo, main } from "./commands.ts";

try {
  process.exitCode = await main(process.argv.slice(2), consoleIo);
} catch (e) {
  consoleIo.err(`agent-harness: ${e instanceof Error ? e.message : String(e)}`);
  process.exitCode = 1;
}
