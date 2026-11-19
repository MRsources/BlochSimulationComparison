# Phantoms

One 4 mm BrainWeb slab, cropped from the public [BIfTI registry](https://github.com/mrx-org/bifti-phantoms) BrainWeb 1 mm collection (`collection-brainweb-1mm`, Zenodo DOI `10.5281/zenodo.21822442`, tissue data `subj05-3T-1mm.json`). The NIfTI sform is the world placement. 


|                  |                                                         |
| ---------------- | ------------------------------------------------------- |
| Slab             | 181 × 217 × 4 voxels, 1 mm isotropic                    |
| Voxel-to-world   | `[[1, 0, 0, -90], [0, 1, 0, -108], [0, 0, 1, -1.5]]` mm |
| z planes         | −1.5, −0.5, +0.5, +1.5 mm                               |
| Tissues          | gm, wm, csf, vessels, fat                               |
| Non-empty voxels | 97 653 of 157 108                                       |



| File                              | What it is                                                               |
| --------------------------------- | ------------------------------------------------------------------------ |
| `challenge-brain-4mm.json`        | Cases 0–3. `T2'` left out, so it is treated as infinite.                 |
| `challenge-brain-4mm-t2star.json` | Case 4. The same tissues, with the published `T2'`.                      |
| `subj05.nii.gz`                   | Densities for gm, wm, csf, vessels and fat.                              |
| `subj05_dB0.nii.gz`               | Shared off-resonance map. The JSON subtracts 440 Hz for fat.             |
| `subj05_B1+.nii.gz`               | Transmit map on the same grid. The challenge JSON does not reference it. |


The two JSON files differ only in `T2'`, which is what makes case 4 a T2* test. `T1`, `T2` and `dB0` are the published values. `subj05_dB0.nii.gz` is the same unshifted map for every tissue. The fat chemical shift of −440 Hz is applied by the JSON (`x - 440`) and is not stored in the NIfTI. `B1+`, `B1-` and `ADC` are the BIfTI defaults (uniform 1, uniform 1, and 0). Those defaults are already written into the JSON, so every solver is given the same object.

The slab is centred on the world origin. [scripts/](scripts/) is the crop that wrote it, and the conversion of this slab to a KomaMRI phantom. 