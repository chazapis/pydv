# pydv

Collection of Python code to experiment with D-STAR.

Provides Python interfaces to manage DExtra connections (the protocol used by XRF reflectors), convert from network data to D-STAR streams (header and frames) and vice versa, as well as decode voice data using [mbelib](https://github.com/szechyjs/mbelib).

Installs the following executables:
* `dv-recorder`, which connects to a DExtra-compatible reflector and records traffic in .dvtool files.
* `dv-player`, which plays back a .dvtool file to a DExtra-compatible reflector.
* `dv-decoder`, which converts a .dvtool file to .wav.

To build, you must first build and install [mbelib](https://github.com/szechyjs/mbelib).

Based on [ircDDBGateway](https://github.com/g4klx/ircDDBGateway) and [xlxd](https://github.com/LX3JL/xlxd). Tested with [xlxd](https://github.com/LX3JL/xlxd).
