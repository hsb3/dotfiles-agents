"""Focused source contracts for the mounted performance area."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "evals/ui/src/performance.tsx").read_text() if (ROOT / "evals/ui/src/performance.tsx").exists() else ""
VIEWS = (ROOT / "evals/ui/src/views.tsx").read_text()
MAIN = (ROOT / "evals/ui/src/main.tsx").read_text()


class PerformanceUiContracts(unittest.TestCase):
    def test_performance_uses_the_authoritative_adapters_and_carbon_chart(self):
        self.assertIn('from "@carbon/charts-react"', SOURCE)
        self.assertIn("GroupedBarChart", SOURCE)
        self.assertIn("comparisonEligibility", SOURCE)
        self.assertIn("measurementNumber", SOURCE)
        self.assertIn("protectedFileToken", SOURCE)
        self.assertIn("evidenceForRun", SOURCE)
        self.assertIn("includeZero: true", SOURCE)

    def test_selection_and_route_state_are_explicit(self):
        self.assertIn("nextSelection", SOURCE)
        self.assertIn("slice(0, 2)", SOURCE)
        self.assertIn("assessmentsForCampaign", SOURCE)
        self.assertIn("responsePage", SOURCE)
        self.assertIn("eventPage", SOURCE)
        self.assertIn("recordScope(location.hash, \"run\")", SOURCE)
        self.assertIn("recordScope(location.hash, \"campaign\")", SOURCE)
        self.assertIn("#performance?${key}=", SOURCE)

    def test_shell_preserves_query_routes_and_skip_target(self):
        self.assertIn("export function parseRoute", VIEWS)
        self.assertIn("parseRoute(location.hash, current)", VIEWS)
        self.assertIn("<Performance session={session} onExpired={clearUi} />", VIEWS)
        self.assertIn("Your Toolbox", VIEWS)
        self.assertIn("Find tools for your workflow, read their documentation, and explore recorded performance and evaluations.", VIEWS)
        self.assertIn('import "@carbon/charts/styles.css"', MAIN)

    def test_route_parser_preserves_area_for_skip_link_and_selection_stays_capped(self):
        self.assertIn('if (hash === "#main-content") return fallback', VIEWS)
        self.assertIn("rows.some((row) => row.id === run.id)", SOURCE)
        self.assertNotIn('href={href("campaign", run.campaign)}', SOURCE)
        self.assertIn("measurementNumber(baseline, field)", SOURCE)
        self.assertIn("measurementNumber(withValue, field)", SOURCE)


if __name__ == "__main__":
    unittest.main()
