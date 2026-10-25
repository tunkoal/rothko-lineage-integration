#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Populate only declared extracted payloads; reject all conflicting files first."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def rel(value):
    p = PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or str(p) in ('', '.'):
        raise ValueError('unsafe relative path')
    return Path(str(p))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('device', 'vendor', 'kernel'):
        p.add_argument('--' + key, type=Path, required=True)
        p.add_argument('--' + key + '-payloads', type=Path, required=True)
    p.add_argument('--verify-only', action='store_true')
    a = p.parse_args()
    device, vendor, kernel = [getattr(a, key).resolve(strict=True) for key in ('device', 'vendor', 'kernel')]
    rows = []
    rows += [('device', row['destination'], row['output_sha256'], int(row['mode'], 8))
             for row in json.loads((device / 'device-prebuilts.json').read_text())['files']]
    vendor_modes = json.loads((vendor / 'payload-modes.json').read_text())
    rows += [('vendor', 'proprietary/' + row['destination'], row['extracted_sha256'],
              int(vendor_modes['proprietary/' + row['destination']], 8))
             for row in json.loads((vendor / 'PUBLIC_PROVENANCE.json').read_text())['files']]
    rows += [('kernel', row['path'], row['sha256'], int(row['mode'], 8))
             for row in json.loads((kernel / 'extraction-recipe.json').read_text())['files']]
    roots = {'device': device, 'vendor': vendor, 'kernel': kernel}
    inputs = {key: getattr(a, key + '_payloads').resolve(strict=True) for key in roots}
    plan, seen = [], set()
    for key, path, expected, mode in rows:
        relative = rel(path)
        if '.git' in relative.parts or (key == 'device' and relative.parts[0] != 'prebuilts') \
                or (key == 'vendor' and relative.parts[0] != 'proprietary'):
            raise ValueError('target is outside the declared payload layout')
        if (key, path) in seen:
            raise ValueError('duplicate target')
        seen.add((key, path))
        if mode not in (0o644, 0o755):
            raise ValueError('unsupported payload mode')
        source = (inputs[key] / rel(path)).resolve(strict=True)
        target = roots[key] / rel(path)
        if not source.is_relative_to(inputs[key]) or not source.is_file():
            raise ValueError('payload source escapes root')
        if not target.resolve().is_relative_to(roots[key]) or target.is_symlink():
            raise ValueError('payload target escapes root or is a symlink')
        if sha(source) != expected:
            raise ValueError('extracted payload differs: ' + path)
        if target.exists() and (not target.is_file() or sha(target) != expected):
            raise ValueError('conflicting checkout file: ' + path)
        plan.append((source, target, expected, mode))
    if not a.verify_only:
        for source, target, expected, mode in plan:
            if target.exists():
                if target.is_symlink() or not target.is_file() or sha(target) != expected:
                    raise ValueError('target changed after preflight')
                target.chmod(mode)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            # Do not overwrite a file that appeared after preflight.
            with target.open('xb') as f:
                f.write(source.read_bytes())
            if sha(target) != expected:
                raise ValueError('source changed during populate')
            target.chmod(mode)
    print(f'{"Verified" if a.verify_only else "Populated"} {len(plan)} declared payloads; existing matching files retained')


if __name__ == '__main__':
    main()
