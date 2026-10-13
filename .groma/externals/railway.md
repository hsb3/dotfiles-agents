---
type: C4 System
title: Railway
description: Hosts the deployed PocketBase service and its data volume
status: stable
groma:
  id: railway
  technology: PaaS with a volume
---

Builds the deploy package with its Dockerfile, mounts the volume at `/pb/pb_data` and runs `start.sh`. The owner deploys with `railway up`; evals never deploys.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [railway](railway.md) | [pocketbase-release](pocketbase-release.md) | Downloads the PocketBase binary | HTTPS, SHA-256 checked |
| [railway](railway.md) | [pocketbase-service](../systems/evals/containers/pocketbase-service/container.md) | Hosts the service | Docker image, volume at /pb/pb_data |
