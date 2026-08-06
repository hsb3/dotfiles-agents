# mermaid

Author Mermaid diagrams for GitHub-rendered markdown and technical docs — flowcharts, sequence
diagrams, ER diagrams, state diagrams, and class diagrams. Renders natively on GitHub, lives in
the markdown itself, and diffs like code, so it is the default choice for any diagram destined
for a `.md` file. Enforces the house rule that node labels carry no parentheses or special
characters, and covers light/dark theming plus local rendering to SVG/PNG.

## When it triggers

Use it whenever adding a diagram to a README, repo doc, PR description, or any markdown GitHub
renders, or when the user says mermaid, flowchart, sequence diagram, ERD, or state diagram.
Structural diagrams only — data charts belong to the `dataviz` skill, and provider-icon cloud
architecture belongs to the `diagrams` skill, which also hosts the tool selection guide.

## Install

```
claude plugin install diagrams@dotfiles-agents
```

Ships in the diagrams bundle (not standalone).
