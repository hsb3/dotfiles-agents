/// <reference path="../pb_data/types.d.ts" />
// GET /api/toolbox/catalog: the packaged catalog for any authenticated request
// (users or superusers); 401 otherwise. The catalog file sits beside this hook,
// outside pb_public, so it is never served as a static file.

routerAdd(
  "GET",
  "/api/toolbox/catalog",
  (e) => {
    const raw = toString($os.readFile(__hooks + "/toolbox-catalog.json"));
    return e.json(200, JSON.parse(raw));
  },
  $apis.requireAuth(),
);
