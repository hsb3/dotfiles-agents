---
type: C4 System
title: Cases directory
description: External eval cases, read but not owned
status: stable
groma:
  id: cases-directory
  technology: directory of case.json, fixture/ and check.py
---

Real cases live with the primitives they test and arrive through `--cases-dir`, laid out as `<candidate>/<case-id>/case.json` with an optional `fixture/` and `check.py`.
