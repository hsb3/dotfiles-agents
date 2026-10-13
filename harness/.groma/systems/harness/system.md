---
type: C4 System
title: agent-harness
status: stable
groma:
  id: harness
description: Evaluation harness for coding-agent extenders
---
Measures whether a coding-agent extender, the **candidate**, makes a headless coding agent better at real tasks. The number that matters is the with − baseline pass-rate delta within one (campaign, harness, model) cell. Trials run each agent CLI under a throwaway per-run home so the owner's own configuration never leaks in; credentials reach a CLI only through environment variables. The ledger it writes is read later, in a separate step, by the evals loader.
