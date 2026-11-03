"""Case 2: turbo spin echo (TSE), 16 echoes.

Closely modelled on PyPulseq v1.5.0 ``examples/scripts/write_tse.py``.

Deviations from the example, and why:

  * slice_thickness 5 mm -> 4 mm, to match the phantom slab
  * n_slices is dropped (the example already ran with n_slices = 1, so the slice
    loop and its freq_offset arithmetic were no-ops)
  * FOV, matrix and system limits come from common.py (only max_grad differs
    from the example, 28 instead of 32 mT/m)
  * the example reuses the names ``t_ex`` and ``t_ref`` for two different
    quantities -- first the RF durations, then the total block-group durations.
    Here the second use is renamed to ``t_ex_block`` / ``t_ref_block``. Same
    numbers, one less way to misread the timing arithmetic.

What this case probes: refocusing, stimulated echoes and coherence pathway
bookkeeping.

Block structure
---------------
The slice-select gradient has to run continuously across block boundaries, so
it is cut into pieces and re-spliced as extended trapezoids. The names encode
the block position within one echo period, which is what makes the wall of
``gs1``..``gs7`` / ``gr3``..``gr7`` readable:

    block:        1       2       3    |     4       5       6       7
    role:       ramp     exc    crush  |   refoc   crush    read    crush
    ------------------------------------------------------------------------
    slice  gz:   gs1     gs2     gs3   |    gs4     gs5      --      gs7
    read   gx:    --      --     gr3   |     --     gr5     gr6      gr7
    phase  gy:    --      --      --   |     --   gp_pre     --    gp_rew

Blocks 1-3 happen once per shot; blocks 4-7 repeat once per echo. There is no
``gr1``/``gr2`` (no readout gradient that early) and no ``gs6`` (the slice
gradient is zero during the readout). Each piece starts at the amplitude the
previous one ended on, which is what keeps the waveform continuous:

    gs1: 0            -> gs_ex        ramp up
    gs2: gs_ex        -> gs_ex        flat, excitation sits here
    gs3: gs_ex  -> gs_spex -> gs_ref  crusher between excitation and refocusing
    gs4: gs_ref       -> gs_ref       flat, refocusing sits here
    gs5: gs_ref -> gs_spr  -> 0       crusher, ramping down for the readout
    gs7: 0      -> gs_spr  -> gs_ref  crusher, ramping back up for the next echo

Run::

    python sequences/sequence_generators/write_case2_tse.py
    python sequences/sequence_generators/write_case2_tse.py --plot
"""

import argparse
import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pypulseq as pp

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import FOV, NX, NY, SLICE_THICKNESS, system, write_seq  # noqa: E402

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
n_echo = 16  # echoes per shot (turbo factor)
rf_flip = 180  # [deg] refocusing flip angle
TE = 12e-3  # [s] echo spacing
TR = 2000e-3  # [s]

dG = 250e-6  # [s] ramp time used for every gradient built here
sampling_time = 6.4e-3  # [s] pure ADC time
t_ex = 2.5e-3  # [s] excitation pulse duration
t_ref = 2e-3  # [s] refocusing pulse duration
fsp_r = 1  # readout spoiler area, in units of the readout gradient area
fsp_s = 0.5  # slice spoiler area, in units of half the excitation slice area

rf_ex_phase = np.pi / 2  # CPMG: excitation and refocusing are 90 deg apart
rf_ref_phase = 0


def main(plot: bool = False, write: bool = True, seq_filename: str = 'case2_tse.seq'):
    seq = pp.Sequence(system)

    flip_ref = np.full(n_echo, rf_flip, dtype=float)

    # Widths including RF dead and ringdown time: the gradient flat top must
    # cover the whole RF event, not just its waveform.
    readout_time = sampling_time + 2 * system.adc_dead_time
    t_exwd = t_ex + system.rf_ringdown_time + system.rf_dead_time
    t_refwd = t_ref + system.rf_ringdown_time + system.rf_dead_time
    t_sp = 0.5 * (TE - readout_time - t_refwd)
    t_spex = 0.5 * (TE - t_exwd - t_refwd)

    # ======
    # CREATE EVENTS
    # ======
    rf_ex, gz, _ = pp.make_sinc_pulse(
        flip_angle=np.pi / 2,
        system=system,
        duration=t_ex,
        slice_thickness=SLICE_THICKNESS,
        apodization=0.5,
        time_bw_product=4,
        phase_offset=rf_ex_phase,
        return_gz=True,
        delay=system.rf_dead_time,
        use='excitation',
    )
    gs_ex = pp.make_trapezoid(
        channel='z', system=system, amplitude=gz.amplitude, flat_time=t_exwd, rise_time=dG
    )

    rf_ref, gz, _ = pp.make_sinc_pulse(
        flip_angle=flip_ref[0] * np.pi / 180,
        system=system,
        duration=t_ref,
        slice_thickness=SLICE_THICKNESS,
        apodization=0.5,
        time_bw_product=4,
        phase_offset=rf_ref_phase,
        return_gz=True,
        delay=system.rf_dead_time,
        use='refocusing',
    )
    # As in the example, the refocusing slice gradient reuses the excitation
    # amplitude rather than the one make_sinc_pulse derived for it. The two
    # pulses have different durations, so their nominal slabs differ slightly.
    gs_ref = pp.make_trapezoid(
        channel='z', system=system, amplitude=gs_ex.amplitude, flat_time=t_refwd, rise_time=dG
    )

    ags_ex = gs_ex.area / 2
    gs_spr = pp.make_trapezoid(
        channel='z', system=system, area=ags_ex * (1 + fsp_s), duration=t_sp, rise_time=dG
    )
    gs_spex = pp.make_trapezoid(
        channel='z', system=system, area=ags_ex * fsp_s, duration=t_spex, rise_time=dG
    )

    delta_k = 1 / FOV
    k_width = NX * delta_k

    # flat_area is the k-space span of the samples, so the flat time is the ADC
    # window. readout_time is longer by a dead-time margin on each side.
    gr_acq = pp.make_trapezoid(
        channel='x', system=system, flat_area=k_width, flat_time=sampling_time, rise_time=dG
    )
    adc = pp.make_adc(
        num_samples=NX, duration=sampling_time, delay=system.adc_dead_time, system=system
    )
    gr_spr = pp.make_trapezoid(
        channel='x', system=system, area=gr_acq.area * fsp_r, duration=t_sp, rise_time=dG
    )

    # The ADC delay is the dead time, so the echo (k = 0) is that much
    # after the start of the flat top. The prephaser has to include it.
    agr_preph = gr_acq.area / 2 + gr_spr.area + gr_acq.amplitude * system.adc_dead_time
    gr_preph = pp.make_trapezoid(
        channel='x', system=system, area=agr_preph, duration=t_spex, rise_time=dG
    )

    # Phase encoding order: n_ex shots, each covering n_echo lines.
    n_ex = math.floor(NY / n_echo)
    pe_steps = np.arange(1, n_echo * n_ex + 1) - 0.5 * n_echo * n_ex - 1
    if n_echo % 2 == 0:
        pe_steps = np.roll(pe_steps, [0, int(-np.round(n_ex / 2))])
    pe_order = pe_steps.reshape((n_ex, n_echo), order='F').T
    phase_areas = pe_order * delta_k

    # ======
    # SPLIT GRADIENTS AND RE-SPLICE INTO BLOCKS
    # See the block structure table in the module docstring.
    # ======
    def ext_trap(channel, times, amplitudes):
        return pp.make_extended_trapezoid(channel=channel, times=np.array(times), amplitudes=np.array(amplitudes))

    def crusher_times(g):
        """The four corner times of a trapezoid: start, end of ramp up, end of flat, end."""
        return [0, g.rise_time, g.rise_time + g.flat_time, g.rise_time + g.flat_time + g.fall_time]

    # Slice-select chain
    gs1 = ext_trap('z', [0, gs_ex.rise_time], [0, gs_ex.amplitude])
    gs2 = ext_trap('z', [0, gs_ex.flat_time], [gs_ex.amplitude, gs_ex.amplitude])
    gs3 = ext_trap('z', crusher_times(gs_spex),
                   [gs_ex.amplitude, gs_spex.amplitude, gs_spex.amplitude, gs_ref.amplitude])
    gs4 = ext_trap('z', [0, gs_ref.flat_time], [gs_ref.amplitude, gs_ref.amplitude])
    gs5 = ext_trap('z', crusher_times(gs_spr),
                   [gs_ref.amplitude, gs_spr.amplitude, gs_spr.amplitude, 0])
    gs7 = ext_trap('z', crusher_times(gs_spr),
                   [0, gs_spr.amplitude, gs_spr.amplitude, gs_ref.amplitude])

    # Readout chain
    gr3 = gr_preph
    gr5 = ext_trap('x', crusher_times(gr_spr),
                   [0, gr_spr.amplitude, gr_spr.amplitude, gr_acq.amplitude])
    gr6 = ext_trap('x', [0, readout_time], [gr_acq.amplitude, gr_acq.amplitude])
    gr7 = ext_trap('x', crusher_times(gr_spr),
                   [gr_acq.amplitude, gr_spr.amplitude, gr_spr.amplitude, 0])

    # ======
    # TIMING
    # ======
    t_ex_block = pp.calc_duration(gs1) + pp.calc_duration(gs2) + pp.calc_duration(gs3)
    t_ref_block = (
        pp.calc_duration(gs4) + pp.calc_duration(gs5) + pp.calc_duration(gs7) + readout_time
    )
    t_end_block = pp.calc_duration(gs4) + pp.calc_duration(gs5)

    TE_train = t_ex_block + n_echo * t_ref_block + t_end_block
    TR_fill = TR - TE_train
    TR_fill = system.grad_raster_time * round(TR_fill / system.grad_raster_time)
    if TR_fill < 0:
        TR_fill = 1e-3
        warnings.warn(f'TR too short, adapted to {1e3 * (TE_train + TR_fill):.1f} ms')
    else:
        print(f'TR fill: {1e3 * TR_fill:.1f} ms')
    delay_TR = pp.make_delay(TR_fill)

    # ======
    # CONSTRUCT SEQUENCE
    # ======
    # Shot 0 is a dummy: it plays the full echo train with no ADC and no phase
    # encoding, driving the magnetisation towards its pseudo steady state before
    # the first measured shot.
    for k_ex in range(n_ex + 1):
        seq.add_block(gs1)
        seq.add_block(rf_ex, gs2)
        seq.add_block(gs3, gr3)

        for k_echo in range(n_echo):
            phase_area = phase_areas[k_echo, k_ex - 1] if k_ex > 0 else 0.0

            gp_pre = pp.make_trapezoid(
                channel='y', system=system, area=phase_area, duration=t_sp, rise_time=dG
            )
            gp_rew = pp.make_trapezoid(
                channel='y', system=system, area=-phase_area, duration=t_sp, rise_time=dG
            )

            seq.add_block(rf_ref, gs4)
            seq.add_block(gr5, gp_pre, gs5)
            if k_ex > 0:
                seq.add_block(gr6, adc)
            else:
                seq.add_block(gr6)
            seq.add_block(gr7, gp_rew, gs7)

        seq.add_block(gs4)
        seq.add_block(gs5)
        seq.add_block(delay_TR)

    print(f'TSE: {n_ex} measured shots (+1 dummy) x {n_echo} echoes = {n_ex * n_echo} lines')
    print(f'     echo spacing {TE * 1e3:.1f} ms, train {TE_train * 1e3:.1f} ms, TR {TR * 1e3:.0f} ms')
    print(f'     matrix {NX} x {NY}, FOV {FOV * 1e3:.0f} mm, slice {SLICE_THICKNESS * 1e3:.0f} mm')

    if plot:
        seq.plot()

    if write:
        write_seq(seq, Path(__file__).parent / seq_filename, 'case2_tse', NX, NY)

    return seq


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--plot', action='store_true', help='show the sequence diagram')
    p.add_argument('--no-write', action='store_true', help='do not write the .seq file')
    args = p.parse_args()
    main(plot=args.plot, write=not args.no_write)
