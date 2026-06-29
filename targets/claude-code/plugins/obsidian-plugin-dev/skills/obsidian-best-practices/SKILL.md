---
name: obsidian-best-practices
description: This skill should be used when the user asks about "community plugin review", "plugin approval", "common mistakes", "gotchas", "console.log", "promise handling", or mentions Obsidian plugin review requirements and validation.
---

# Obsidian Best Practices

Provides guidance on community plugin review requirements, common gotchas, and best practices for Obsidian plugin development. Following these rules is **essential for plugin approval**.

## Community Review Requirements

Obsidian's automated review bot enforces strict rules. Violations will **auto-reject** your plugin.

### 1. Never Use innerHTML

**Auto-reject violation #1:**

```typescript
// ❌ FORBIDDEN
el.innerHTML = '<div>content</div>';
el.outerHTML = '<span>text</span>';
el.insertAdjacentHTML('beforeend', '<p>text</p>');

// ✅ REQUIRED
el.createDiv({ text: 'content' });
el.createEl('span', { text: 'text' });
```

**No exceptions.** Use Obsidian's `createEl` helpers exclusively.

### 2. Console Methods Restrictions

Only specific console methods are allowed:

```typescript
// ✅ ALLOWED
console.warn('Warning message');
console.error('Error message');
console.debug('Debug info');

// ❌ FORBIDDEN
console.log('Info message');  // Use console.debug instead
console.info('Info');          // Use console.debug instead
console.trace('Trace');        // Not allowed
```

**Rule:** Use `console.debug` instead of `console.log`.

### 3. Promise Handling Required

All promises **must** be handled:

```typescript
// ❌ WRONG - Floating promise
this.performAsync();

// ✅ CORRECT - Explicitly handled
await this.performAsync();

// ✅ CORRECT - Explicitly voided
void this.performAsync();

// ✅ CORRECT - Caught
this.performAsync().catch(e => console.error(e));

// ✅ CORRECT - With then + rejection handler
this.performAsync().then(
  result => this.handleResult(result),
  error => console.error(error)
);
```

**Rule:** Every promise must be awaited, caught, voided, or have rejection handler.

### 4. Command ID Conventions

Command IDs must **not** include the plugin ID:

```typescript
// ❌ WRONG
this.addCommand({
  id: 'my-plugin:open-view',  // Don't include plugin ID
  name: 'Open view'
});

// ✅ CORRECT
this.addCommand({
  id: 'open-view',  // Obsidian namespaces automatically
  name: 'Open view'
});
```

**Obsidian automatically namespaces** commands with your plugin ID.

### 5. UI Text Conventions

Use sentence case, not Title Case:

```typescript
// ❌ WRONG
name: 'Open Chat View'

// ✅ CORRECT
name: 'Open chat view'
```

**Rule:** Only capitalize first word (except proper nouns).

### 6. Async Method Requirements

If a method is marked `async`, it **must** contain at least one `await`:

```typescript
// ❌ WRONG - async with no await
async myMethod() {
  return this.value;
}

// ✅ CORRECT - Remove async
myMethod() {
  return this.value;
}

// ✅ CORRECT - Has await
async myMethod() {
  await this.loadData();
  return this.value;
}
```

### 7. Lifecycle and Memory Management

Never use the main plugin instance as a Component:

```typescript
// ❌ WRONG - Memory leak risk
this.registerDomEvent(window, 'click', () => {});

// ✅ CORRECT - Use register helpers
this.registerEvent(
  this.app.workspace.on('active-leaf-change', () => {})
);

this.registerInterval(
  window.setInterval(() => {}, 5000)
);
```

**Register helpers auto-cleanup** on plugin unload.

## Common Gotchas

### metadataCache Timing

After writing a file, `metadataCache` may not update immediately:

```typescript
await this.app.vault.modify(file, newContent);

// ❌ Cache might be stale here
const cache = this.app.metadataCache.getFileCache(file);

// ✅ Wait for update
await new Promise(resolve => setTimeout(resolve, 100));

// ✅ Or listen for event
this.app.metadataCache.on('changed', (changedFile) => {
  if (changedFile.path === file.path) {
    // Cache updated
  }
});
```

### Port Binding Conflicts

When running HTTP servers (for MCP):

```typescript
try {
  this.httpServer = http.createServer(...);
  this.httpServer.listen(port, '127.0.0.1');
} catch (error) {
  console.error(`Port ${port} in use`);
  // Try fallback ports or notify user
}
```

**Best practice:** Make port configurable with fallback range.

### Electron Environment

Obsidian runs in Electron, which provides Node.js APIs:

```typescript
// ✅ Available - Full Node.js APIs
import { createServer } from 'http';
import { readFileSync } from 'fs';

// ❌ Not available - Browser-only APIs
const sse = new EventSource(url);  // Use fetch() instead
```

**Use Node.js APIs**, not browser-only features.

### Build Configuration

Must bundle ALL dependencies except `obsidian` and `electron`:

```javascript
// esbuild.config.mjs
export default {
  entryPoints: ['src/main.ts'],
  bundle: true,
  external: [
    'obsidian',  // Provided by Obsidian
    'electron',  // Provided by Electron
    // All other deps MUST be bundled
  ],
  format: 'cjs',  // Must be CommonJS
  platform: 'node',
  outfile: 'main.js',
};
```

### Git Ignore Rules

Never commit generated files:

```gitignore
# Build outputs
main.js
*.js.map

# Dependencies
node_modules/

# OS files
.DS_Store

# Development
.env
.vscode/
```

## File Structure Best Practices

Keep `main.ts` lean:

```
src/
  main.ts           # <100 lines - lifecycle only
  settings.ts       # Settings interface and tab
  constants.ts      # Constants, type IDs
  api/              # External API clients
  mcp/              # MCP server modules
  ui/               # UI components
  commands/         # Command implementations
```

**Rule:** Split files >200-300 lines into focused modules.

## TypeScript Configuration

Recommended `tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2018",
    "module": "ESNext",
    "lib": ["ES2018", "DOM"],
    "moduleResolution": "node",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "skipLibCheck": true
  },
  "include": ["src/**/*.ts"]
}
```

## Release Checklist

Before submitting for review:

**Code Quality:**
- [ ] No `innerHTML`, `outerHTML`, `insertAdjacentHTML`
- [ ] Only allowed console methods (warn, error, debug)
- [ ] All promises handled (await/void/catch)
- [ ] Command IDs exclude plugin ID
- [ ] Sentence case for all UI text
- [ ] Async methods contain await
- [ ] Using `register*` helpers for cleanup

**Build:**
- [ ] All dependencies bundled (except obsidian/electron)
- [ ] `main.js` outputs correctly
- [ ] `manifest.json` valid
- [ ] No generated files committed

**Testing:**
- [ ] Tested in Obsidian sandbox vault
- [ ] No console errors
- [ ] Commands work correctly
- [ ] Settings persist
- [ ] Cleanup on disable/unload

**Documentation:**
- [ ] README with installation and usage
- [ ] CHANGELOG for version history
- [ ] LICENSE file (usually MIT)

## Validation Tools

### Manual Checks

```bash
# Check for innerHTML
grep -r "innerHTML" src/

# Check for console.log
grep -r "console\.log" src/

# Check for floating promises
# Review async calls without await/void/catch
```

### Automated Validation

Create a validation script:

```bash
#!/bin/bash
# validate.sh

errors=0

if grep -r "innerHTML\|outerHTML" src/; then
  echo "❌ Found innerHTML usage"
  errors=$((errors + 1))
fi

if grep -r "console\.log" src/; then
  echo "❌ Found console.log"
  errors=$((errors + 1))
fi

if [ $errors -eq 0 ]; then
  echo "✅ Validation passed"
else
  echo "❌ $errors validation errors"
  exit 1
fi
```

## Common Rejection Reasons

### 1. innerHTML Violations

Most common rejection. Search your entire codebase.

### 2. Unhandled Promises

Review all `async` calls without `await`, `void`, or `catch`.

### 3. Console Methods

Replace `console.log` with `console.debug`.

### 4. Command Naming

Remove plugin ID from command IDs.

### 5. Memory Leaks

Use `register*` helpers, not manual event management.

## Additional Resources

### Reference Files

For detailed patterns:
- **`references/review-requirements.md`** - Complete review checklist
- **`references/common-violations.md`** - Examples of failures

### Official Resources

- [Plugin Guidelines](https://docs.obsidian.md/Plugins/Releasing/Plugin+guidelines)
- [Submit Plugin](https://docs.obsidian.md/Plugins/Releasing/Submit+your+plugin)
- [Sample Plugin](https://github.com/obsidianmd/obsidian-sample-plugin)

## Quick Reference

| Rule | ❌ Wrong | ✅ Correct |
|------|----------|-----------|
| DOM | `innerHTML` | `createEl()` |
| Console | `console.log()` | `console.debug()` |
| Promises | `this.async()` | `await this.async()` |
| Commands | `plugin:cmd` | `cmd` |
| Text | `Open View` | `Open view` |
| Async | No await | Has await |
| Events | Manual | `register*()` |

Follow these rules to ensure smooth community plugin approval.
