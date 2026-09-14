#!/usr/bin/env python3
"""Render a deck to PDF, slide JPEGs and a labeled HTML contact sheet."""
import argparse
import html
import os
import sys
from pathlib import Path
import shutil
import subprocess
import tempfile


def render(source, output):
    source = Path(source).resolve(strict=True)
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError(f'Refusing existing output directory: {output}; choose a new QA directory')
    if source.suffix.lower() not in ('.pptx', '.potx') or not source.is_file():
        raise ValueError('Input must be a .pptx or .potx file')
    if not shutil.which('pdftoppm'):
        raise ValueError('pdftoppm is required (Poppler)')
    soffice = shutil.which('soffice')
    mac = Path('/Applications/LibreOffice.app/Contents/MacOS/soffice')
    if not soffice and mac.is_file():
        soffice = str(mac)
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        # Fixed input basename avoids option-like filenames and renderer output-name guesses.
        deck = temp / 'deck.pptx'
        shutil.copyfile(source, deck)
        pdf = temp / 'deck.pdf'
        if soffice:
            env = os.environ.copy()
            # macOS LibreOffice can miss installed fonts when its own Fontconfig has no config.
            matcher = shutil.which('fc-match')
            if sys.platform == 'darwin' and matcher and 'FONTCONFIG_FILE' not in env:
                config = Path(matcher).resolve().parents[1] / 'etc/fonts/fonts.conf'
                if not config.is_file():
                    config = Path(matcher).parents[1] / 'etc/fonts/fonts.conf'
                if config.is_file():
                    env['FONTCONFIG_FILE'] = str(config)
            subprocess.run([soffice, '-env:UserInstallation=' + (temp / 'profile').as_uri(),
                            '--headless', '--convert-to', 'pdf', '--outdir', str(temp), str(deck)],
                           check=True, timeout=120, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        elif Path('/Applications/Microsoft PowerPoint.app').exists() and shutil.which('osascript'):
            script = '''on run argv
 tell application "Microsoft PowerPoint"
  open POSIX file (item 1 of argv)
  set pres to active presentation
  save pres in POSIX file (item 2 of argv) as save as PDF
  close pres saving no
 end tell
end run'''
            subprocess.run(['osascript', '-', str(deck), str(pdf)], input=script, text=True,
                           check=True, timeout=120, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            raise ValueError('Install LibreOffice or Microsoft PowerPoint for PDF conversion')
        if not pdf.is_file() or not pdf.stat().st_size:
            raise ValueError('Converter produced no PDF')
        subprocess.run(['pdftoppm', '-jpeg', '-r', '150', str(pdf), str(temp / 'slide')],
                       check=True, timeout=120, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        images = sorted(temp.glob('slide-*.jpg'))
        if not images:
            raise ValueError('No slide images produced')
        output.mkdir()
        shutil.copyfile(pdf, output / (source.stem + '.pdf'))
        if shutil.which('pdffonts'):
            fonts = subprocess.run(['pdffonts', str(pdf)], check=True, capture_output=True, text=True, timeout=30)
            (output / 'fonts.txt').write_text(fonts.stdout)
        for file in images:
            shutil.copyfile(file, output / file.name)
        cards = ''.join(f'<figure><img src="{html.escape(f.name)}" alt="Slide {i}"><figcaption>Slide {i}</figcaption></figure>' for i, f in enumerate(images, 1))
        (output / 'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Slide review</title><style>body{font:18px system-ui;margin:2rem}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:1rem}figure{margin:0}img{width:100%}</style><h1>Slide review</h1><main>' + cards + '</main></html>')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path, nargs='?')
    args = parser.parse_args()
    try:
        print(render(args.input, args.output or args.input.with_name(args.input.stem + '-qa')))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        detail = getattr(error, 'stderr', None) or ''
        if isinstance(detail, bytes): detail = detail.decode(errors='replace')
        parser.exit(2, f'{error}\n{detail}')


if __name__ == '__main__':
    main()
