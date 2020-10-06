# stupid_simple_pulsar
A very simple pulsar receiver that produces folded pulse profiles in a .json file
That's now a bit of a lie.  It has grown "features".

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

If you have gr-osmosdr

make EXTRA_TARGET=stupid_simple_pulsar.py
sudo make EXTRA_TARGET=stupid_simple_pulsar.py install

There are basically 2 versions of the .py files produced:

stupid_simple_pulsar.py/stupid_simple_pulsar_uhd.py  -- UHD only
stupid_simple_pulsar_osmo.py                         -- OSMOSDR

ON a GR3.8/3.9 system:

make GRCC_CMD="grc" 
sudo make install

It assumes that you have "grcc" installed which should have come with 
GnuRadio and GRC.

It installs into /usr/local/bin by default--you can set the PREFIX
  variable on the Make command line to change this.
  

USING

Options:
  -h, --help           show this help message and exit
  --antenna=ANTENNA    Set Antenna selector [default=RX2]
  --debug=DEBUG        Set Debug magnitude [default=0.0]
  --device=DEVICE      Set Device String [default=rtl=0]
  --dm=DM              Set Dispersion Measure [default=26.76]
  --fine=FINE          Set Set fine-scale trial folding [default=0]
  --freq=FREQ          Set Frequency [default=408.0M]
  --logtime=LOGTIME    Set Logging interval (seconds) [default=60]
  --obstime=OBSTIME    Set Runtime in seconds [default=300]
  --outfile=OUTFILE    Set Output Filename [default=output.json]
  --period=PERIOD      Set Pulsar period (seconds) [default=714.52m]
  --pname=PNAME        Set Pulsar Name [default=b0329+54]
  --refclock=REFCLOCK  Set Reference clock source [default=internal]
  --rfgain=RFGAIN      Set RF Gain [default=50.0]
  --sky=SKY            Set Sky Frequency [default=0.0]
  --srate=SRATE        Set Sample Rate [default=2.56M]
  --timesrc=TIMESRC    Set Reference time (1PPS) source [default=internal]
  --width=WIDTH        Set Pulsar W50 width (seconds) [default=6.6m]

The --device parameter:

The _osmo version of the application uses gr-osmosdr, so it uses gr-osmosdr type device strings:

For a USRP B210:

--device "uhd,type=b200,subdev=A:A,num_recv_frames=128"

For an RTLSDR

--device rtl=0

For an Airspy

--device airspy

For the UHD version of the application (_uhd) standard UHD device arguments apply.

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
--fine      Enables fine-scale pulsar period trials
--antenna   Sets the antenna (usually UHD devices only)
--refclock  Sets the reference clock to be used
--timesrc   Sets the time (1PPS) source to be used
--pname     Sets the catalog pulsar name (used for filename formation)
--fmask     List of mask frequencies--comma-separated floats

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

The --fmask option

This option provides a list of frequencies that are known to contain RFI--it will be used to compute
  a zap-mask on the output of the filterbank

  
Output files

The code produces two different output files:

The .json file

The output .json file contains integrated profile estimates, computed over
  several different offsets from the --period parameter given on the command line.
  By default a "coarse" list of offsets, in PPM is used.  If the --fine option is
  set to non-zero, then it is assumed that the input --period is very close to
  actual, and a shorter, finer-grained list is used.

The .int8 file

This file is a "naked" filterbank file with the filename indicating recording parameters:

psr-<pname>-<freq-in-mhz>-<bw-in-mhz>-<mjd>-<nfb>-<output-rate>.int8 

Where: 
<pname>             Catalog name given on the command line
<freq-in-mhz>       The *center* SKY frequency, in MHz
<bw-in-mhz>         Observing bandwidth, in MHz
<nfb>               The number of filterbank channels
<output-rate>       The sample rate in Hz




