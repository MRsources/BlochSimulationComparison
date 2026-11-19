"""MR-zero simulation and timing reference for all five cases.

Writes ``case0.h5`` … ``case4.h5`` next to this file (raw ADC, acquisition
order). Prints the wall-clock of the MR-zero run itself, after the phantom
and the sequence are loaded, and names the CPU or GPU that ran it. The same
lines are written to ``timings.txt`` as each case finishes. Copy your own
wall-clock into ``runtime_s`` and the time recorded here into
``mrzero_runtime_s``. Evaluation divides the two.

Install::

    pip install mrzerocore==1.2.0 numpy h5py

The GPU is used when one is present. Pass ``cpu`` or ``gpu`` to choose::

    python submissions/003_MR-zero/simulation_mr0.py
    python submissions/003_MR-zero/simulation_mr0.py cpu
    python submissions/003_MR-zero/simulation_mr0.py gpu
"""
import sys
import time
from pathlib import Path

import h5py
import MRzeroCore as mr0
import numpy as np
import torch

here = Path(__file__).resolve().parent
root = here.parents[1] #modify this so it points to git base directory to run
LARMOR = 127.7292e6  # Hz. Published with the sequences.

# Example solver setup, not a challenge rule.
MAX_STATES = 200
MIN_STATE = 1e-3

# Case 4 repeats the EPI file on the phantom that carries T2'.
CASES = (
    (0, 'case0_fid.seq', 'challenge-brain-5mm.json'),
    (1, 'case1_gre.seq', 'challenge-brain-5mm.json'),
    (2, 'case2_tse.seq', 'challenge-brain-5mm.json'),
    (3, 'case3_epi.seq', 'challenge-brain-5mm.json'),
    (4, 'case3_epi.seq', 'challenge-brain-5mm-t2star.json'),
)


def use_gpu(argv: list[str]) -> bool:
    choice = argv[1] if len(argv) > 1 else 'auto'
    if choice == 'cpu':
        return False
    if choice == 'gpu' and not torch.cuda.is_available():
        raise SystemExit('gpu was requested, but CUDA is not available')
    if choice not in {'auto', 'gpu'}:
        raise SystemExit('usage: simulation_mr0.py [cpu|gpu]')
    return torch.cuda.is_available()


def hardware(gpu: bool) -> str:
    if gpu:
        return torch.cuda.get_device_name(0)
    return 'cpu'


def load_phantom(name: str, gpu: bool):
    obj = mr0.TissueDict.load(str(root / 'phantoms' / 'brainweb' / name)).build()
    return obj.cuda() if gpu else obj


def load_sequence(name: str, gpu: bool):
    seq = mr0.Sequence.import_file(str(root / 'sequences' / name), larmor_hz=LARMOR)
    return seq.cuda() if gpu else seq


def write_signal(index: int, signal: np.ndarray) -> Path:
    path = here / f'case{index}.h5'
    with h5py.File(path, 'w') as handle:
        handle.create_dataset('signal_real', data=signal.real)
        handle.create_dataset('signal_imag', data=signal.imag)
    return path


def write_timings(where: str, lines: list[str]) -> Path:
    path = here / 'timings.txt'
    path.write_text('hardware: ' + where + '\n' + '\n'.join(lines) + '\n')
    return path


def main() -> None:
    gpu = False #use_gpu(sys.argv)
    where = hardware(gpu)
    phantoms: dict[str, object] = {}
    lines: list[str] = []
    print(f'hardware: {where}')
    for index, seq_name, phantom_name in CASES:
        if phantom_name not in phantoms:
            phantoms[phantom_name] = load_phantom(phantom_name, gpu)
        seq = load_sequence(seq_name, gpu)
        obj = phantoms[phantom_name]
        if gpu:
            torch.cuda.synchronize()
        started = time.perf_counter()
        graph = mr0.compute_graph(seq, obj, max_state_count=MAX_STATES, min_state_mag=MIN_STATE)
        signal = mr0.execute_graph(graph, seq, obj, print_progress=False)
        if gpu:
            torch.cuda.synchronize()
        seconds = time.perf_counter() - started
        adc = np.asarray(signal.detach().cpu()).reshape(-1)
        path = write_signal(index, adc)
        line = f'case {index}  {seconds:8.1f} s  {adc.size:5d} samples  {path.name}'
        print(line)
        lines.append(line)
        write_timings(where, lines)
    print(f'wrote {here / "timings.txt"}')


if __name__ == '__main__':
    main()
