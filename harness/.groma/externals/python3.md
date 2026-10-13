---
type: C4 System
title: python3
description: Interpreter that runs each case's check.py
status: stable
groma:
  id: python3
  technology: Python 3
---

Runs `python3 <case dir>/check.py` in the final workspace; its stdout is a JSON array of `{id, passed, evidence}` checks.
