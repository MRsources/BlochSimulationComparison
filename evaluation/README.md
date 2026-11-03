# Evaluation

Each case has its own folder. File names keep the case stem.

An imaging case is one figure, `<stem>.png`. Each submission is a row. The columns are k-space, magnitude, and phase.

- K-space is the log10 magnitude of the acquired K-space.
- Magnitude is the absolute value of the reconstruction.
- Phase runs from −π to π.

The FID has no readout gradient. Its folder holds two plots of the ADC against time, `<stem>_real.png` and `<stem>_imag.png`.