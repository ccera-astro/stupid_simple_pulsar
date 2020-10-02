# stupid_simple_pulsar
A very simple pulsar receiver that produces folded pulse profiles in a .json file

DEPENDENCIES

All the usual dependencies for Gnu Radio and gr-osmosdr--since it is
 device agnostic, it uses gr-osmosdr as a generic wrapper for
 various device types.
 
This application is based on GR 3.7 for now but if further developed
 will be ported to GR 3.8/3.9.
 
 

BUILDING

Just use:

make
sudo make install

It assumes that you have "grcc" installed which should have come with 
GnuRadio and GRC.

It installs into /usr/local/bin -- if this isn't appropriate on your
  system, you'll have to edit the Makefile for now.
  
USING

Usage: stupid_simple_pulsar.py: [options]

Options:
  -h, --help         show this help message and exit
  --device=DEVICE    Set Device String [default=rtl=0]
  --dm=DM            Set Dispersion Measure [default=26.76]
  --freq=FREQ        Set Frequency [default=408.0M]
  --logtime=LOGTIME  Set Logging interval (seconds) [default=30]
  --obstime=OBSTIME  Set Runtime in seconds [default=300]
  --outfile=OUTFILE  Set Output Filename [default=output.json]
  --period=PERIOD    Set Pulsar period (seconds) [default=714.52m]
  --res=RES          Set Filterbank resolution multiplier [default=1]
  --rfgain=RFGAIN    Set RF Gain [default=50.0]
  --srate=SRATE      Set Sample Rate [default=2.56M]
  --width=WIDTH      Set Pulsar W50 width (seconds) [default=6.6m]
  --debug=DEBUG      Set Debug magnitude [default=0.0]

The --device parameter:

The application uses gr-osmosdr, so it uses gr-osmosdr type device strings:

For a USRP B210:

--device "uhd,type=b200,subdev=A:A,num_recv_frames=128"

For an RTLSDR

--device rtl=0

For an Airspy

--device airspy

Other parameters:

--dm        The dispersion measure
--freq      The center frequency, in Hz. Engineering notation is supported
--logtime   How often the .json file is updated, in seconds
--obstime   The run-time (observing time) of the run, in seconds
--outfile   The name of the output file
--period    The pulsar period, in seconds
--rfgain    The RF gain setting for the hardware
--srate     The sampl rate, in sps.  Engineering notation is supported
--width     The pulsar width, in seconds
--debug     Enable a special debug mode
--sky       Set sky frequency, if different from --freq

The --debug mode

The code has a built-in sub-graph that includes a "fake pulsar" that can be used
  to test the downstream folding algorithm.  It is set to 0.0 by default which means
  that the fake pulsar signal is multiplied by zero before combining with the radio
  signal.  To have the fake pulsar roughly 20dB below the average radio noise, use
  --debug 0.01.  To have it 30dB below the radio noise, use --debug 0.001, etc.
  
The --sky option

If this option is non-zero, then it is used as the "sky" frequency that corresponds to the
  given *tuner* frequency specified with "--freq".  This is used in situations where there's
  a downconversion stage, in which case, the "--freq" option only applies to the hardware settings,
  and the "sky" frequency must be explicitly set to allow correct de-dispersion calculations.
  
  


