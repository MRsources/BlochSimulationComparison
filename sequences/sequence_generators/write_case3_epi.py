"""Case 3 and case 4: single-shot EPI without ramp sampling.

Closely modelled on PyPulseq v1.5.0 ``examples/scripts/write_epi.py`` (the
example's own description is "demo low-performance EPI sequence without
ramp-sampling"). Structure, variable names and parameter values follow the
example so the difference is easy to see.

Deviations from the example, and why:

  * n_slices 3 -> 1. With a single slice the example's rf.freq_offset works out
    to zero, so the slice loop and the offset are dropped instead of being
    carried along as no-ops.
  * slice_thickness 3 mm -> 4 mm, to match the phantom slab
  * fov 220 mm -> 256 mm (from common.py). At 220 mm the 217 mm wide BrainWeb
    phantom would fold over in the phase encode direction.
  * system limits come from common.py

**One .seq file, two cases.** Case 3 simulates this sequence on the phantom with
T2' = inf; case 4 simulates the byte-identical file on the phantom that keeps the
published T2'. The only variable is the phantom, so the difference between a
tool's case 3 and case 4 result is its intra-voxel dephasing model, isolated.

What this case probes: gradient raster and timing under a long echo train, and
accumulation of off-resonance (the phantom's dB0 map, including the fat
chemical shift at -440 Hz) across that train.

Run::

    python sequences/sequence_generators/write_case3_epi.py
    python sequences/sequence_generators/write_case3_epi.py --plot
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pypulseq as pp

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import FOV, NX, NY, SLICE_THICKNESS, system, write_seq  # noqa: E402

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
# 5 µs, not 4: 64 samples then last 320 µs, which sits on the 10 µs gradient
# raster and on the 100 ns ADC raster. 4 µs does not.
dwell_time = 5e-6  # [s] ADC dwell
pre_time = 8e-4  # [s] duration of the prewinder block


def main(plot: bool = False, write: bool = True, seq_filename: str = 'case3_epi.seq'):
    seq = pp.Sequence(system)

    # ======
    # CREATE EVENTS
    # ======
    # The rephaser returned here is discarded: like the example, we build our own
    # below so that it shares the prewinder block's duration.
    rf, gz, _ = pp.make_sinc_pulse(
        flip_angle=np.pi / 2,
        duration=3e-3,
        slice_thickness=SLICE_THICKNESS,
        apodization=0.5,
        time_bw_product=4,
        system=system,
        return_gz=True,
        delay=system.rf_dead_time,
        use='excitation',
    )

    # The ADC occupies the whole flat top, so both readout polarities sample
    # kx = -31.5 ... +31.5. delay is the rise time: that is where the flat starts.
    delta_k = 1 / FOV
    k_width = NX * delta_k
    gx = pp.make_trapezoid(
        channel='x', system=system, flat_area=k_width, flat_time=NX * dwell_time,
    )
    adc = pp.make_adc(
        num_samples=NX, duration=gx.flat_time, delay=gx.rise_time, system=system,
    )

    # Prewinders: move to the corner of k-space.
    gx_pre = pp.make_trapezoid(channel='x', system=system, area=-gx.area / 2, duration=pre_time)
    gz_reph = pp.make_trapezoid(channel='z', system=system, area=-gz.area / 2, duration=pre_time)
    gy_pre = pp.make_trapezoid(channel='y', system=system, area=-NY / 2 * delta_k, duration=pre_time)

    # Phase blip, in the shortest time the slew rate allows.
    dur = np.ceil(2 * np.sqrt(delta_k / system.max_slew) / 10e-6) * 10e-6
    gy = pp.make_trapezoid(channel='y', system=system, area=delta_k, duration=dur)

    # ======
    # CONSTRUCT SEQUENCE
    # ======
    seq.add_block(rf, gz)
    seq.add_block(gx_pre, gy_pre, gz_reph)
    for _ in range(NY):
        seq.add_block(gx, adc)  # read one line of k-space
        seq.add_block(gy)  # phase blip
        gx.amplitude = -gx.amplitude  # reverse the readout polarity

    echo_spacing = pp.calc_duration(gx) + pp.calc_duration(gy)
    print(f'EPI: single shot, {NY} lines, echo spacing {echo_spacing * 1e6:.0f} us')
    print(f'     train length {NY * echo_spacing * 1e3:.1f} ms, dwell {gx.flat_time / NX * 1e6:.3f} us')
    print(f'     matrix {NX} x {NY}, FOV {FOV * 1e3:.0f} mm, slice {SLICE_THICKNESS * 1e3:.0f} mm')

    if plot:
        seq.plot()

    if write:
        write_seq(seq, Path(__file__).parent / seq_filename, 'case3_epi', NX, NY)

    return seq


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--plot', action='store_true', help='show the sequence diagram')
    p.add_argument('--no-write', action='store_true', help='do not write the .seq file')
    args = p.parse_args()
    main(plot=args.plot, write=not args.no_write)
