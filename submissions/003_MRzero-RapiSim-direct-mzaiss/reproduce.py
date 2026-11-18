"""Prepare exact inputs and export MRzero plugin results; not a local solver.

Requires numpy and h5py for export. See RUN.md for the service simulation step.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def checked_bytes(path: Path, expected: str) -> bytes:
    data = path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch for {path}: {actual} != {expected}")
    return data


def prepare(manifest: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name, digest in manifest["input_sha256"].items():
        checked_bytes(ROOT / name, digest)
    for archive in manifest["phantom_archives"]:
        target = output / archive["file_name"]
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as handle:
            for name in archive["members"]:
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = 0o644 << 16
                handle.writestr(info, (ROOT / "phantoms/brainweb" / name).read_bytes())
        checked_bytes(target, archive["sha256"])
        print(f"Verified {target}: {archive['sha256']}")
    calls = [{"case": run["case"], "tool": manifest["tool"], "arguments": run["arguments"]}
             for run in manifest["runs"]]
    (output / "simulation_calls.json").write_text(json.dumps(calls, indent=2) + "\n")
    print("Upload the archives and original .seq files through the MRzero plugin,")
    print("then execute the recorded calls in simulation_calls.json.")


def export(manifest: dict, signals: Path, output: Path, download: bool) -> None:
    import h5py
    import numpy as np

    signals.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    for run in manifest["runs"]:
        case = run["case"]
        source = signals / f"case{case}_signal.npy"
        artifact = run["output_signal"]
        if download:
            with urllib.request.urlopen(artifact["url"], timeout=120) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != artifact["sha256"]:
                raise ValueError(f"Downloaded signal checksum mismatch for case {case}")
            source.write_bytes(data)
        checked_bytes(source, artifact["sha256"])
        raw = np.load(source, allow_pickle=False)
        count = 1024 if case == 0 else 4096
        if raw.shape != (count, 1) or raw.dtype != np.dtype("complex128"):
            raise ValueError(f"Unexpected signal shape/dtype: {raw.shape}, {raw.dtype}")
        if not np.isfinite(raw).all() or not np.any(raw):
            raise ValueError(f"Nonfinite or all-zero signal for case {case}")
        # The service returns (samples, coils); the published phantom has one coil.
        # Remove only the singleton coil dimension. Preserve values and ADC order.
        signal = raw[:, 0]
        target = output / f"case{case}.h5"
        with h5py.File(target, "w") as handle:
            handle.create_dataset("signal", data=signal, track_times=False)
        with h5py.File(target, "r") as handle:
            if not np.array_equal(handle["signal"][()], signal):
                raise ValueError(f"HDF5 round-trip changed the signal for case {case}")
        print(f"Exported {target}: complex128, {count} finite samples")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare", help="verify inputs, make ZIPs, list service calls")
    prep.add_argument("--output-dir", type=Path, required=True)
    exp = sub.add_parser("export", help="export the recorded service results to HDF5")
    exp.add_argument("--signals-dir", type=Path, required=True)
    exp.add_argument("--output-dir", type=Path, default=HERE)
    exp.add_argument("--download", action="store_true", help="retrieve recorded CAS results")
    args = parser.parse_args()
    manifest = json.loads((HERE / "provenance.json").read_text())
    if args.command == "prepare":
        prepare(manifest, args.output_dir)
    else:
        export(manifest, args.signals_dir, args.output_dir, args.download)


if __name__ == "__main__":
    main()
