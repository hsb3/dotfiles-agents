#!/usr/bin/env python3
"""Create a portable PptxGenJS source package with the authored presentation assets."""
import argparse
from pathlib import Path
import json
import re
import shutil
import tempfile

ASSETS = Path(__file__).resolve().parent.parent / 'assets'


def create(output, slug, kind):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug):
        raise ValueError('slug must be lowercase kebab-case')
    if kind not in ('status', 'advisor', 'client'):
        raise ValueError('type must be status, advisor or client')
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError(f'Refusing existing output: {output}')
    # Stage adjacent to destination; a failed copy leaves no partial deck package.
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        package = Path(tmp) / 'package'
        package.mkdir()
        kit = package / 'deck-kit'
        kit.mkdir()
        for name in ('deck-kit.js', 'theme-tokens.js'):
            shutil.copyfile(ASSETS / name, kit / name)
        # 4.0.1 declares image-size but never imports it. Omit the vulnerable parser;
        # a future caller must fail visibly rather than receive fabricated dimensions.
        unused = kit / 'unused-image-size'
        unused.mkdir()
        (unused / 'package.json').write_text(json.dumps({
            'name': '@presentations/unused-image-size', 'version': '0.0.0',
            'private': True, 'main': 'index.js',
        }, indent=2) + '\n')
        (unused / 'index.js').write_text(
            'throw new Error("image-size is intentionally unavailable; PptxGenJS 4.0.1 does not use it");\n')
        source = (ASSETS / 'starter.js').read_text()
        source = source.replace('__TYPE__', kind).replace('__SLUG__', slug)
        (package / 'deck.js').write_text(source)
        (package / '.gitignore').write_text('node_modules/\n*.pptx\nrender/\n')
        (package / 'package.json').write_text(json.dumps({
            'name': slug, 'private': True, 'scripts': {'build': 'node deck.js'},
            'dependencies': {'pptxgenjs': '4.0.1', 'image-size': 'file:./deck-kit/unused-image-size'},
            'overrides': {'pptxgenjs@4.0.1': {'image-size': '$image-size'}},
        }, indent=2) + '\n')
        # mkdir exclusively reserves the destination, including against a symlink race.
        output.mkdir()
        try:
            for item in package.iterdir():
                shutil.move(str(item), output / item.name)
        except Exception:
            shutil.rmtree(output)
            raise
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--type', choices=['status', 'advisor', 'client'], required=True)
    parser.add_argument('--slug', required=True)
    parser.add_argument('--out', type=Path, required=True, help='New package directory; parent must exist')
    args = parser.parse_args()
    try:
        print(create(args.out, args.slug, args.type))
    except (ValueError, OSError) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()
