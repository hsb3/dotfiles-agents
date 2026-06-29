# Community Plugin Review Requirements

Complete reference for Obsidian's community plugin review process. The automated review bot checks submissions against these rules. Violations result in auto-rejection.

## Auto-Reject Rules

These violations are detected automatically and will reject your plugin immediately.

### Rule 1: No innerHTML / outerHTML / insertAdjacentHTML

**Severity:** Auto-reject
**Detection:** Static analysis of bundled `main.js`

The review bot scans for any occurrence of `innerHTML`, `outerHTML`, or `insertAdjacentHTML` in your bundled output. This includes usage in your own code and in any bundled dependencies.

```typescript
// All of these trigger auto-reject:
element.innerHTML = '<div>text</div>';
element.outerHTML = '<span>new</span>';
element.insertAdjacentHTML('beforeend', '<p>text</p>');

// Template literals also trigger:
element.innerHTML = `<div>${variable}</div>`;

// Even empty assignments trigger:
element.innerHTML = '';
```

**Required alternative:** Use Obsidian's `createEl`, `createDiv`, `createSpan` helpers. To clear an element, use `element.empty()` instead of `element.innerHTML = ''`.

**Dependency trap:** If a bundled dependency uses innerHTML internally, your plugin will still be rejected. Audit dependencies or find alternatives that use DOM APIs directly.

### Rule 2: Restricted Console Methods

**Severity:** Auto-reject
**Detection:** Static analysis for `console.log` and `console.info`

Only three console methods are permitted:

| Method | Status | Use Case |
|--------|--------|----------|
| `console.debug()` | Allowed | Development logging, verbose info |
| `console.warn()` | Allowed | Non-critical warnings |
| `console.error()` | Allowed | Error reporting |
| `console.log()` | Forbidden | Replace with `console.debug()` |
| `console.info()` | Forbidden | Replace with `console.debug()` |
| `console.trace()` | Forbidden | Not allowed |

**Dependency trap:** Bundled dependencies that use `console.log` will also trigger rejection. Use esbuild's `drop` option or a find-and-replace build step to strip them.

```javascript
// esbuild config to drop console.log from dependencies
esbuild.build({
  // ...
  drop: ['debugger'],
  // For fine-grained control, use a plugin:
  plugins: [{
    name: 'strip-console-log',
    setup(build) {
      build.onLoad({ filter: /\.js$/ }, async (args) => {
        const source = await require('fs').promises.readFile(args.path, 'utf8');
        return {
          contents: source.replace(/console\.log\(/g, 'console.debug('),
          loader: 'js'
        };
      });
    }
  }]
});
```

### Rule 3: Unhandled Promises

**Severity:** Auto-reject
**Detection:** Static analysis for floating promise expressions

Every promise must be explicitly handled. The bot looks for async function calls without `await`, `void`, `.catch()`, or `.then()` with a rejection handler.

```typescript
// Triggers rejection - floating promise:
this.loadData();
this.saveData(data);
someAsyncFunction();

// Acceptable forms:
await this.loadData();
void this.saveData(data);
someAsyncFunction().catch(e => console.error(e));
someAsyncFunction().then(handler, rejectionHandler);
```

### Rule 4: Command ID Must Not Include Plugin ID

**Severity:** Auto-reject
**Detection:** Static analysis of `addCommand` calls

Obsidian automatically namespaces command IDs with your plugin ID. Including it yourself creates a double prefix.

```typescript
// Rejected - double namespacing:
this.addCommand({ id: 'my-plugin:do-thing', name: 'Do thing' });
this.addCommand({ id: 'my-plugin-do-thing', name: 'Do thing' });

// Accepted:
this.addCommand({ id: 'do-thing', name: 'Do thing' });
```

### Rule 5: Async Functions Must Contain Await

**Severity:** Auto-reject
**Detection:** Static analysis for async functions without await expressions

If a function is marked `async`, it must contain at least one `await` expression. Otherwise, remove the `async` keyword.

```typescript
// Rejected - unnecessary async:
async getName(): Promise<string> {
  return this.name;
}

// Accepted:
getName(): string {
  return this.name;
}

// Accepted - has await:
async getName(): Promise<string> {
  const data = await this.loadData();
  return data.name;
}
```

### Rule 6: UI Text Must Use Sentence Case

**Severity:** Auto-reject (or manual review flag)
**Detection:** Pattern matching on command names and UI strings

All user-facing text must use sentence case. Only capitalize the first word and proper nouns.

```typescript
// Rejected:
name: 'Open Chat View'
name: 'Show Plugin Settings'
name: 'Import From File'

// Accepted:
name: 'Open chat view'
name: 'Show plugin settings'
name: 'Import from file'
```

## Manual Review Flags

These issues may not auto-reject but will be flagged for manual reviewer attention.

### Memory Leaks

Reviewers check for proper cleanup patterns:

```typescript
// Flagged - manual event management:
window.addEventListener('resize', this.handleResize);
document.addEventListener('keydown', this.handleKey);

// Preferred - auto-cleanup:
this.registerDomEvent(window, 'resize', this.handleResize);
this.registerDomEvent(document, 'keydown', this.handleKey);

// Flagged - manual interval:
setInterval(() => this.poll(), 5000);

// Preferred - auto-cleanup:
this.registerInterval(window.setInterval(() => this.poll(), 5000));
```

### Network Requests

Reviewers check that network requests are appropriate:

- Requests must be relevant to plugin functionality
- No analytics or tracking without user consent
- No requests to unexpected domains
- API keys should come from user settings, never hardcoded

### File System Access

Reviewers verify file operations stay within the vault:

- Use Obsidian's Vault API, not Node.js `fs` directly (when possible)
- Never write outside the vault directory
- Destructive operations should require user confirmation

### Excessive Permissions

Reviewers flag plugins that request more access than needed:

- Don't register for all workspace events when you only need one
- Don't read all files when you only need specific ones
- Don't modify files you don't need to change

## Build Requirements

### External Modules

Only two modules may be marked as external:

```javascript
external: ['obsidian', 'electron']
```

Everything else must be bundled. The review bot checks that `main.js` is self-contained.

### Output Format

- Format: CommonJS (`format: 'cjs'`)
- Single output file: `main.js`
- Platform: `node` (Obsidian runs in Electron)
- Target: `es2018` or later

### Required Files

Your plugin repository must contain:

| File | Required | Purpose |
|------|----------|---------|
| `main.js` | Yes | Bundled plugin code |
| `manifest.json` | Yes | Plugin metadata |
| `styles.css` | No | Plugin styles |
| `package.json` | Yes | Node.js project file |

### manifest.json Requirements

```json
{
  "id": "my-plugin-id",
  "name": "My Plugin Name",
  "version": "1.0.0",
  "minAppVersion": "0.15.0",
  "description": "A clear, concise description",
  "author": "Your Name",
  "authorUrl": "https://github.com/yourusername",
  "isDesktopOnly": false
}
```

- `id` must match the directory name in the community plugins repo
- `version` must follow semver
- `minAppVersion` should be the minimum Obsidian version your plugin supports
- `isDesktopOnly` should be `true` only if you use Node.js APIs (http, fs, etc.)

## Pre-Submission Checklist

Run through this checklist before submitting your plugin:

### Code Quality
- [ ] Zero `innerHTML` / `outerHTML` / `insertAdjacentHTML` in bundled output
- [ ] Zero `console.log` / `console.info` / `console.trace` in bundled output
- [ ] All promises handled (await / void / catch / then with rejection)
- [ ] Command IDs do not include plugin ID prefix
- [ ] All async functions contain at least one await
- [ ] Sentence case for all UI-facing text
- [ ] All event listeners use `registerEvent` / `registerDomEvent` / `registerInterval`
- [ ] No memory leaks from unmanaged listeners or timers

### Build
- [ ] Only `obsidian` and `electron` are external
- [ ] Output is CommonJS format
- [ ] `main.js` bundles correctly
- [ ] No `node_modules/` committed
- [ ] No `main.js` committed (generated artifact)

### Repository
- [ ] `manifest.json` is valid and complete
- [ ] `package.json` exists
- [ ] Version numbers are consistent across manifest and package.json
- [ ] README explains what the plugin does and how to use it

### Testing
- [ ] Plugin loads without errors in a fresh vault
- [ ] Plugin unloads cleanly (no orphaned listeners, servers, or UI)
- [ ] Commands appear in command palette
- [ ] Settings save and load correctly
- [ ] No errors in developer console

## Validation Script

Run this before submission to catch common issues:

```bash
#!/bin/bash
# validate-plugin.sh - Run from plugin root directory

echo "=== Obsidian Plugin Validation ==="
errors=0

# Build first
npm run build 2>/dev/null

# Check for innerHTML in bundled output
if grep -q "innerHTML\|outerHTML\|insertAdjacentHTML" main.js 2>/dev/null; then
  echo "FAIL: innerHTML/outerHTML found in main.js"
  grep -n "innerHTML\|outerHTML\|insertAdjacentHTML" main.js
  errors=$((errors + 1))
fi

# Check for forbidden console methods
if grep -q "console\.log\|console\.info\|console\.trace" main.js 2>/dev/null; then
  echo "FAIL: Forbidden console methods in main.js"
  grep -n "console\.log\|console\.info\|console\.trace" main.js
  errors=$((errors + 1))
fi

# Check manifest exists
if [ ! -f manifest.json ]; then
  echo "FAIL: manifest.json not found"
  errors=$((errors + 1))
fi

# Check manifest has required fields
if [ -f manifest.json ]; then
  for field in id name version minAppVersion description author; do
    if ! grep -q "\"$field\"" manifest.json; then
      echo "FAIL: manifest.json missing '$field'"
      errors=$((errors + 1))
    fi
  done
fi

# Check for main.js in git
if git ls-files --error-unmatch main.js 2>/dev/null; then
  echo "WARN: main.js is tracked by git (should be in .gitignore)"
fi

# Check for node_modules in git
if git ls-files --error-unmatch node_modules 2>/dev/null; then
  echo "FAIL: node_modules is tracked by git"
  errors=$((errors + 1))
fi

# Summary
echo ""
if [ $errors -eq 0 ]; then
  echo "PASS: All checks passed"
else
  echo "FAIL: $errors issue(s) found"
  exit 1
fi
```
