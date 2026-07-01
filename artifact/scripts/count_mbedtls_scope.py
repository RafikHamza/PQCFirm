#!/usr/bin/env python3
"""Count Mbed TLS library scope used by PQCFirm large-library evaluation."""
from __future__ import annotations

import json
from pathlib import Path


def count_lines(path: Path) -> int:
    try:
        return len(path.read_text(encoding='utf-8', errors='ignore').splitlines())
    except Exception:
        return 0


def main() -> int:
    artifact_dir = Path(__file__).resolve().parents[1]
    mbed_root = artifact_dir / 'embedded' / 'mbedtls'
    library = mbed_root / 'library'
    results = artifact_dir / 'results'
    results.mkdir(parents=True, exist_ok=True)
    out = results / 'mbedtls_library_scope.json'

    if not library.exists():
        data = {
            'status': 'NOT_AVAILABLE',
            'scope': 'embedded/mbedtls/library',
            'reason': 'Mbed TLS library directory is not present. Run ensure_mbedtls.py first or include the vendored source snapshot.'
        }
        out.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        print(f'Mbed TLS library scope not available: {library}')
        return 0

    c_files = sorted(library.rglob('*.c'))
    h_files = sorted(library.rglob('*.h'))
    c_lines = sum(count_lines(p) for p in c_files)
    h_lines = sum(count_lines(p) for p in h_files)
    data = {
        'status': 'AVAILABLE',
        'scope': 'embedded/mbedtls/library',
        'c_translation_units': len(c_files),
        'header_files': len(h_files),
        'c_and_header_files': len(c_files) + len(h_files),
        'raw_c_source_lines': c_lines,
        'raw_header_lines': h_lines,
        'raw_c_and_header_lines': c_lines + h_lines,
        'interpretation': 'Raw physical line counts for the Mbed TLS library folder used as the large-library scan scope.'
    }
    out.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    print(f"Mbed TLS library scope: {len(c_files)} C translation units, {c_lines} raw C source lines")
    print(f'Wrote scope summary: {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
