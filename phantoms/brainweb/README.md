# Phantoms

One 5 mm BrainWeb slab on the sequence grid: the centred 1 mm crop, resampled to 64 × 64 over the 256 mm field of view. The NIfTI sform is the world placement.


|                  |                                                            |
| ---------------- | ---------------------------------------------------------- |
| Slab             | 64 × 64 × 5 voxels, 4 mm in plane, 1 mm slices             |
| Voxel-to-world   | `[[4, 0, 0, -126], [0, 4, 0, -126], [0, 0, 1, -2]]` mm     |
| z planes         | −2, −1, 0, +1, +2 mm                                       |
| Tissues          | gm, wm, csf, vessels, fat                                  |
| Non-empty voxels | 8 681 of 20 480                                            |



| File                              | What it is                                                               |
| --------------------------------- | ------------------------------------------------------------------------ |
| `challenge-brain-5mm.json`        | Cases 0–3. `T2'` left out, so it is treated as infinite.                 |
| `challenge-brain-5mm-t2star.json` | Case 4. The same tissues, with the published `T2'`.                      |
| `subj05.nii.gz`                   | Densities for gm, wm, csf, vessels and fat.                              |
| `subj05_dB0.nii.gz`               | Shared off-resonance map. The JSON subtracts 440 Hz for fat.             |
| `subj05_B1+.nii.gz`               | Transmit map on the same grid. The challenge JSON does not reference it. |


The two JSON files differ only in `T2'`, which is what makes case 4 a T2* test. `T1`, `T2` and `dB0` are the published values. `subj05_dB0.nii.gz` is the same unshifted map for every tissue. The fat chemical shift of −440 Hz is applied by the JSON (`x - 440`) and is not stored in the NIfTI. `B1+`, `B1-` and `ADC` are the BIfTI defaults (uniform 1, uniform 1, and 0). Those defaults are already written into the JSON, so every solver is given the same object.

The slab is centred on the world origin. Tissue order in `subj05.nii.gz` is the order named in the JSON. `subj05_dB0.nii.gz` is the shared off-resonance map; the fat chemical shift of −440 Hz is applied by the JSON. [scripts/](scripts/) converts this slab to a KomaMRI phantom. 