/// <reference path="../pb_data/types.d.ts" />

routerAdd(
  "GET",
  "/api/toolbox/catalog",
  (e) => e.json(200, JSON.parse($os.readFile($os.getenv("PB_CATALOG_PATH") || "/pb/pb_catalog/toolbox-catalog.json"))),
  $apis.requireAuth(),
)
