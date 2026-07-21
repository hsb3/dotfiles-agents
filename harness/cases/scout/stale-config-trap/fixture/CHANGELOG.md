# Changelog

## v1.3

- Bumped `REQUEST_TIMEOUT_SECONDS` after the payments backend's p99 regressed;
  see `src/config.py` for the current value.

## v1.2

- Migrated settings from `src/legacy/settings.py` into `src/config.py`.
  `src/legacy/settings.py` is kept for the v1.1 migration script only.

## v1.1

- Initial release with `src/legacy/settings.py`.
