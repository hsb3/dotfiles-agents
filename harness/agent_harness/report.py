"""Aggregation + report.

Extended from the workbench: cells are now **per (harness, model, case, config)**
and deltas are computed **within a (harness, model) cell** (DESIGN §3/§4), so the
cross-harness / cross-model grid reports each cell separately and a with-vs-baseline
delta never mixes harnesses. Rows with ``passed is None`` (unsupported/skip) are
excluded from pass statistics but surfaced by the run loop as explicit skip rows.
"""

from __future__ import annotations

import statistics


def _mean(xs):
    return round(statistics.mean(xs), 4) if xs else None


def _stdev(xs):
    return round(statistics.stdev(xs), 4) if len(xs) > 1 else 0.0 if xs else None


def summarize(rows):
    """Per-(campaign, harness, model, case, config) stats: n, pass_rate, pass@n,
    pass^n, cost, dur. ``campaign`` (default "") is part of the cell key so a
    labeled re-run never merges with pre-fix rows for the same cell (#171)."""
    groups = {}
    for r in rows:
        if r.get("passed") is None:  # unsupported/skip rows carry no pass signal
            continue
        key = (r.get("campaign", ""), r.get("harness"), r.get("model"), r["case"], r["config"])
        groups.setdefault(key, []).append(r)
    out = {}
    for key in sorted(groups, key=lambda k: tuple("" if x is None else str(x) for x in k)):
        rs = groups[key]
        passes = [bool(r.get("passed")) for r in rs]
        costs = [
            r["cost_usd"] for r in rs if isinstance(r.get("cost_usd"), (int, float))
        ]
        durs = [
            r["duration_ms"]
            for r in rs
            if isinstance(r.get("duration_ms"), (int, float))
        ]
        out[key] = {
            "n": len(rs),
            "pass_rate": round(sum(passes) / len(passes), 4),
            "pass_any": any(passes),
            "pass_all": all(passes),
            "cost_mean": _mean(costs),
            "cost_stdev": _stdev(costs),
            "duration_mean": _mean(durs),
            "duration_stdev": _stdev(durs),
        }
    return out


def deltas(summary):
    """with-vs-baseline pass-rate delta per (campaign, harness, model, case).

    Positive = candidate helps. Compared only within one (campaign, harness,
    model) cell, so with/baseline must share a campaign to form a delta.
    """
    out = {}
    for campaign, harness, model, case, config in summary:
        if config == "with" and (campaign, harness, model, case, "baseline") in summary:
            out[(campaign, harness, model, case)] = round(
                summary[(campaign, harness, model, case, "with")]["pass_rate"]
                - summary[(campaign, harness, model, case, "baseline")]["pass_rate"],
                4,
            )
    return out


def print_report(candidate, rows):
    """Human-readable per-cell report for one candidate."""
    if not rows:
        print(f"no result rows for {candidate}")
        return
    summary = summarize(rows)
    skipped = [r for r in rows if r.get("passed") is None]
    if not summary:
        print(f"\n{candidate} — {len(rows)} row(s), none with a pass signal")
    else:
        show_campaign = any(camp for camp, _h, _m, _c2, _c in summary)
        cw = max(20, max(len(case) for _ca, _h, _m, case, _c in summary))
        mw = max(8, max(len(str(m)) for _ca, _h, m, _c2, _c in summary))
        hw = max(7, max(len(str(h)) for _ca, h, _m, _c2, _c in summary))
        gw = max(8, max(len(str(ca)) for ca, _h, _m, _c2, _c in summary)) if show_campaign else 0
        print(f"\n{candidate} — {len(rows)} trial row(s)")
        camp_hdr = f"{'campaign':<{gw}} " if show_campaign else ""
        hdr = (
            f"{camp_hdr}{'harness':<{hw}} {'model':<{mw}} {'case':<{cw}} {'config':<9} "
            f"{'n':>2} {'pass':>6} {'p@n':>4} {'p^n':>4} {'cost μ±σ':>14} {'ms μ±σ':>16}"
        )
        print(hdr)
        print("-" * len(hdr))
        for (campaign, harness, model, case, config), s in summary.items():
            cost = (
                f"{s['cost_mean']}±{s['cost_stdev']}"
                if s["cost_mean"] is not None
                else "-"
            )
            dur = (
                f"{s['duration_mean']}±{s['duration_stdev']}"
                if s["duration_mean"] is not None
                else "-"
            )
            camp_col = f"{str(campaign):<{gw}} " if show_campaign else ""
            print(
                f"{camp_col}{str(harness):<{hw}} {str(model):<{mw}} {case:<{cw}} {config:<9} "
                f"{s['n']:>2} {s['pass_rate']:>6} "
                f"{'Y' if s['pass_any'] else 'n':>4} {'Y' if s['pass_all'] else 'n':>4} "
                f"{cost:>14} {dur:>16}"
            )
        for (campaign, harness, model, case), delta in deltas(summary).items():
            tag = f"{campaign}/" if campaign else ""
            print(f"delta (with - baseline) [{tag}{harness}/{model}] {case}: {delta:+}")
    if skipped:
        print(f"\n{len(skipped)} unsupported/skip row(s):")
        for r in skipped:
            camp = r.get("campaign", "")
            prefix = f"[{camp}] " if camp else ""
            print(
                f"  ∅ {prefix}{r.get('harness')}/{r.get('model')} {r['case']} "
                f"{r['config']}: {r.get('error')}"
            )
