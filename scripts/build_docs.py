#!/usr/bin/env python3
"""Render canonical Markdown with Pandoc; never stage generated output in the repo."""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import posixpath
import re
import shutil
import subprocess
from urllib.parse import quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
REPO = 'https://github.com/hsb3/dotfiles-agents'


def pages():
    return sorted({Path('README.md'), Path('.github/CONTRIBUTING.md'),
                   *[p.relative_to(ROOT) for p in (ROOT / 'docs').rglob('*.md')],
                   *[p.relative_to(ROOT) for p in (ROOT / 'plugins').glob('*/README.md')]})


def target(path):
    # The official Pages artifact action excludes every hidden directory.
    if path == Path('.github/CONTRIBUTING.md'):
        return Path('contributing.html')
    return Path('index.html') if path == Path('docs/README.md') else path.with_suffix('.html')


def rewrite(node, source, selected, base, ref):
    if isinstance(node, list):
        return [rewrite(x, source, selected, base, ref) for x in node]
    if not isinstance(node, dict):
        return node
    if node.get('t') in ('Link', 'Image'):
        url = node['c'][-1][0]
        parts = urlsplit(url)
        if not parts.scheme and not parts.netloc and parts.path:
            path = Path(posixpath.normpath(str(source.parent / unquote(parts.path))))
            disk = ROOT / path
            if not disk.exists() or not disk.resolve().is_relative_to(ROOT):
                raise ValueError(f'{source}: broken local link: {url}')
            if disk.is_dir() and path / 'README.md' in selected:
                path /= 'README.md'
            if path in selected:
                dest = base + '/' + quote(target(path).as_posix())
            else:
                kind = 'tree' if disk.is_dir() else 'blob'
                dest = f'{REPO}/{kind}/{ref}/' + quote(path.as_posix())
                if node['t'] == 'Image':
                    dest = f'https://raw.githubusercontent.com/hsb3/dotfiles-agents/{ref}/' + quote(path.as_posix())
            node['c'][-1][0] = dest + ('?' + parts.query if parts.query else '') + ('#' + parts.fragment if parts.fragment else '')
    return {k: rewrite(v, source, selected, base, ref) for k, v in node.items()}


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links = set(), []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        for key in ('href', 'src'):
            if key in attrs:
                self.links.append(attrs[key])


def validate(output, base):
    documents = {}
    for path in output.rglob('*.html'):
        if any(part.startswith('.') for part in path.relative_to(output).parts):
            raise ValueError(f'Pages artifact excludes hidden path: {path}')
        parser = Links()
        parser.feed(path.read_text())
        documents[path.relative_to(output).as_posix()] = parser
    for name, page in documents.items():
        for url in page.links:
            parts = urlsplit(url)
            if parts.scheme or parts.netloc:
                continue
            path = unquote(parts.path)
            if path.startswith('/'):
                if not path.startswith(base + '/'):
                    raise ValueError(f'{name}: escapes project subpath: {url}')
                path = path[len(base) + 1:]
            elif path:
                path = posixpath.normpath(posixpath.join(posixpath.dirname(name), path))
            else:
                path = name
            if not (output / path).is_file():
                raise ValueError(f'{name}: missing rendered target: {url}')
            if parts.fragment and path in documents and unquote(parts.fragment) not in documents[path].ids:
                raise ValueError(f'{name}: missing heading: {url}')
    return len(documents)


def build(output, base, ref):
    if output.resolve().is_relative_to(ROOT):
        raise ValueError('Choose an output directory outside the source checkout')
    selected = set(pages())
    output.mkdir(parents=True, exist_ok=True)
    (output / 'assets').mkdir(exist_ok=True)
    shutil.copyfile(ROOT / 'docs/site/site.css', output / 'assets/site.css')
    for source in sorted(selected):
        text = (ROOT / source).read_text()
        ast = json.loads(subprocess.check_output(['pandoc', '-f', 'gfm+yaml_metadata_block', '-t', 'json'], input=text, text=True))
        meta_title = ast.get('meta', {}).get('title')
        if not re.search(r'^# ', text, re.M):
            title = meta_title or {'t': 'MetaString', 'c': source.stem}
            title_text = subprocess.check_output(['pandoc', '-f', 'json', '-t', 'plain'], input=json.dumps({**ast, 'blocks': [{'t': 'Plain', 'c': title.get('c', [])}]}), text=True).strip() if title['t'] == 'MetaInlines' else title['c']
            heading = json.loads(subprocess.check_output(['pandoc', '-f', 'gfm', '-t', 'json'], input='# ' + title_text, text=True))['blocks']
            ast['blocks'] = heading + ast['blocks']
        ast = rewrite(ast, source, selected, base, ref)
        title = re.search(r'^# (.+)', text, re.M)
        page_title = title[1] if title else source.stem
        # Frontmatter belongs to canonical Markdown; the site needs only the visible title.
        ast['meta'] = {}
        dest = output / target(source)
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['pandoc', '-f', 'json', '-t', 'html5', '--standalone', '--toc', '--toc-depth=2',
                        '--template=' + str(ROOT / 'docs/site/template.html'), '-M', 'pagetitle=' + page_title,
                        '-V', 'base=' + base, '-V', 'source=' + REPO + '/blob/' + ref + '/' + quote(source.as_posix()),
                        '-o', str(dest)], input=json.dumps(ast), text=True, check=True)
        # Overflowing code and tables must be reachable without a pointer device.
        dest.write_text(re.sub(r'<(pre|table)(?=[\s>])', r'<\1 tabindex="0"', dest.read_text()))
    print(f'{validate(output, base)} pages built; project paths, assets and heading links verified: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/dotfiles-agents-site/dotfiles-agents'))
    parser.add_argument('--base', default='/dotfiles-agents')
    parser.add_argument('--ref', default='dev')
    args = parser.parse_args()
    if not re.fullmatch(r'/[A-Za-z0-9_-]+', args.base):
        parser.error('--base must be one project URL segment, such as /dotfiles-agents')
    build(args.output, args.base, args.ref)
