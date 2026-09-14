/// <reference path="../pb_data/types.d.ts" />

routerAdd(
  "GET",
  "/api/toolbox/catalog",
  (e) => e.json(200, JSON.parse(String.fromCharCode.apply(
    null, $os.readFile(`${__hooks}/toolbox-catalog.json`),
  ))),
  $apis.requireAuth(),
)
