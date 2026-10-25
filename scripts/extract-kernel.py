#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Copy only hash-pinned stock kernel artifacts to a new private directory."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def relative(value):
    p = PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or str(p) in ('', '.'):
        raise ValueError('unsafe relative path')
    return Path(str(p))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe', type=Path, required=True)
    parser.add_argument('--stock-dump', type=Path, required=True)
    parser.add_argument('--stock-artifacts', type=Path, required=True)
    parser.add_argument('--stock-images', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    roots = {key: getattr(args, 'stock_' + key).resolve(strict=True)
             for key in ('dump', 'artifacts', 'images')}
    output = args.output.resolve()
    if output.exists() or any(output.is_relative_to(root) for root in roots.values()):
        raise ValueError('output must be new and outside inputs')
    recipe = json.loads(args.recipe.read_text())
    if recipe['schema_version'] != 1:
        raise ValueError('unsupported recipe')
    plan, seen = [], set()
    for row in recipe['files']:
        target = relative(row['path'])
        if str(target) in seen:
            raise ValueError('duplicate target')
        seen.add(str(target))
        root = roots[row['input']]
        source = (root / relative(row['source'])).resolve(strict=True)
        if not source.is_relative_to(root) or not source.is_file():
            raise ValueError('source escapes selected input')
        if digest(source) != row['sha256'] or source.stat().st_size != row['bytes']:
            raise ValueError('stock input differs: ' + row['path'])
        if row['mode'] not in ('0644', '0755'):
            raise ValueError('unsupported mode')
        plan.append((source, target, row))
    output.mkdir(parents=True, exist_ok=False)
    for source, target, row in plan:
        dest = output / target
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(source.read_bytes())
        if digest(dest) != row['sha256']:
            raise ValueError('source changed during copy')
        dest.chmod(int(row['mode'], 8))
    (output / 'extraction-report.json').write_text(json.dumps({
        'firmware': recipe['firmware'], 'files_verified': len(plan),
        'source_built_kernel': False, 'bootloader_operations': False,
    }, indent=2) + '\n')
    print(f'Verified {len(plan)} stock kernel artifacts; no kernel compilation or phone access')


if __name__ == '__main__':
    main()
