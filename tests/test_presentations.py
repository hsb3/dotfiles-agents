"""Package edits must preserve notes/chart bytes and reject broken input before output."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
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
            self.assertEqual(json.loads((out / 'package.json').read_text())['dependencies'], {'pptxgenjs': '4.0.1'})
            with self.assertRaises(ValueError): creator.create(out, 'board', 'advisor')
            with self.assertRaises(ValueError): creator.create(root / 'bad', '../escape', 'status')
            self.assertFalse((root / 'bad').exists())


if __name__ == '__main__':
    unittest.main()
