"""Case 1: RF-spoiled gradient echo (FLASH). The baseline case.

Closely modelled on PyPulseq v1.5.0 ``examples/scripts/write_gre.py``. The
structure, variable names and parameter values are kept so that the difference
between this file and the upstream example is easy to see.

Deviations from the example, and why:

  * slice_thickness 3 mm -> 4 mm, to match the phantom slab (common.SLICE_THICKNESS)
  * system limits come from common.py, which takes the most conservative value
    across the three examples we follow, so one system is valid for all cases
  * FOV and matrix come from common.py
  * TE 5 ms -> 6 ms, because the shared system has a longer RF ringdown time
    (100 us instead of 20 us) and the original TE no longer fits

What this case probes: steady state over the echo train, RF and gradient
spoiling, and plain Cartesian gradient handling.

Run::

    python sequences/sequence_generators/write_case1_gre.py
    python sequences/sequence_generators/write_case1_gre.py --plot
"""

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pypulseq as pp

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import FOV, NX, NY, SLICE_THICKNESS, system, write_seq  # noqa: E402

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
alpha = 10  # [deg] flip angle
TR = 12e-3  # [s]
TE = 6e-3  # [s]
rf_spoiling_inc = 117  # [deg] RF spoiling phase increment


def main(plot: bool = False, write: bool = True, seq_filename: str = 'case1_gre.seq'):
    seq = pp.Sequence(system)

    # ======
    # CREATE EVENTS
    # ======
    rf, gz, gz_reph = pp.make_sinc_pulse(
        flip_angle=alpha * math.pi / 180,
        duration=3e-3,
        slice_thickness=SLICE_THICKNESS,
        apodization=0.42,
        time_bw_product=4,
        system=system,
        return_gz=True,
        delay=system.rf_dead_time,
        use='excitation',
    )

    # Readout, phase encoding and prewinders
    delta_k = 1 / FOV
    gx = pp.make_trapezoid(channel='x', flat_area=NX * delta_k, flat_time=3.2e-3, system=system)
    adc = pp.make_adc(num_samples=NX, duration=gx.flat_time, delay=gx.rise_time, system=system)
    gx_pre = pp.make_trapezoid(channel='x', area=-gx.area / 2, duration=1e-3, system=system)
    phase_areas = (np.arange(NY) - NY / 2) * delta_k

    # Gradient spoiling.
    gx_spoil = pp.make_trapezoid(channel='x', area=2 * NX * delta_k, system=system)
    gz_spoil = pp.make_trapezoid(channel='z', area=4 / SLICE_THICKNESS, system=system)

    # ======
    # TIMING
    # ======
    delay_TE = (
        math.ceil(
            (
                TE
                - (pp.calc_duration(gz, rf) - pp.calc_rf_center(rf)[0] - rf.delay)
                - pp.calc_duration(gx_pre)
                - pp.calc_duration(gx) / 2
                - pp.eps
            )
            / seq.grad_raster_time
        )
        * seq.grad_raster_time
    )
    delay_TR = (
        np.ceil(
            (TR - pp.calc_duration(gz, rf) - pp.calc_duration(gx_pre) - pp.calc_duration(gx) - delay_TE)
            / seq.grad_raster_time
        )
        * seq.grad_raster_time
    )

    assert np.all(delay_TE >= 0), f'TE too short by {-delay_TE * 1e3:.3f} ms'
    assert np.all(delay_TR >= pp.calc_duration(gx_spoil, gz_spoil)), 'TR too short for the spoilers'

    # ======
    # CONSTRUCT SEQUENCE
    # ======
    rf_phase = 0
    rf_inc = 0

    for i in range(NY):
        # RF spoiling: the phase increment itself grows by rf_spoiling_inc every TR.
        rf.phase_offset = rf_phase / 180 * np.pi
        adc.phase_offset = rf_phase / 180 * np.pi
        rf_inc = divmod(rf_inc + rf_spoiling_inc, 360.0)[1]
        rf_phase = divmod(rf_phase + rf_inc, 360.0)[1]

        seq.add_block(rf, gz)
        gy_pre = pp.make_trapezoid(
            channel='y',
            area=phase_areas[i],
            duration=pp.calc_duration(gx_pre),
            system=system,
        )
        seq.add_block(gx_pre, gy_pre, gz_reph)
        seq.add_block(pp.make_delay(delay_TE))
        seq.add_block(gx, adc)
        gy_pre.amplitude = -gy_pre.amplitude  # rewind the phase encode
        seq.add_block(pp.make_delay(delay_TR), gx_spoil, gy_pre, gz_spoil)

    print(f'GRE: {NY} TRs of {TR * 1e3:.1f} ms, TE {TE * 1e3:.1f} ms, alpha {alpha} deg')
    print(f'     matrix {NX} x {NY}, FOV {FOV * 1e3:.0f} mm, slice {SLICE_THICKNESS * 1e3:.0f} mm')

    if plot:
        seq.plot(time_range=(0.0, 2 * TR), stacked=True, show_guides=True)

    if write:
        write_seq(seq, Path(__file__).parent / seq_filename, 'case1_gre', NX, NY)

    return seq


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--plot', action='store_true', help='show the sequence diagram')
    p.add_argument('--no-write', action='store_true', help='do not write the .seq file')
    args = p.parse_args()
    main(plot=args.plot, write=not args.no_write)
