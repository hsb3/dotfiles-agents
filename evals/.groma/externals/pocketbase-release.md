---
type: C4 System
title: PocketBase release
description: The pinned PocketBase 0.40.3 binary the image build downloads
status: stable
groma:
  id: pocketbase-release
  technology: GitHub release download
---

The Dockerfile downloads `pocketbase_0.40.3_linux_<arch>.zip` from github.com and checks its SHA-256 before installing it in the image.
