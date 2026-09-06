#!/usr/bin/env python3
"""Find tasks whose status was silently reverted by an unattributed write.

On a GitHub-wired board, a task's status moves itself: push -> in-progress, PR ->
in-review, merge -> done. Those transitions are logged with `userId: null`, because no
human made them. That is normal and this script does not care about it.

What it looks for is the pathological case: an unattributed `status_changed` that puts a
task BACK to the status it just left, seconds after a real transition. The task then sits
in a lane nobody chose — a card reading `done` in its closing comment while the board
shows `up-next`. It self-heals on the next event, which is exactly why it is invisible
until someone goes looking.

The check is deliberately narrow: consecutive `status_changed` entries where the later
one is unattributed and its `newStatus` is the earlier one's `oldStatus`. A wider
heuristic (any unattributed write, any status disagreement) fires on every healthy
GitHub-driven board and gets ignored within a day.

`PATCH /task/bulk` logs `newStatus` only, with no `oldStatus` key (single-task
`PUT /task/status/{id}` logs both), so the missing value is reconstructed from the
preceding `status_changed`. Without that, every revert of a bulk write reads as a move
somewhere new and is dropped — which is why only non-bulk drift was ever reported. The
first `status_changed` in a trail has nothing to reconstruct from, so a revert of it
stays invisible.

Reports drift and exits 1 so a gate can consume it; a clean board exits 0.

Env: KANEO_API_URL, KANEO_API_KEY, KANEO_PROJECT_ID (or --project).
Stdlib only.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

# Two writes further apart than this are a person changing their mind, not a pipeline
# double-stepping. The worst observed real case flipped 8 times in 12 seconds.
DEFAULT_WINDOW_SECONDS = 120


def _get(api, key, path):
    request = urllib.request.Request(api + path, headers={"x-api-key": key})
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, None
    except urllib.error.URLError as e:
        raise RuntimeError("cannot reach {0}: {1}".format(api, e)) from e


def _parse_ts(value):
    """ISO-8601 with a trailing Z, which is what this API emits."""
    from datetime import datetime
    try:
        return datetime.fromisoformat((value or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def board_tasks(api, key, project):
    """(id, number, title, status) for every task in every column."""
    status, data = _get(api, key, "/task/tasks/{0}".format(project))
    if status != 200 or not data:
        raise RuntimeError("board read failed: HTTP {0}".format(status))
    payload = data.get("data", data)
    out = []
    for column in payload.get("columns", []):
        for task in column.get("tasks", []):
            out.append((task["id"], task.get("number"), task.get("title", ""),
                        column.get("slug")))
    return out


def reverts(activity, window_seconds=DEFAULT_WINDOW_SECONDS):
    """Unattributed status writes that undo the transition immediately before them.

    `activity` is the endpoint's own ordering (newest first); it is reversed here so the
    pairs read chronologically.
    """
    changes = [e for e in activity if e.get("type") == "status_changed"]
    changes = list(reversed(changes))
    # Bulk writes omit `oldStatus`; carry the previous event's `newStatus` in its place.
    prior_status, previous = [], None
    for event in changes:
        data = event.get("eventData") or {}
        prior_status.append(data.get("oldStatus") or previous)
        previous = data.get("newStatus")
    found = []
    for index, (earlier, later) in enumerate(zip(changes, changes[1:])):
        if later.get("userId") is not None:
            continue  # a person did it on purpose
        earlier_data = earlier.get("eventData") or {}
        later_data = later.get("eventData") or {}
        earlier_old = prior_status[index]
        if earlier_old is None or later_data.get("newStatus") != earlier_old:
            continue  # moved somewhere new, not back
        gap = None
        start, end = _parse_ts(earlier.get("createdAt")), _parse_ts(later.get("createdAt"))
        if start and end:
            gap = (end - start).total_seconds()
            if gap > window_seconds:
                continue
        found.append({
            "from": earlier_old,
            "to": earlier_data.get("newStatus"),
            "reverted_to": later_data.get("newStatus"),
            "at": later.get("createdAt"),
            "gap_seconds": gap,
        })
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", default=os.environ.get("KANEO_PROJECT_ID", ""))
    parser.add_argument("--window-seconds", type=int, default=DEFAULT_WINDOW_SECONDS)
    args = parser.parse_args(argv)

    api = os.environ.get("KANEO_API_URL", "").rstrip("/")
    key = os.environ.get("KANEO_API_KEY", "")
    if not api or not key or not args.project:
        print("KANEO_API_URL, KANEO_API_KEY and KANEO_PROJECT_ID (or --project) "
              "are all required", file=sys.stderr)
        return 2

    try:
        tasks = board_tasks(api, key, args.project)
    except RuntimeError as e:
        print("kaneo_status_drift: {0}".format(e), file=sys.stderr)
        return 2

    drifted = 0
    for task_id, number, title, current in tasks:
        status, activity = _get(api, key, "/activity/{0}".format(task_id))
        if status != 200 or not isinstance(activity, list):
            continue
        for hit in reverts(activity, args.window_seconds):
            drifted += 1
            gap = "" if hit["gap_seconds"] is None else " after {0:.0f}s".format(hit["gap_seconds"])
            print("#{0} {1}".format(number, title[:60]))
            print("   {0} -> {1}, then reverted to {2}{3} by an unattributed write".format(
                hit["from"], hit["to"], hit["reverted_to"], gap))
            print("   board shows: {0}".format(current))

    print("\n{0} task(s) scanned, {1} reverting write(s) found".format(len(tasks), drifted))
    return 1 if drifted else 0


if __name__ == "__main__":
    sys.exit(main())
