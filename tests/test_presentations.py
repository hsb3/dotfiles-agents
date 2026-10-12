"""Package edits must preserve notes/chart bytes and reject broken input before output."""
import importlib.util
import json
import os
import posixpath
import shutil
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import zlib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'primitives-core/skills/presentations/scripts'


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


pptx = module('pptx', 'pptx.py')
creator = module('create_deck', 'create-deck.py')
renderer = module('render_deck', 'render.py')


def fixture():
    p, a, r = pptx.P, pptx.A, pptx.R
    def rels(items):
        return ('<Relationships xmlns="' + pptx.REL + '">' + ''.join(
            f'<Relationship Id="{id}" Type="{r}/{kind}" Target="{dest}"/>' for id, kind, dest in items) + '</Relationships>').encode()
    parts = {
        '[Content_Types].xml': f'<Types xmlns="{pptx.CT}"><Default Extension="xml" ContentType="application/xml"/><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/></Types>'.encode(),
        '_rels/.rels': rels([('r1', 'officeDocument', 'ppt/presentation.xml')]),
        'ppt/presentation.xml': f'<p:presentation xmlns:p="{p}" xmlns:r="{r}"><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="master"/></p:sldMasterIdLst><p:sldIdLst><p:sldId id="256" r:id="s1"/><p:sldId id="257" r:id="s2"/></p:sldIdLst><p:sldSz cx="12192000" cy="6858000"/></p:presentation>'.encode(),
        'ppt/_rels/presentation.xml.rels': rels([('s1', 'slide', 'slides/slide1.xml'), ('s2', 'slide', 'slides/slide2.xml'), ('master', 'slideMaster', 'slideMasters/master.xml')]),
        'ppt/slideMasters/master.xml': f'<p:sldMaster xmlns:p="{p}"/>'.encode(),
        'ppt/slides/slide1.xml': f'<p:sld xmlns:p="{p}" xmlns:a="{a}" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main" mc:Ignorable="p14"><p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>Old </a:t></a:r><a:r><a:t>title</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>'.encode(),
        'ppt/slides/slide2.xml': f'<p:sld xmlns:p="{p}" xmlns:a="{a}"><p:cSld><a:p><a:r><a:t>Second</a:t></a:r></a:p></p:cSld></p:sld>'.encode(),
        'ppt/slides/_rels/slide1.xml.rels': rels([('n1', 'notesSlide', '../notesSlides/notes1.xml'), ('c1', 'chart', '../charts/chart1.xml')]),
        'ppt/notesSlides/notes1.xml': f'<p:notes xmlns:p="{p}" xmlns:a="{a}"><a:t>Keep these notes</a:t></p:notes>'.encode(),
        'ppt/charts/chart1.xml': '<chart><value>42</value></chart>'.encode(),
    }
    return parts


PNG_SIG = b'\x89PNG\r\n\x1a\n'


def png(w, h):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    return (PNG_SIG + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 0, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\x00\x00')) + chunk(b'IEND', b''))


def geometry_findings(path, counts=None):
    """Distortion, box-overflow and negative-extent findings for a .pptx; counts is filled if given."""
    counts = {} if counts is None else counts
    counts.update(pictures=0, boxed=0, extents=0, lines=0)
    findings = []
    P, A, R = pptx.P, pptx.A, pptx.R
    with zipfile.ZipFile(path) as z:  # not pptx.load: hand-built fixtures lack a full OPC skeleton
        parts = {n: z.read(n) for n in z.namelist()}
    slide_names = sorted((n for n in parts if n.startswith('ppt/slides/slide') and n.endswith('.xml')),
                         key=lambda n: int(n[len('ppt/slides/slide'):-4]))
    for name in slide_names:
        tree = pptx.xml(parts[name])
        parent = {c: p for p in tree.iter() for c in p}
        def shape_name(el):
            while el is not None:
                c = el.find(f'.//{{{P}}}cNvPr')
                if el.tag in {f'{{{P}}}{t}' for t in ('sp', 'pic', 'cxnSp', 'grpSp', 'graphicFrame')} and c is not None:
                    return c.get('name')
                el = parent.get(el)
            return '?'

        where = lambda el: f'{name} {shape_name(el)!r}'
        # PptxGenJS draws lines as p:sp with a "line" preset, other tools as p:cxnSp connectors.
        counts['lines'] += len(list(tree.iter(f'{{{P}}}cxnSp'))) + sum(
            g.get('prst') == 'line' for g in tree.iter(f'{{{A}}}prstGeom'))
        for el in tree.iter():
            if 'cx' in el.attrib or 'cy' in el.attrib:
                counts['extents'] += 1
                for k in ('cx', 'cy'):
                    if int(el.get(k, 0)) < 0:  # G1
                        findings.append(f'G1 {where(el)}: negative {k}={el.get(k)}')
        rels_path = posixpath.join('ppt/slides/_rels', posixpath.basename(name) + '.rels')
        targets = {r.get('Id'): posixpath.normpath(posixpath.join('ppt/slides', r.get('Target')))
                   for r in pptx.xml(parts[rels_path])} if rels_path in parts else {}

        def rect(sp):
            x, e = sp.find(f'.//{{{A}}}off'), sp.find(f'.//{{{A}}}ext')
            x0, y0, w, h = (int(x.get('x')), int(x.get('y')), int(e.get('cx')), int(e.get('cy')))
            return x0, y0, x0 + w, y0 + h

        boxes = {c.get('name')[4:]: sp for sp in tree.iter(f'{{{P}}}sp')
                 for c in sp.iter(f'{{{P}}}cNvPr') if (c.get('name') or '').startswith('box:')}
        for pic in tree.iter(f'{{{P}}}pic'):
            counts['pictures'] += 1
            media = targets.get(pic.find(f'.//{{{A}}}blip').get(f'{{{R}}}embed'))
            data = parts.get(media, b'')
            if data[:8] != PNG_SIG:  # G2
                findings.append(f'G2 {where(pic)}: cannot measure {media}, not a PNG')
            else:
                width, height = struct.unpack('>II', data[16:24])
                src = pic.find(f'.//{{{A}}}srcRect')
                crop = {k: int(src.get(k, 0)) if src is not None else 0 for k in 'ltrb'}
                seen = (width * (100000 - crop['l'] - crop['r'])) / (height * (100000 - crop['t'] - crop['b']))
                x0, y0, x1, y1 = rect(pic)
                if x1 == x0 or y1 == y0:
                    findings.append(f'G2 {where(pic)}: zero-size frame {x1 - x0} x {y1 - y0}')
                    continue
                want = (x1 - x0) / (y1 - y0)
                if abs(seen / want - 1) > 0.01:
                    findings.append(f'G2 {where(pic)}: visible aspect {seen:.4f} != frame aspect {want:.4f}')
            pic_name = pic.find(f'.//{{{P}}}cNvPr').get('name')
            descr = pic.find(f'.//{{{P}}}cNvPr').get('descr') or ''
            if '/' in descr or '\\' in descr:  # G4: PptxGenJS defaults descr to the image file path
                findings.append(f'G4 {where(pic)}: alt text looks like a path: {descr!r}')
            if pic_name.startswith('img:'):  # G3
                box = boxes.get(pic_name[4:])
                if box is None:
                    findings.append(f'G3 {where(pic)}: no box:{pic_name[4:]} on slide')
                    continue
                counts['boxed'] += 1
                p, b = rect(pic), rect(box)
                if p[0] < b[0] - 1 or p[1] < b[1] - 1 or p[2] > b[2] + 1 or p[3] > b[3] + 1:
                    findings.append(f'G3 {where(pic)}: {p} outside box {b}')
    return findings


def deck_file(directory, slides, media):
    """slides: list of lists of shape XML; media: {media filename: bytes}; every slide relates rId2 to image1."""
    path = Path(directory) / 'geometry.pptx'
    with zipfile.ZipFile(path, 'w') as z:
        for n, shapes in enumerate(slides, 1):
            z.writestr(f'ppt/slides/slide{n}.xml', f'<p:sld xmlns:p="{pptx.P}" xmlns:a="{pptx.A}" xmlns:r="{pptx.R}"><p:cSld><p:spTree>{"".join(shapes)}</p:spTree></p:cSld></p:sld>')
            z.writestr(f'ppt/slides/_rels/slide{n}.xml.rels', f'<Relationships xmlns="{pptx.REL}"><Relationship Id="rId2" Type="{pptx.R}/image" Target="../media/{next(iter(media))}"/></Relationships>')
        for n, data in media.items():
            z.writestr(f'ppt/media/{n}', data)
    return path


def xfrm(x, y, cx, cy):
    return f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'


def pic(id, rect, crop='', descr=None):
    d = '' if descr is None else f' descr="{descr}"'
    return (f'<p:pic><p:nvPicPr><p:cNvPr id="2" name="img:{id}"{d}/></p:nvPicPr><p:blipFill><a:blip r:embed="rId2"/>{crop}<a:stretch/></p:blipFill>'
            f'<p:spPr>{xfrm(*rect)}</p:spPr></p:pic>')


def box(id, rect):
    return f'<p:sp><p:nvSpPr><p:cNvPr id="3" name="box:{id}"/></p:nvSpPr><p:spPr>{xfrm(*rect)}</p:spPr></p:sp>'


class PresentationPackages(unittest.TestCase):
    def test_edit_retains_related_bytes_and_namespace_declarations(self):
        original = fixture()
        edited = pptx.replace_text(dict(original), [{'slide': 1, 'old': 'Old title', 'new': 'New title'}])
        pptx.validate(edited)
        self.assertEqual(pptx.inspect(edited)['slides'][0]['text'], ['New title', ''])
        self.assertEqual(pptx.inspect(edited)['slides'][0]['notes'], ['Keep these notes'])
        self.assertIn(b'xmlns:p14=', edited['ppt/slides/slide1.xml'])
        self.assertEqual([k for k in original if original[k] != edited[k]], ['ppt/slides/slide1.xml'])

    def test_selection_prunes_discarded_slide_and_its_private_parts(self):
        selected = pptx.select(fixture(), [2])
        pptx.validate(selected)
        self.assertEqual(pptx.inspect(selected)['slides'][0]['text'], ['Second'])
        self.assertNotIn('ppt/slides/slide1.xml', selected)
        self.assertNotIn('ppt/charts/chart1.xml', selected)
        self.assertNotIn('ppt/notesSlides/notes1.xml', selected)

    def test_edit_refuses_rebound_namespace_prefix_without_output(self):
        parts = fixture()
        name = 'ppt/slides/slide1.xml'
        parts[name] = parts[name].replace(
            b'<p:cSld>', b'<p:cSld xmlns:q="urn:outer" mc:Ignorable="q">').replace(
            b'<p:spTree>', b'<p:spTree xmlns:q="urn:inner" mc:Ignorable="q">')
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / 'source.pptx', Path(directory) / 'output.pptx'
            pptx.save(parts, source)
            edits = Path(directory) / 'edits.json'
            edits.write_text(json.dumps([{'slide': 1, 'old': 'Old title', 'new': 'New title'}]))
            result = subprocess.run(['python3', str(SCRIPTS / 'pptx.py'), 'edit', str(source),
                                     '--edits', str(edits), '--output', str(output)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn('namespace prefix', result.stderr)
            self.assertFalse(output.exists())
            self.assertEqual(pptx.load(source)[name], parts[name])

    def test_merge_compares_dimensions_without_optional_size_label(self):
        incoming = fixture()
        incoming[pptx.PRES] = incoming[pptx.PRES].replace(
            b'cx="12192000"', b'type="screen16x9" cx="012192000"')
        combined = pptx.merge([fixture(), incoming])
        self.assertEqual(len(pptx.slides(combined)), 4)
        self.assertEqual(pptx.xml(combined[pptx.PRES]).find(f'{{{pptx.P}}}sldSz').attrib,
                         {'cx': '12192000', 'cy': '6858000'})
        incoming[pptx.PRES] = incoming[pptx.PRES].replace(b'012192000', b'12192001')
        with self.assertRaisesRegex(ValueError, 'identical slide dimensions'):
            pptx.merge([fixture(), incoming])

    def test_edit_refuses_generated_namespace_prefix_collision(self):
        parts = fixture()
        name = 'ppt/slides/slide1.xml'
        parts[name] = parts[name].replace(
            b'mc:Ignorable="p14"', b'xmlns:ns1="urn:custom-feature" mc:Ignorable="ns1"')
        before = parts[name]
        with self.assertRaisesRegex(ValueError, 'namespace prefix'):
            pptx.replace_text(parts, [{'slide': 1, 'old': 'Old title', 'new': 'New title'}])
        self.assertEqual(parts[name], before)

    def test_merge_keeps_chart_notes_and_master_graph(self):
        combined = pptx.merge([fixture(), fixture()])
        self.assertEqual(len(pptx.slides(combined)), 4)
        self.assertEqual(len(pptx.inspect(combined)['charts']), 2)
        self.assertEqual(pptx.inspect(combined)['slides'][2]['notes'], ['Keep these notes'])
        self.assertEqual(combined['ppt/import1/ppt/charts/chart1.xml'], fixture()['ppt/charts/chart1.xml'])
        duplicate = pptx.select(combined, [1, 3])
        self.assertEqual(len(pptx.slides(duplicate)), 2)
        pptx.validate(duplicate)

    def test_embedded_workbook_is_binary_and_opc_roots_keep_default_namespace(self):
        parts = fixture()
        parts['ppt/embeddings/workbook.xlsx'] = b'PK\x03\x04binary workbook'
        types = pptx.xml(parts['[Content_Types].xml'])
        pptx.ET.SubElement(types, f'{{{pptx.CT}}}Override', PartName='/ppt/embeddings/workbook.xlsx',
                           ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        parts['[Content_Types].xml'] = pptx.encoded(types)
        pptx.validate(parts)
        merged = pptx.merge([parts, parts])
        self.assertEqual(merged['ppt/import1/ppt/embeddings/workbook.xlsx'], b'PK\x03\x04binary workbook')
        # LibreOffice rejects prefixed OPC root elements even though XML parses them.
        self.assertIn(b'<Types xmlns=', merged['[Content_Types].xml'])
        self.assertIn(b'<Relationships xmlns=', merged['ppt/_rels/presentation.xml.rels'])

    def test_malformed_package_and_edit_fail_without_output(self):
        for edit in [None, [], [{'slide': 0, 'old': 'Old title', 'new': 'x'}], [{'slide': 1, 'old': 'missing', 'new': 'x'}], [{'slide': True, 'old': 'Old title', 'new': 'x'}]]:
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                pptx.replace_text(fixture(), edit)
        for mutation in ['missing', 'relationship', 'entity', 'duplicate', 'traversal', 'dimensions']:
            parts = fixture()
            if mutation == 'dimensions': parts['ppt/presentation.xml'] = parts['ppt/presentation.xml'].replace(b'cx="12192000"', b'cx="0"')
            if mutation == 'missing': del parts['ppt/charts/chart1.xml']
            if mutation == 'relationship': parts['ppt/_rels/presentation.xml.rels'] = parts['ppt/_rels/presentation.xml.rels'].replace(b'Id="s2"', b'Id="s1"')
            if mutation == 'entity': parts['ppt/charts/chart1.xml'] = '<!DOCTYPE x [<!ENTITY y "bad">]><x>&y;</x>'.encode('utf-16')
            if mutation == 'duplicate': parts['ppt/presentation.xml'] = parts['ppt/presentation.xml'].replace(b'id="257"', b'id="256"')
            if mutation == 'traversal': parts['../outside.xml'] = b'<x/>'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                pptx.validate(parts)

    def test_xml_default_content_type_cannot_bypass_entity_guard(self):
        parts = fixture()
        parts['[Content_Types].xml'] = parts['[Content_Types].xml'].replace(
            b'</Types>', b'<Default Extension="data" ContentType="application/xml"/></Types>')
        parts['custom/item.data'] = b'<!DOCTYPE x [<!ENTITY y "bad">]><x>&y;</x>'
        with self.assertRaisesRegex(ValueError, 'DTD/entity'):
            pptx.validate(parts)

    def test_zip_load_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'deck.pptx'
            pptx.save(fixture(), out)
            self.assertEqual(len(pptx.slides(pptx.load(out))), 2)
            before = out.read_bytes()
            with self.assertRaises(ValueError): pptx.save(fixture(), out)
            self.assertEqual(out.read_bytes(), before)
            link = Path(directory) / 'link.pptx'
            link.symlink_to(out)
            with self.assertRaises(ValueError): pptx.save(fixture(), link)
            bad = Path(directory) / 'bad.pptx'
            with zipfile.ZipFile(bad, 'w') as archive:
                archive.writestr('../escape', b'bad')
            with self.assertRaises(ValueError): pptx.load(bad)
            self.assertFalse((Path(directory).parent / 'escape').exists())

    def test_render_refuses_existing_output_without_deleting_images(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'deck.pptx'
            source.write_bytes(b'not a deck')
            output = root / 'review'
            output.mkdir()
            image = output / 'slide-1.jpg'
            image.write_bytes(b'previous review')
            with self.assertRaises(ValueError): renderer.render(source, output)
            self.assertEqual(image.read_bytes(), b'previous review')
            link = root / 'review-link'
            link.symlink_to(output, target_is_directory=True)
            with self.assertRaises(ValueError): renderer.render(source, link)

    def test_portable_source_package_and_output_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out = creator.create(root / 'board', 'board', 'advisor')
            source = (out / 'deck.js').read_text()
            self.assertIn('require("./deck-kit/deck-kit")', source)
            self.assertNotIn(str(ROOT), source)
            self.assertEqual((out / 'deck-kit/theme-tokens.js').read_bytes(), (SCRIPTS.parent / 'assets/theme-tokens.js').read_bytes())
            manifest = json.loads((out / 'package.json').read_text())
            self.assertEqual(manifest['engines'], {'node': '>=20.15'})
            self.assertEqual(manifest['dependencies'], {'pptxgenjs': '4.0.1', 'image-size': 'file:./deck-kit/unused-image-size'})
            self.assertEqual(manifest['overrides'], {'pptxgenjs@4.0.1': {'image-size': '$image-size'}})
            self.assertTrue((out / 'deck-kit/unused-image-size/index.js').is_file())
            with self.assertRaises(ValueError): creator.create(out, 'board', 'advisor')
            with self.assertRaises(ValueError): creator.create(root / 'bad', '../escape', 'status')
            self.assertFalse((root / 'bad').exists())

    @unittest.skipUnless(os.environ.get('PRESENTATIONS_PACKAGE'), 'requires an installed generated deck package')
    def test_installed_package_omits_parser_and_preserves_native_content(self):
        project = Path(os.environ['PRESENTATIONS_PACKAGE']).resolve()
        script = '''
const assert = require('node:assert/strict');
const {createRequire} = require('node:module');
const local = createRequire(process.argv[1] + '/package.json');
const fromPptx = createRequire(local.resolve('pptxgenjs'));
assert.throws(() => fromPptx('image-size'), /image-size is intentionally unavailable/);
const PptxGenJS = local('pptxgenjs');
const deck = new PptxGenJS();
const slide = deck.addSlide();
slide.addText('Dependency proof', {x:1, y:1, w:4, h:1});
slide.addNotes('Speaker notes preserved');
slide.addImage({path:process.argv[3], x:1, y:2, w:1, h:1});
slide.addChart(deck.ChartType.bar, [{name:'Series', labels:['A'], values:[3]}],
              {x:3, y:2, w:4, h:3});
deck.writeFile({fileName:process.argv[2]}).catch(e => {console.error(e); process.exitCode=1;});
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out = root / 'proof.pptx'
            # Construct a real 1x1 RGB PNG with stdlib, not a parser-specific mock.
            import struct
            import zlib
            def chunk(kind, data):
                return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
            png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
            png += chunk(b'IDAT', zlib.compress(b'\x00\xff\x00\x00')) + chunk(b'IEND', b'')
            (root / 'pixel.png').write_bytes(png)
            result = subprocess.run(['node', '-e', script, str(project), str(out), str(root / 'pixel.png')],
                                    capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            parts = pptx.load(out)
            self.assertIn('Speaker notes preserved', pptx.inspect(parts)['slides'][0]['notes'])
            self.assertEqual(len(pptx.inspect(parts)['charts']), 1)
            self.assertIn(png, parts.values())


class PictureGeometry(unittest.TestCase):
    def check(self, slides, media=None):
        with tempfile.TemporaryDirectory() as directory:
            counts = {}
            found = geometry_findings(deck_file(directory, slides, media or {'image1.png': png(1600, 900)}), counts)
        return found, counts

    def one(self, rule, pic_xml, box_xml, media=None):
        found, _ = self.check([[box_xml, pic_xml]] if box_xml else [[pic_xml]], media)
        self.assertEqual(len(found), 1, found)
        self.assertTrue(found[0].startswith(rule), found)
        return found[0]

    def test_clean_shapes_have_no_findings_and_are_counted(self):
        crop = '<a:srcRect l="25000" r="25000"/>'
        cases = [('landscape', (1600, 900), (0, 150000, 1600000, 900000), (0, 0, 1600000, 1200000), ''),
                 ('portrait', (900, 1600), (150000, 0, 900000, 1600000), (0, 0, 1200000, 1600000), ''),
                 ('square', (800, 800), (100000, 100000, 800000, 800000), (0, 0, 1000000, 1000000), ''),
                 ('crop', (1600, 900), (0, 0, 800000, 900000), (0, 0, 800000, 900000), crop)]
        for id, size, frame, outer, src in cases:
            with self.subTest(id), tempfile.TemporaryDirectory() as directory:
                counts = {}
                path = deck_file(directory, [[box(id, outer), pic(id, frame, src)]], {'image1.png': png(*size)})
                self.assertEqual(geometry_findings(path, counts), [])
                self.assertEqual(counts, {'pictures': 1, 'boxed': 1, 'extents': 2, 'lines': 0})

    def test_stretched_picture_is_found(self):
        self.assertIn('visible aspect', self.one('G2', pic('a', (0, 0, 1680000, 900000)), box('a', (0, 0, 2000000, 1200000))))

    def test_negative_extent_is_found(self):
        line = f'<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="4" name="line:x"/></p:nvCxnSpPr><p:spPr>{xfrm(0, 0, -12700, 0)}</p:spPr></p:cxnSp>'
        found, counts = self.check([[line]])
        self.assertEqual(len(found), 1, found)
        self.assertIn("G1 ppt/slides/slide1.xml 'line:x': negative cx=-12700", found[0])
        self.assertEqual(counts['extents'], 1)

    def test_picture_outside_box_is_found(self):
        self.assertIn('outside box', self.one('G3', pic('a', (100000, 0, 1600000, 900000)), box('a', (0, 0, 1600000, 900000))))

    def test_crop_not_matching_frame_is_found(self):
        crop = '<a:srcRect l="25000" r="25000"/>'
        self.assertIn('visible aspect', self.one('G2', pic('a', (0, 0, 1600000, 900000), crop), box('a', (0, 0, 1600000, 900000))))

    def test_path_in_alt_text_is_found(self):
        frame, outer = (0, 0, 1600000, 900000), box('a', (0, 0, 1600000, 900000))
        self.assertIn('/home/someone/shot.png', self.one('G4', pic('a', frame, descr='/home/someone/shot.png'), outer))
        found, _ = self.check([[outer, pic('a', frame, descr='Quarterly revenue chart')]])
        self.assertEqual(found, [])

    def test_img_without_box_is_found(self):
        self.assertIn('no box:a', self.one('G3', pic('a', (0, 0, 1600000, 900000)), None))

    def test_non_png_media_cannot_be_measured(self):
        self.assertIn('cannot measure', self.one('G2', pic('a', (0, 0, 1600000, 900000)), box('a', (0, 0, 1600000, 900000)),
                                                 {'image1.jpg': b'\xff\xd8\xff\xe0JFIF'}))

    def test_zero_extent_picture_is_found_not_raised(self):
        for rect in ((0, 0, 1600000, 0), (0, 0, 0, 900000)):
            with self.subTest(rect=rect):
                self.assertIn('zero', self.one('G2', pic('a', rect), box('a', (0, 0, 1600000, 900000))))

    @unittest.skipUnless(shutil.which('node'), 'Node is required to load deck-kit.js')
    def test_fit_image_rejects_non_finite_or_missing_box_numbers(self):
        script = '''
const assert = require('node:assert/strict');
const Module = require('node:module');
const load = Module._load;
Module._load = (id, ...rest) => id === 'pptxgenjs' ? function () {} : load(id, ...rest);
const {fitImage} = require(process.argv[1]);
for (const box of [{x: 0, y: 0, w: Infinity, h: 1}, {y: 0, w: 1, h: 1}, {x: 0, w: 1, h: 1}, {x: 0, y: NaN, w: 1, h: 1}]) {
  assert.throws(() => fitImage(10, 10, box), /box/i, JSON.stringify(box));
}
assert.deepEqual(fitImage(10, 10, {x: 1, y: 2, w: 4, h: 2}).x, 2);
'''
        asset = SCRIPTS.parent / 'assets/deck-kit.js'
        result = subprocess.run(['node', '-e', script, str(asset)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_package_ships_media_example(self):
        with tempfile.TemporaryDirectory() as directory:
            out = creator.create(Path(directory) / 'board', 'board', 'advisor')
            self.assertTrue((out / 'deck-kit/media-example.js').is_file())

    @unittest.skipUnless(os.environ.get('PRESENTATIONS_MEDIA_PPTX'), 'set PRESENTATIONS_MEDIA_PPTX to a generated media-example .pptx')
    def test_generated_media_deck_geometry(self):
        counts = {}
        self.assertEqual(geometry_findings(os.environ['PRESENTATIONS_MEDIA_PPTX'], counts), [])
        self.assertGreaterEqual(counts['pictures'], 4)
        self.assertGreaterEqual(counts['boxed'], 4)
        self.assertGreaterEqual(counts['lines'], 1)


if __name__ == '__main__':
    unittest.main()
