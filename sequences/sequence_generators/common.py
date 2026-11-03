"""Scanner limits and the writer used by the sequence generators.

The numbers are the published constants in ``sequences/README.md``.
"""

from pathlib import Path

import pypulseq as pp

B0 = 3.0  # [T]
GAMMA = 42.5764e6  # [Hz/T]
LARMOR = GAMMA * B0  # 127.7292e6 Hz
FOV = 256e-3  # [m]
NX = 64
NY = 64
SLICE_THICKNESS = 4e-3  # [m]
MAX_GRAD = 28  # [mT/m]
MAX_SLEW = 130  # [T/m/s]
RF_DEAD_TIME = 100e-6  # [s]
RF_RINGDOWN_TIME = 100e-6  # [s]
ADC_DEAD_TIME = 10e-6  # [s]

SEQUENCES = Path(__file__).resolve().parent.parent

system = pp.Opts(
    max_grad=MAX_GRAD,
    grad_unit='mT/m',
    max_slew=MAX_SLEW,
    slew_unit='T/m/s',
    rf_ringdown_time=RF_RINGDOWN_TIME,
    rf_dead_time=RF_DEAD_TIME,
    adc_dead_time=ADC_DEAD_TIME,
    B0=B0,
)


def write_seq(seq, path, name: str, nx: int | None = None, ny: int | None = None) -> None:
    """Check timing, attach the challenge definitions, and write the published ``.seq``."""
    if (nx is None) != (ny is None):
        raise ValueError('nx and ny are set together')
    path = SEQUENCES / Path(path).name
    ok, error_report = seq.check_timing()
    if ok:
        print('Timing check passed successfully')
    else:
        print('Timing check FAILED. Error listing follows:')
        for error in error_report:
            print('   ', error)

    seq.set_definition(key='FOV', value=[FOV, FOV, SLICE_THICKNESS])
    seq.set_definition(key='Name', value=name)
    seq.set_definition(key='B0', value=B0)
    if nx is not None:
        seq.set_definition(key='Nx', value=int(nx))
        seq.set_definition(key='Ny', value=int(ny))
    seq.write(str(path))
    print(f'wrote {path}')
