#!/usr/bin/env python3
"""Inspect, validate and edit PresentationML packages without extracting ZIP entries.

Structural checks are deliberately distinct from full ISO/ECMA schema validation.
See references/editing.md for the supported package/editing boundary.
"""
import argparse
import json
import io
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import tempfile
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
import zipfile

P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
PRES = 'ppt/presentation.xml'
MAX_BYTES = 256 * 1024 * 1024
for prefix, uri in [('p', P), ('a', A), ('r', R)]:
    ET.register_namespace(prefix, uri)


def xml(data):
    # Decode first so UTF-16 cannot hide DTD/entity declarations from the check.
    if re.search(br'<!\s*(DOCTYPE|ENTITY)', data.replace(b'\x00', b''), re.I):
        raise ValueError('DTD/entity declarations are unsupported')
    return ET.fromstring(data)


def encoded(root, original=None):
    if root.tag in (f'{{{CT}}}Types', f'{{{REL}}}Relationships'):
        ET.register_namespace('', root.tag[1:].split('}')[0])
    data = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    if original:
        # Keep declarations used by mc:Ignorable and other QName-valued attributes.
        bindings = dict(binding for _, binding in ET.iterparse(io.BytesIO(data), events=['start-ns']))
        for _, (prefix, uri) in ET.iterparse(io.BytesIO(original), events=['start-ns']):
            if prefix in bindings and bindings[prefix] != uri:
                raise ValueError(f'Conflicting namespace prefix {prefix!r}; use a native application to edit')
            bindings[prefix] = uri
            if prefix and f'xmlns:{prefix}='.encode() not in data:
                root.set('xmlns:' + prefix, uri)
        data = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    return data


def safe_name(name):
    if (not name or '\\' in name or '\x00' in name or ':' in name
            or name.startswith('/') or any(p in ('', '.', '..') for p in name.split('/'))):
        raise ValueError(f'Unsafe package path: {name!r}')
    return name


def relpath(part):
    return posixpath.join(posixpath.dirname(part), '_rels', posixpath.basename(part) + '.rels')


def source_part(name):
    if name == '_rels/.rels':
        return ''
    p = PurePosixPath(name)
    if p.parent.name != '_rels':
        raise ValueError(f'Invalid relationship part: {name}')
    return str(p.parent.parent / p.name[:-5])


def target(part, value):
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or parsed.query or '\\' in value:
        raise ValueError(f'Invalid internal target: {value}')
    raw = unquote(parsed.path)
    name = posixpath.normpath(posixpath.join(posixpath.dirname(part), raw)) if not raw.startswith('/') else raw[1:]
    return safe_name(name)


def relationships(parts, part):
    data = parts.get(relpath(part))
    return list(xml(data)) if data is not None else []


def load(file):
    with zipfile.ZipFile(file) as archive:
        entries = archive.infolist()
        if len(entries) > 10000 or sum(i.file_size for i in entries) > MAX_BYTES:
            raise ValueError('Package exceeds 10000 entries or 256 MiB expanded')
        parts = {}
        for entry in entries:
            if entry.is_dir():
                safe_name(entry.filename.rstrip('/'))
                continue
            name = safe_name(entry.filename)
            if name in parts or entry.flag_bits & 1 or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError(f'Duplicate, encrypted or symlink entry: {name}')
            parts[name] = archive.read(entry)
    validate(parts)
    return parts


def slides(parts):
    root = xml(parts[PRES])
    rels = {r.get('Id'): r for r in relationships(parts, PRES)}
    result = []
    ids = set()
    for item in root.findall(f'{{{P}}}sldIdLst/{{{P}}}sldId'):
        rid = item.get(f'{{{R}}}id')
        relation = rels.get(rid)
        if relation is None or relation.get('Type') != R + '/slide' or relation.get('TargetMode') == 'External':
            raise ValueError(f'Invalid slide relationship: {rid}')
        sid = item.get('id', '')
        if not sid.isdigit() or not 256 <= int(sid) < 2147483648 or sid in ids:
            raise ValueError(f'Invalid/duplicate slide id: {sid}')
        ids.add(sid)
        result.append(target(PRES, relation.get('Target', '')))
    if not result:
        raise ValueError('Presentation has no slides')
    return result


def validate(parts):
    for required in ('[Content_Types].xml', '_rels/.rels', PRES):
        if required not in parts:
            raise ValueError(f'Missing package part: {required}')
    types = xml(parts['[Content_Types].xml'])
    if types.tag != f'{{{CT}}}Types':
        raise ValueError('Invalid content-types root')
    overrides, defaults = {}, {}
    for item in types:
        if item.tag not in (f'{{{CT}}}Override', f'{{{CT}}}Default'):
            raise ValueError('Unknown content type declaration')
        is_override = item.tag == f'{{{CT}}}Override'
        key = item.get('PartName') if is_override else item.get('Extension')
        table = overrides if is_override else defaults
        if not key or key in table or not item.get('ContentType'):
            raise ValueError('Invalid/duplicate content type')
        table[key] = item.get('ContentType')
    for name, data in parts.items():
        safe_name(name)
        if name != '[Content_Types].xml' and '/' + name not in overrides and name.rsplit('.', 1)[-1] not in defaults:
            raise ValueError(f'No content type for {name}')
        content_type = overrides.get('/' + name, defaults.get(name.rsplit('.', 1)[-1], ''))
        if name.endswith(('.xml', '.rels')) or content_type.endswith(('+xml', '/xml')):
            root = xml(data)
            if name.endswith('.rels'):
                if root.tag != f'{{{REL}}}Relationships':
                    raise ValueError(f'Invalid relationships root: {name}')
                source = source_part(name)
                if source and source not in parts:
                    raise ValueError(f'Missing relationship source: {source}')
                ids = set()
                for relation in root:
                    if relation.tag != f'{{{REL}}}Relationship' or relation.get('TargetMode') not in (None, 'Internal', 'External'):
                        raise ValueError(f'Invalid relationship element in {name}')
                    rid = relation.get('Id')
                    if not rid or rid in ids or not relation.get('Type') or not relation.get('Target'):
                        raise ValueError(f'Invalid/duplicate relationship in {name}')
                    ids.add(rid)
                    if relation.get('TargetMode') == 'External':
                        continue
                    if target(source, relation.get('Target')) not in parts:
                        raise ValueError(f'Missing target from {name}: {relation.get("Target")}')
            else:
                available = {r.get('Id') for r in relationships(parts, name)}
                for element in root.iter():
                    for attr, value in element.attrib.items():
                        if attr.startswith('{' + R + '}') and value not in available:
                            raise ValueError(f'Unresolved {attr}={value} in {name}')
    if xml(parts[PRES]).tag != f'{{{P}}}presentation':
        raise ValueError('Only transitional PresentationML is supported')
    size = xml(parts[PRES]).find(f'{{{P}}}sldSz')
    if size is None or any(not size.get(k, '').isdigit() or int(size.get(k)) <= 0 for k in ('cx', 'cy')):
        raise ValueError('Missing or invalid slide dimensions')
    roots = relationships(parts, '')
    if not any(r.get('Type') == R + '/officeDocument' and target('', r.get('Target', '')) == PRES for r in roots):
        raise ValueError('Missing officeDocument relationship')
    for name in slides(parts):
        if xml(parts[name]).tag != f'{{{P}}}sld':
            raise ValueError(f'Invalid slide root: {name}')


def save(parts, output):
    validate(parts)
    output = Path(output)
    if output.suffix.lower() not in ('.pptx', '.potx'):
        raise ValueError('Output must be .pptx or .potx')
    if output.exists() or output.is_symlink():
        raise ValueError(f'Refusing existing output: {output}')
    types = xml(parts['[Content_Types].xml'])
    for item in types:
        if item.get('PartName') == '/' + PRES:
            kind = 'template' if output.suffix.lower() == '.potx' else 'presentation'
            item.set('ContentType', f'application/vnd.openxmlformats-officedocument.presentationml.{kind}.main+xml')
    parts = dict(parts, **{'[Content_Types].xml': encoded(types)})
    # Exclusive create after a complete temporary ZIP prevents partial output and overwrite races.
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        tmp = Path(temp) / 'package.zip'
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(parts.items()):
                archive.writestr(name, data)
        os.link(tmp, output)


def inspect(parts):
    result = []
    for index, name in enumerate(slides(parts), 1):
        root = xml(parts[name])
        related = relationships(parts, name)
        notes = [target(name, r.get('Target')) for r in related if r.get('Type') == R + '/notesSlide']
        result.append({'slide': index, 'part': name,
                       'text': [''.join(p.itertext()) for p in root.findall(f'.//{{{A}}}t')],
                       'notes': [t.text or '' for n in notes for t in xml(parts[n]).findall(f'.//{{{A}}}t')],
                       'relationships': [dict(r.attrib) for r in related]})
    return {'slides': result, 'charts': [n for n in parts if '/charts/' in n and n.endswith('.xml')],
            'fonts': sorted({e.get('typeface') for n, b in parts.items() if n.endswith('.xml')
                             for e in xml(b).iter() if e.get('typeface')}), 'parts': len(parts)}


def editable(parts):
    if any(n.startswith('_xmlsignatures/') or n.endswith('vbaProject.bin') for n in parts):
        raise ValueError('Signed or macro-enabled packages cannot be edited')


def replace_text(parts, edits):
    editable(parts)
    if not isinstance(edits, list) or not edits:
        raise ValueError('Edits must be a nonempty JSON array')
    ordered = slides(parts)
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) != {'slide', 'old', 'new'}:
            raise ValueError('Each edit requires exactly slide, old, new')
        number, old, new = edit['slide'], edit['old'], edit['new']
        if type(number) is not int or not 1 <= number <= len(ordered) or not isinstance(old, str) or not old or not isinstance(new, str):
            raise ValueError('Invalid slide number or replacement text')
        name = ordered[number - 1]
        root = xml(parts[name])
        found = 0
        # Match complete paragraphs, including text split over formatting runs.
        for paragraph in root.findall(f'.//{{{A}}}p'):
            runs = paragraph.findall(f'.//{{{A}}}t')
            if ''.join(t.text or '' for t in runs) == old:
                runs[0].text = new
                for run in runs[1:]:
                    run.text = ''
                found += 1
        if found != 1:
            raise ValueError(f'Expected one paragraph on slide {number}, found {found}: {old!r}')
        parts[name] = encoded(root, parts[name])
    return parts


def select(parts, numbers):
    editable(parts)
    ordered = slides(parts)
    if not numbers or any(type(n) is not int or not 1 <= n <= len(ordered) for n in numbers):
        raise ValueError('Selection must contain valid 1-based slide numbers')
    if len(set(numbers)) != len(numbers):
        raise ValueError('For duplicates use merge with the same input twice, then select')
    root = xml(parts[PRES])
    listing = root.find(f'{{{P}}}sldIdLst')
    items = list(listing)
    listing[:] = [items[n - 1] for n in numbers]
    # Custom shows/section metadata reference the old order and are explicitly unsupported here.
    if root.find(f'{{{P}}}custShowLst') is not None or root.find(f'{{{P}}}extLst') is not None:
        raise ValueError('Selection of decks with custom shows/extensions is unsupported')
    parts[PRES] = encoded(root, parts[PRES])
    rels = xml(parts[relpath(PRES)])
    keep = {item.get(f'{{{R}}}id') for item in listing}
    rels[:] = [r for r in rels if r.get('Type') != R + '/slide' or r.get('Id') in keep]
    parts[relpath(PRES)] = encoded(rels)
    return prune(parts)


def prune(parts):
    reachable = {'[Content_Types].xml', '_rels/.rels'}
    pending = ['']
    while pending:
        part = pending.pop()
        for relation in relationships(parts, part):
            if relation.get('TargetMode') == 'External':
                continue
            dest = target(part, relation.get('Target'))
            if dest not in reachable:
                reachable.add(dest)
                pending.append(dest)
                if relpath(dest) in parts:
                    reachable.add(relpath(dest))
    out = {name: data for name, data in parts.items() if name in reachable}
    types = xml(out['[Content_Types].xml'])
    types[:] = [t for t in types if t.tag != f'{{{CT}}}Override' or t.get('PartName', '').lstrip('/') in out]
    out['[Content_Types].xml'] = encoded(types)
    return out


def merge(packages):
    """Import whole part graphs under collision-free names; keep each slide's own masters."""
    if len(packages) < 2:
        raise ValueError('merge needs at least two inputs')
    out = dict(packages[0])
    editable(out)
    root = xml(out[PRES])
    listing = root.find(f'{{{P}}}sldIdLst')
    rels = xml(out[relpath(PRES)])
    types = xml(out['[Content_Types].xml'])
    size = tuple(int(root.find(f'{{{P}}}sldSz').get(k)) for k in ('cx', 'cy'))
    for index, incoming in enumerate(packages[1:], 1):
        editable(incoming)
        other = xml(incoming[PRES])
        if tuple(int(other.find(f'{{{P}}}sldSz').get(k)) for k in ('cx', 'cy')) != size:
            raise ValueError('Merged decks must have identical slide dimensions')
        if any(n.startswith('ppt/comments/') or n == 'ppt/commentAuthors.xml' for n in incoming):
            raise ValueError('Merge with comments is unsupported')
        prefix = f'ppt/import{index}/'
        if any(n.startswith(prefix) for n in out):
            raise ValueError(f'Import namespace already exists: {prefix}')
        mapping = {n: prefix + n for n in incoming if n != '[Content_Types].xml' and not n.endswith('.rels')}
        for name, data in incoming.items():
            if name in mapping:
                out[mapping[name]] = data
            elif name.endswith('.rels'):
                source = source_part(name)
                if not source:
                    continue
                relations = xml(data)
                for relation in relations:
                    if relation.get('TargetMode') != 'External':
                        dest = mapping[target(source, relation.get('Target'))]
                        relation.set('Target', '/' + dest)
                out[relpath(mapping[source])] = encoded(relations)
        incoming_types = xml(incoming['[Content_Types].xml'])
        defaults = {t.get('Extension'): t.get('ContentType') for t in incoming_types if t.tag == f'{{{CT}}}Default'}
        overrides = {t.get('PartName'): t.get('ContentType') for t in incoming_types if t.tag == f'{{{CT}}}Override'}
        for name, renamed in mapping.items():
            kind = overrides.get('/' + name, defaults.get(name.rsplit('.', 1)[-1]))
            ET.SubElement(types, f'{{{CT}}}Override', PartName='/' + renamed, ContentType=kind)
        for name in slides(incoming):
            rid = f'rIdImported{index}_{len(listing)}'
            used = {r.get('Id') for r in rels}
            while rid in used:
                rid += '_'
            ET.SubElement(rels, f'{{{REL}}}Relationship', Id=rid, Type=R + '/slide', Target='/' + mapping[name])
            sid = max(int(s.get('id')) for s in listing) + 1
            ET.SubElement(listing, f'{{{P}}}sldId', {'id': str(sid), f'{{{R}}}id': rid})
        for relation in relationships(incoming, PRES):
            if relation.get('Type') != R + '/slideMaster':
                continue
            masters = root.find(f'{{{P}}}sldMasterIdLst')
            if masters is None:
                masters = ET.Element(f'{{{P}}}sldMasterIdLst')
                root.insert(0, masters)
            rid = f'rIdMaster{index}_{len(masters)}'
            ET.SubElement(rels, f'{{{REL}}}Relationship', Id=rid, Type=R + '/slideMaster', Target='/' + mapping[target(PRES, relation.get('Target'))])
            mid = max([int(m.get('id')) for m in masters] + [2147483647]) + 1
            ET.SubElement(masters, f'{{{P}}}sldMasterId', {'id': str(mid), f'{{{R}}}id': rid})
    out[PRES], out[relpath(PRES)], out['[Content_Types].xml'] = encoded(root, out[PRES]), encoded(rels), encoded(types)
    validate(out)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('inspect', 'validate', 'edit', 'select', 'merge'):
        command = commands.add_parser(name)
        command.add_argument('input', nargs='+' if name == 'merge' else None)
        if name in ('edit', 'select', 'merge'):
            command.add_argument('--output', required=True)
        if name == 'edit':
            command.add_argument('--edits', required=True, help='JSON array of {slide, old, new} exact paragraph replacements')
        if name == 'select':
            command.add_argument('--slides', required=True, help='Ordered 1-based comma-separated slide numbers')
    args = parser.parse_args()
    try:
        parts = merge([load(p) for p in args.input]) if args.command == 'merge' else load(args.input)
        if args.command == 'inspect':
            print(json.dumps(inspect(parts), indent=2))
        elif args.command == 'validate':
            print(f'Valid package structure: {len(slides(parts))} slides; full XSD conformance not checked')
        else:
            if args.command == 'edit':
                parts = replace_text(parts, json.loads(Path(args.edits).read_text()))
            elif args.command == 'select':
                parts = select(parts, [int(n) for n in args.slides.split(',')])
            save(parts, args.output)
            print(args.output)
    except (ValueError, OSError, KeyError, ET.ParseError, zipfile.BadZipFile) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()
