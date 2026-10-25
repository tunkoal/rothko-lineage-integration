#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reproduce vendor payloads/rules from an unpacked stock dump or product tree.

Uses the real extract-utils parse/process/write APIs with DiskSource directly.
Build-tree mode maps recovery/root and accepts only explicit, separately verified
APK signing variants. It does not test extraction from an installed phone.
Does not unpack archives into the input, use ADB, or load existing vendor blobs.
"""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while data := stream.read(1024 * 1024):
            digest.update(data)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', type=Path, required=True)
    parser.add_argument('--stock-dump', '--input', dest='stock_dump', type=Path, required=True)
    parser.add_argument('--input-kind', choices=('stock', 'build-tree'), default='stock')
    parser.add_argument('--apex-input', type=Path,
                        help='Explicit prepared APEX root when INPUT/apex is an external symlink')
    parser.add_argument('--accepted-apk-variants', type=Path,
                        help='Explicit digest lock for separately verified signing-only build APK variants')
    parser.add_argument('--extract-utils', type=Path, required=True)
    parser.add_argument('--expected-payloads', type=Path, required=True)
    parser.add_argument('--reference-metadata', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    device, stock, reference, output = (p.resolve() for p in
        (args.device, args.stock_dump, args.reference_metadata, args.output))
    if not stock.is_dir() or output.exists() or any(output.is_relative_to(p)
                                                   for p in (device, stock, reference)):
        raise ValueError('Output must be new and outside the input directories')
    expected = json.loads(args.expected_payloads.read_text())['files']
    apex = args.apex_input.resolve(strict=True) if args.apex_input else None
    if apex is not None and (not apex.is_dir() or (stock / 'apex').resolve() != apex):
        raise ValueError('Explicit APEX root must match INPUT/apex')
    if apex is not None and output.is_relative_to(apex):
        raise ValueError('Output must be outside the explicit APEX input')
    if args.accepted_apk_variants and args.input_kind != 'build-tree':
        raise ValueError('Signing variants are only supported for an explicit build-tree input')
    variants = json.loads(args.accepted_apk_variants.read_text())['files'] if args.accepted_apk_variants else {}
    for path, variant in variants.items():
        if not path.endswith('.apk') or variant['expected_stock_sha256'] != expected.get(path):
            raise ValueError('Signing variant does not match the reviewed APK baseline')
    sys.path[:0] = [str(device), str(args.extract_utils.resolve())]
    from extract_utils.source import DiskSource
    from extract_utils.module import ProprietaryFileType
    spec = importlib.util.spec_from_file_location('stock_reproduction_device', device / 'extract-files.py')
    imported = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(imported)
    module = imported.module
    if len(module.proprietary_files) != 1 or module.rro_packages or module.postprocess_fns or module.extract_fns:
        raise ValueError('Unreviewed module hooks/layout')
    pf = module.proprietary_files[0]
    if pf.kind is not ProprietaryFileType.BLOBS or pf.pre_makefile_generation_fns or pf.post_makefile_generation_fns:
        raise ValueError('Only the reviewed plain blob list is supported')
    pf.file_list_path = str(device / 'proprietary-files.txt')
    module.device_path = str(device)
    module.vendor_path = str(output)
    module.vendor_rro_path = str(output / 'rro_overlays')
    module.parse(regenerate=False, section=None)
    selected = {file.dst for file in pf.file_list.files}
    if selected != set(expected):
        raise ValueError('Expected payload lock does not match the complete file list')
    output.mkdir(parents=True, exist_ok=False)
    # Bypass create_source/create_disk_source: those can unpack into the supplied
    # source directory. This workflow requires an already unpacked filesystem.
    copy_trace = {}

    class RecordingSource(DiskSource):
        def _copy_file_path(self, path, target):
            if args.input_kind == 'build-tree' and path.startswith('recovery/'):
                path = 'recovery/root/' + path.removeprefix('recovery/')
            candidate = (stock / path).resolve()
            if not (stock / path).is_file():
                return False
            allowed_apex = apex is not None and path.startswith('apex/') and candidate.is_relative_to(apex)
            if not candidate.is_relative_to(stock) and not allowed_apex:
                raise ValueError('Source copy escapes supplied input directory')
            copied = super()._copy_file_path(path, target)
            if copied:
                destination = Path(target).resolve().relative_to(output / 'proprietary').as_posix()
                if destination in copy_trace:
                    raise ValueError('More than one successful source copy for a destination')
                copy_trace[destination] = {'copied_source': path,
                                          'source_sha256': sha(Path(target)),
                                          'source_bytes': Path(target).stat().st_size}
            return copied

    source = RecordingSource(str(stock))
    copied = module.process(source, kang=False, no_cleanup=False,
                            extract_factory=False, section=None,
                            allow_prohibited_files=False)
    if not copied:
        raise RuntimeError('Not all payloads were extracted')
    module.write_makefiles(legacy=False, extract_factory=False)
    actual = {p.relative_to(output / 'proprietary').as_posix()
              for p in (output / 'proprietary').rglob('*') if p.is_file()}
    if actual != selected:
        raise RuntimeError('Extracted file set differs from the full list')
    if set(copy_trace) != selected:
        raise RuntimeError('Source-copy trace does not cover the complete selected list')
    files = {file.dst: file for file in pf.file_list.files}
    rows = []
    for index, path in enumerate(sorted(selected)):
        digest = sha(output / 'proprietary' / path)
        signing_variant = digest != expected[path] and variants.get(path, {}).get('sha256') == digest
        if digest != expected[path] and not signing_variant:
            raise RuntimeError(f'Extracted bytes differ from the reviewed payload: {path}')
        rows.append({'destination': path, 'sha256': digest,
                     'exact_stock_payload': digest == expected[path],
                     'declared_signing_only_variant': signing_variant,
                     'selection': str(files[path]), 'declared_source': files[path].src,
                     **copy_trace[path],
                     'source_to_output_changed': copy_trace[path]['source_sha256'] != digest,
                     'bytes': (output / 'proprietary' / path).stat().st_size})
        if (index + 1) % 500 == 0:
            print(f'Verified {index + 1} extracted payloads', flush=True)
    metadata = {}
    for name in ('Android.bp', 'Android.mk', 'rothko-vendor.mk', 'BoardConfigVendor.mk'):
        digest = sha(output / name)
        if digest != sha(reference / name):
            raise RuntimeError(f'Generated metadata differs: {name}')
        metadata[name] = digest
    report = {'state': 'unpacked-stock-vendor-reproduction-passed' if args.input_kind == 'stock'
              else 'build-tree-extraction-passed-with-explicit-variant-checks',
              'files': rows, 'count': len(rows), 'generated_metadata': metadata,
              'exact_stock_payload_count': sum(row['exact_stock_payload'] for row in rows),
              'declared_signing_variant_count': sum(row['declared_signing_only_variant'] for row in rows),
              'input_kind': args.input_kind,
              'source_copy_trace_complete': True,
              'explicit_external_apex_input': apex is not None,
              'existing_vendor_payloads_used': False,
              'prohibited_file_checks_enabled': True,
              'archive_unpacking_tested': False, 'installed_lineage_extraction_tested': False,
              'image_metadata_verified': False, 'compiled': False}
    (output / 'reproduction-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASSED: {len(rows)} payloads and four generated metadata files verified; '
          f'{report["declared_signing_variant_count"]} declared signing variants')


if __name__ == '__main__':
    main()
