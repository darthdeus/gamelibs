#!/usr/bin/env python3
"""Copy upstream notices into each release prefix before it is archived."""
import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
COMMON = ('LICENSE-MIT', 'LICENSE-APACHE')
IMGUI = ('cimgui/LICENSE', 'cimgui/imgui/LICENSE.txt')
SOURCES = {
    'desktop': COMMON + IMGUI + (
        'luajit/COPYRIGHT',
        'SDL2-2.32.4/LICENSE.txt',
        'SDL2-2.32.4/src/hidapi/LICENSE-orig.txt',
        'SDL2-2.32.4/src/hidapi/LICENSE-bsd.txt',
        'SDL2-2.32.4/src/video/yuv2rgb/LICENSE',
        'freetype-2.14.1/LICENSE.TXT',
        'freetype-2.14.1/docs/FTL.TXT',
        'freetype-2.14.1/docs/GPLv2.TXT',
        'freetype-2.14.1/src/bdf/README',
        'freetype-2.14.1/src/pcf/README',
        'freetype-2.14.1/src/base/fthash.c',
        'freetype-2.14.1/src/gzip/zlib.h',
        'freetype-2.14.1/src/autofit/ft-hb-ft.c',
    ),
    'ios': COMMON + ('luajit/COPYRIGHT',),
    'bindings': COMMON + IMGUI + ('cimgui_love_generator/LICENSE.cimgui-love',),
}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=SOURCES)
    parser.add_argument('prefix', type=Path)
    args = parser.parse_args()
    for source in SOURCES[args.kind]:
        destination = args.prefix / 'licenses' / source
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / source, destination)
