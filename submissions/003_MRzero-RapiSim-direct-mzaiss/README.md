# MRzero plugin / RapiSim (direct)

`003_MRzero-RapiSim-direct-mzaiss`

- Group: mzaiss
- Date: 2026-10-27
- Solver: RapiSim, direct sampler; min_mag=1e-7 for cases 0,1,3,4 and 1e-10 for case 2; compute_signal_stats=true

## Setup notes

Run through the MRzero ChatGPT plugin. Unmodified challenge inputs at commit 4c0d86e74aebf56d2e27b69c1f273483d4b7dbb9; native 181x217x4 grid, no resampling. Phantom B0=3 T and gyro=42.5764 MHz/T retained. Defaults: B1+=B1-=1, ADC=0, T2 prime infinite unless specified. Raw complex128 output is preserved with only the singleton coil axis removed. State-cutoff checks and input/output hashes are in provenance.json. Backend version, commit, hardware, and compute timings are not exposed; tool_date records the run, and timings remain null. Prepared with ChatGPT assistance.
