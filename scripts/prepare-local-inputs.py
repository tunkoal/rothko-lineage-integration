#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Recreate private stock dependencies, then populate the three source checkouts."""
import argparse
import subprocess
import sys
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source-root', 'stock-dump', 'stock-artifacts', 'stock-images', 'staging-output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--apex-input', type=Path)
    a = p.parse_args()
    source = a.source_root.resolve(strict=True)
    dump = a.stock_dump.resolve(strict=True)
    stage = a.staging_output.resolve()
    integration = Path(__file__).resolve().parents[1]
    scripts = integration / 'scripts'
    device, vendor, kernel = [source / path for path in
                             ('device/xiaomi/rothko', 'vendor/xiaomi/rothko', 'device/xiaomi/rothko-kernel')]
    roots = [source, dump, a.stock_artifacts.resolve(strict=True), a.stock_images.resolve(strict=True)]
    if stage.exists() or any(stage.is_relative_to(root) for root in roots):
        raise ValueError('staging output must be new and outside source/stock inputs')
    stage.mkdir(parents=True, exist_ok=False)
    def run(*args):
        subprocess.run([sys.executable, *map(str, args)], check=True)
    run(device / 'extract-device-prebuilts.py', '--stock-dump', dump,
        '--patchelf', source / 'prebuilts/extract-tools/linux-x86/bin/patchelf-0_18',
        '--output', stage / 'device')
    extra = ['--apex-input', a.apex_input] if a.apex_input else []
    run(scripts / 'reproduce-stock-vendor.py', '--device', device, '--stock-dump', dump,
        '--extract-utils', source / 'tools/extract-utils',
        '--expected-payloads', integration / 'metadata/vendor-payload-lock.json',
        '--reference-metadata', vendor, '--output', stage / 'vendor', *extra)
    run(scripts / 'extract-kernel.py', '--recipe', kernel / 'extraction-recipe.json',
        '--stock-dump', dump, '--stock-artifacts', a.stock_artifacts,
        '--stock-images', a.stock_images, '--output', stage / 'kernel')
    run(scripts / 'populate-payloads.py', '--device', device, '--device-payloads', stage / 'device',
        '--vendor', vendor, '--vendor-payloads', stage / 'vendor',
        '--kernel', kernel, '--kernel-payloads', stage / 'kernel')
    print('Private input reconstruction complete. Do not commit extracted payloads.')


if __name__ == '__main__':
    main()
