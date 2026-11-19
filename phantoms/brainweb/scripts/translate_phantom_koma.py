"""Write a KomaMRI ``.phantom`` by calling ``nifti_to_koma.py``.

The converter sits next to this file. This script picks the challenge slab
and forwards the discretisation.

Run::

    python phantoms/brainweb/scripts/translate_phantom_koma.py
    python phantoms/brainweb/scripts/translate_phantom_koma.py --t2star --spins-per-voxel 60
    python phantoms/brainweb/scripts/translate_phantom_koma.py phantoms/brainweb/challenge-brain-5mm.json \
        --out phantoms/brainweb/challenge-brain-5mm.phantom
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRAINWEB = HERE.parent
NIFTI_TO_KOMA = HERE / 'nifti_to_koma.py'
DENSITY_THRESHOLD = 1e-3


def phantom_path(t2star: bool = False) -> Path:
    """The published 5 mm slab. ``t2star=True`` keeps the published T2'."""
    name = 'challenge-brain-5mm-t2star.json' if t2star else 'challenge-brain-5mm.json'
    path = BRAINWEB / name
    if not path.is_file():
        raise SystemExit(f'{path} not found')
    return path


def export(phantom_json: Path, out: Path | None = None, spins_per_voxel: int = 1,
           density_threshold: float = DENSITY_THRESHOLD, seed: int = 0) -> Path:
    """Run the converter. ``seed`` is forwarded so a given spin count repeats."""
    if not NIFTI_TO_KOMA.is_file():
        raise SystemExit(f'missing {NIFTI_TO_KOMA}')
    if not phantom_json.is_file():
        raise SystemExit(f'not a file: {phantom_json}')
    out = phantom_json.with_suffix('.phantom') if out is None else out
    cmd = [
        sys.executable, str(NIFTI_TO_KOMA), str(phantom_json),
        '--out', str(out),
        '--name', phantom_json.stem,
        '--density-threshold', str(density_threshold),
        '--spins-per-voxel', str(spins_per_voxel),
        '--seed', str(seed),
    ]
    subprocess.run(cmd, check=True)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('phantom', nargs='?', type=Path, default=None,
                        help='BIfTI phantom JSON (default: the 5 mm challenge slab)')
    parser.add_argument('--t2star', action='store_true',
                        help="use the phantom that keeps the published T2' (case 4)")
    parser.add_argument('--spins-per-voxel', type=int, default=1,
                        help='spins per active voxel, forwarded to nifti_to_koma.py (default: 1)')
    parser.add_argument('--density-threshold', type=float, default=DENSITY_THRESHOLD,
                        help=f'drop voxels below this density (default: {DENSITY_THRESHOLD})')
    parser.add_argument('--seed', type=int, default=0,
                        help='RNG seed forwarded to nifti_to_koma.py (default: 0)')
    parser.add_argument('--out', type=Path, default=None,
                        help='output .phantom file (default: next to the JSON)')
    args = parser.parse_args()

    phantom = args.phantom if args.phantom is not None else phantom_path(t2star=args.t2star)
    export(phantom, args.out, args.spins_per_voxel, args.density_threshold, args.seed)


if __name__ == '__main__':
    main()
