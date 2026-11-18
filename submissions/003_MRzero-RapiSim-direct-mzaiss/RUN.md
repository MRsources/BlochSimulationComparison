# MRzero plugin / RapiSim direct-sampler submission

Five cases were run through the MRzero ChatGPT plugin's `rapisim_simulate`
service on 2026-10-27, for GitHub user `mzaiss`, with ChatGPT assistance.
These are new service runs, not copies of an existing challenge entry.

## Inputs and settings

Inputs are pinned to challenge commit
`4c0d86e74aebf56d2e27b69c1f273483d4b7dbb9`. All four Pulseq files,
the two phantom JSON files, and their referenced density/off-resonance NIfTIs
were checked against the repository blob hashes. Their SHA-256 hashes are
recorded in `provenance.json`.

The original 181 x 217 x 4 phantom grid and NIfTI world placement are retained;
there is no resampling. Each ZIP contains one original JSON and the two
referenced NIfTIs, without modifying their contents. The unreferenced B1+ map
is not included. The service supplies the BIfTI defaults for missing
properties: B1+ = B1- = 1, ADC = 0, and T2' = infinity for cases 0-3.
Case 4 uses the published T2' values. The phantom's B0 = 3 T and
gyro = 42.5764 MHz/T, and the original Pulseq definitions, are retained.
The tool does not offer a separate scanner-constant override.

| Cases | Sampler | `min_mag` | `compute_signal_stats` |
|---|---|---:|---|
| 0, 1, 3, 4 | direct | 1e-7 | true |
| 2 | direct | 1e-10 | true |

The direct sampler does not use the interpolation kernel setting.
The service returns one coil, with shape `(samples, 1)` and dtype
`complex128`. Export removes only the singleton coil dimension and writes
the complex dataset `signal`. No normalization, conjugation, phase change,
filtering, sample reordering, or reconstruction is applied.

The backend version/commit, hardware, RF discretization, internal time step,
and compute timings were not reported. `tool_date` identifies the run;
version, hardware, and timing fields are left empty/null. No relative speed
claim is made. Backend upgrades may change a future rerun.

## Reproduce the preparation and export

`reproduce.py` prepares inputs and exports service results. It is not a
local RapiSim implementation and does not execute the remote simulation.
Run from the repository root; Python 3.12, NumPy, and h5py were used.

```sh
python -m pip install numpy h5py
python submissions/MRzero-RapiSim-direct-mzaiss/reproduce.py prepare --output-dir /tmp/rapisim-inputs
```

This verifies all input hashes, creates deterministic phantom ZIPs, and
writes `simulation_calls.json`. Upload those ZIPs and the four unchanged
`.seq` files using the MRzero plugin's file upload tools. Check that the
returned hashes match `provenance.json`, then invoke `rapisim_simulate`
once per recorded case with the exact `arguments` object in that manifest.

Save each returned signal as `caseN_signal.npy` in one directory, then run:

```sh
python submissions/MRzero-RapiSim-direct-mzaiss/reproduce.py export --signals-dir /tmp/rapisim-signals --output-dir /tmp/rapisim-h5
```

Alternatively, add `--download` to retrieve the recorded results from the
service CAS URLs. Those URLs may not remain available indefinitely; the
submitted HDF5 files preserve the full raw signals. The exporter verifies
the recorded SHA-256 hashes, shapes, types, finite values, and lossless HDF5
round trip. A future backend run that produces different bytes will fail
the original checksum check and needs its own updated provenance.

## Validation

All five signals are finite and nonzero. Case 0 has 1024 samples and cases
1-4 have 4096. In every submitted run, summing the five per-tissue signal
contributions exactly reproduces the total signal. The HDF5 values are
identical to the downloaded NumPy values.

Cases 0, 1, 3, and 4 produced byte-identical outputs at cutoffs 1e-6 and 1e-7.
TSE was checked at 1e-6, 1e-7, 1e-8, 1e-9, 1e-10, and 1e-11. Its 1e-10
and 1e-11 outputs have identical content hashes; the submitted result uses
1e-10. Intermediate relative L2 differences and output hashes are recorded
in `provenance.json`. This checks cutoff sensitivity, not agreement with an
independent physics ground truth.

The challenge's validator can be run with:

```sh
python .github/scripts/validate_submission.py submissions/MRzero-RapiSim-direct-mzaiss
```
