---
type: C4 System
title: GitHub content hosts
status: stable
groma:
  id: github-content-hosts
  technology: HTTPS
---

GitHub's blob, tree and raw hosts (`github.com/<repo>/blob|tree/<ref>/…` and `raw.githubusercontent.com`). Links to files that are not pages, and images, are rewritten to point here; `site` never contacts them.
