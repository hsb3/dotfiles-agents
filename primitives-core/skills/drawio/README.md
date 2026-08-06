# drawio

Read, convert, and export draw.io / diagrams.net files without the GUI — decompress legacy
`.drawio` XML, extract its node/edge structure, and headlessly export to PNG/SVG from the
command line. Buys a path off unmaintained archive files toward diffable, maintainable sources.

## When it triggers

Use it when a `.drawio`, `.drawio.png`, or `.drawio.svg` file needs inspecting, converting to
Mermaid or another format, or exporting from the command line, or when the user asks about
drawio, diagrams.net, or mxGraph XML. It owns the format and export mechanics only; which tool
a *new* diagram should use is decided by the selection guide in the `diagrams` skill — new
repo-doc diagrams are usually Mermaid, not draw.io.

## Install

```
claude plugin install diagrams@dotfiles-agents
```

Ships in the diagrams bundle (not standalone).
