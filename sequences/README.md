# Sequences

Four Pulseq 1.5.0 files, with no extensions beyond LABEL. Case 4 uses `case3_epi.seq` again. Every participant simulates these files unchanged. The scripts that wrote them are in [sequence_generators/](sequence_generators/). 


| Case | File            | Sequence                         | Phantom            | Samples | What it probes                                         |
| ---- | --------------- | -------------------------------- | ------------------ | ------- | ------------------------------------------------------ |
| 0    | `case0_fid.seq` | FID, no readout gradient         | 5 mm slab          | 1024    | Sign, conjugation and scaling conventions              |
| 1    | `case1_gre.seq` | GRE / FLASH, RF-spoiled          | `T2' = inf`        | 4096    | Steady state, spoiling, gradient handling              |
| 2    | `case2_tse.seq` | TSE, 4 shots × 16 echoes         | `T2' = inf`        | 4096    | Refocusing, stimulated echoes, coherence pathways      |
| 3    | `case3_epi.seq` | EPI, single shot, 43.5 ms train  | `T2' = inf`        | 4096    | Gradient raster and timing, off-resonance accumulation |
| 4    | `case3_epi.seq` | EPI (identical `.seq` to case 3) | `T2'` as published | 4096    | Intra-voxel dephasing / T2* modelling                  |




Which phantom each sequence is paired with is in the [Cases](../README.md#cases) section of the repository README. Cases 3 and 4 run the same sequence file. The only variable is the phantom's `T2'`, so the difference between a tool's case 3 and case 4 result is its T2* model, isolated from everything else. The phantom files are described in [../phantoms/brainweb/README.md](../phantoms/brainweb/README.md).

Published scanner constants. Gamma is the shielded-proton NIST value to four digits, the same number as the BIfTI phantom `system.gyro`.

- B0 = 3.0 T, gamma = 42.5764 MHz/T, Larmor = 127.7292 MHz
- FOV 256 mm, matrix 64 × 64, slice thickness 5 mm
- max gradient 28 mT/m, max slew 130 T/m/s
- RF dead time 100 µs, RF ringdown 100 µs, ADC dead time 10 µs

`B0` is also written into each `.seq` file's `[DEFINITIONS]` block. Do not infer a different gamma.