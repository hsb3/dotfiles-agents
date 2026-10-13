#!/usr/bin/env bun
import { run } from "./commands.ts";

process.exitCode = await run(Bun.argv.slice(2));
