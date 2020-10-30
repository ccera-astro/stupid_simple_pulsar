"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""

import numpy as np
from gnuradio import gr
import time
import json
import atexit
import ephem
import math
import random

#
# Many of my RA programs haul this little function around...
# Should be converted to astropy at some point...
#
def cur_sidereal(longitude):
    longstr = "%02d" % int(longitude)
    longstr = longstr + ":"
    longitude = abs(longitude)
    frac = longitude - int(longitude)
    frac *= 60
    mins = int(frac)
    longstr += "%02d" % mins
    longstr += ":00"
    x = ephem.Observer()
    x.date = ephem.now()
    x.long = longstr
    jdate = ephem.julian_date(x)
    tokens=str(x.sidereal_time()).split(":")
    hours=int(tokens[0])
    minutes=int(tokens[1])
    seconds=int(float(tokens[2]))

    sidt = "%02d,%02d,%02d" % (hours, minutes, seconds)
    return (sidt)

class blk(gr.sync_block):  # other base classes are basic_block, decim_block, interp_block
    """A pulsar folder/de-dispersion block"""

    def __init__(self, fbsize=16,smear=0.0085,period=0.714520,fbrate=2500.0,tbins=250,
        tppms="0.0", thresh=1.0e6,mlen=4):  # only default arguments here
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='Stupid Pulsar Folder',   # will show up in GRC
            in_sig=[np.float32],
            out_sig=None
        )

        #
        # Various bits and pieces *know* what size the median filter is
        #  This could change at some point, but for now we set it here, and everything below
        #  that needs to "know* uses this
        #
        self.MEDIANSIZE = mlen

        #
        # Make sure we get data in appropriately-sized chunks
        #
        self.set_output_multiple(fbsize*self.MEDIANSIZE)

        #
        # Remember that we run at self.MEDIANSIZE times the notional filterbank
        #   sample rate.  So compute delays appropriately
        #
        self.ddelay = smear * float(fbrate*self.MEDIANSIZE)
        self.delayincr = self.ddelay/float(fbsize-1.0)
        self.delayincr += self.ddelay/float(fbsize)
        self.delayincr /= 2.0
        self.maxdelay = int(round(self.delayincr*(fbsize-1)))
        self.delaymap = np.zeros((self.maxdelay, fbsize))

        #
        # We create a matrix/map that allows us to just
        #  multiply the input filterbank channel either
        #  by 0 (this channel is still delayed) or
        #  by 1 (this channel is no longer delayed)
        #
        md = self.maxdelay-1
        for k in range(self.maxdelay):
          for j in range(fbsize):
            if ((md - (self.delayincr*j)) <= 0):
                self.delaymap[k][(fbsize-1)-j] = 1.0
          md -= 1
        self.delaycount = 0

        #
        # Needed in a few places
        #
        self.flen = fbsize

        #
        # The pulsar period
        #
        self.p0 = period

        #
        # The derived single-period pulse profile with various shifts
        #
        # We take it as a string, because that's easiest for command-line origin
        #
        if (isinstance(tppms,str)):
            trials = tppms.split(",")
            self.shifts = []
            for p in trials:
                self.shifts.append(float(p)*1.0e-6)
        elif (isinstance(tppms,list)):
            self.shifts = []
            for p in tppms:
                self.shifts.append(float(p)*1.0e-6)
        elif (isinstance(tppms,float) or isinstance(tppms,int)):
            self.shifts = [float(tppms)*1.0e-6]
        #
        # Create numpy 2D arrays for profile accumulator and counter
        #
        self.profiles = np.zeros((len(self.shifts),tbins))
        self.pcounts = np.zeros((len(self.shifts),tbins))
        self.nprofiles = len(self.profiles)

        #
        # The profile length as phase bins
        #
        self.plen = int(tbins)

        #
        #
        # The profile should be "exactly" as long as a single
        #   pulse period
        # We have compute the period offsets and perturb the
        #  period appropriately, producing an array of
        #  periods.
        #
        # Typically, the offsets are at most a few PPM
        #
        self.periods = []
        for shift in self.shifts:
            self.periods.append((self.p0*(1.0+shift)))

        #
        # Slightly accelerate math in the folding loop
        #
        self.pax = []
        for period in self.periods:
            self.pax.append(float(self.plen)/period)
        #
        # Input sample period (UNRELATED TO PULSAR PERIOD)
        #
        # This is correct because we only run the "top half" of the folder
        #  at the self.MEDIANSIZE rate--but after the median filter
        #  this rate is correct.
        #
        self.sper = 1.0/float(fbrate)

        #
        # Mission Elapsed Time
        #
        # Folding relies on this (INTEGER!) counter being incremented every time
        #  a new sample arrives from the filterbank.  Where "sample" is the aggregate
        #  of all the filterbank outputs summed.
        #
        # It is kept as an integer to reduce numerical error accumulation
        #
        self.MET = 0

        #
        # Initialize the profile logging outer main sequence number
        #
        self.sequence = 0
        
        self.housekeeping = False

        #
        # The main list/array that will be written as JSON, and appended to
        #  throughout the run
        #
        self.jsonlets = []
        
        #
        # Median filter buffer
        #
        self.mbuf = [0.0]*self.MEDIANSIZE
        self.mcnt = 0

        #
        # To record time-of-day of first sample
        # The work() function will initialize this on first sample
        #
        self.first_sample = None

        #
        # Housekeeping counters for both "outer" (top half) and
        #   "inner" (bottom half) of epoch folder.
        #
        self.outer_cnt = 0
        self.inner_cnt = 0

        #
        # Strong impulse removal threshold/2.5
        #
        self.thresh = thresh

        #
        # We don't do the threshold comparison until
        #  we've run for a while--to allow the averaging
        #  in the flow-graph to settle.
        #
        self.thrcount = int(fbrate*4*5)

    #
    # Get the current zero-PPM profile
    #
    # Supports the profile_display program, which gets
    #  at this via XMLRPC
    #
    def get_profile(self):
        mid = int(self.nprofiles/2)
        if (0 in self.pcounts[mid]):
            return [0.0]*self.plen
        l = []
        for v in np.divide(self.profiles[mid],self.pcounts[mid]):
            l.append(float(v))
        return l

    #
    # On slower disks, as the jsonlets array gets bigger, the work function
    #  can stall long enough to cause over-runs.  Soooooo
    #  we move the actual file-writing out of the work function and into
    #  this function that is polled.
    #
    # There's a simple semaphore than indicates that the jsonlets array is
    #  ready to be dumped.
    #
    def flush_logfile(self,skyf,samp_rate,longitude,subint,jsfilename,interval):
        
        self.freq = skyf
        self.bw = samp_rate
        self.longitude = longitude
        
        if (self.housekeeping == False):
            self.INTERVAL = interval
            self.logcount = self.INTERVAL
            self.subint = subint
            self.subtimer = subint
            self.subseq = 0
            self.housekeeping = True
            self.logready = False
            
        if (self.logready == True):
            #
            # Dump the accumulating JSON array
            #  (well, actually, an array of dictionaries that
            #   will get JSON encoded.)
            #
            chunk = int(500e6)
            fp = open(jsfilename, "w")
            jstr = json.dumps(self.jsonlets, indent=4)
            
            #
            # If it's "svelt", dump the whole thing immediately
            #
            if (len(jstr) < chunk):
                fp.write(jstr)
                
            #
            # Dribble it out with a bit of a pause--on some systems,
            #   our JSON writing interferes with our main .FIL writing
            #   resulting in over-runs, even at modest sample rates. :(
            #
            else:
                chunks = int(len(jstr)/chunk)
                remainder = len(jstr) % chunk
                base = 0
                for k in range(chunks):
                    fp.write(jstr[base:base+chunk])
                    base += chunk
                    time.sleep(0.250)
                fp.write(jstr[base:])
                
            
            fp.close()
            self.logready = False
        return True

    #
    # So the header-writer can get the first-sample time.
    #
    def first_sample_time(self):
        return self.first_sample

    #
    # Logging into our friend the ever-growing JSON buffer
    #
    def do_logging(self):
        
        if self.housekeeping == False:
            return

        #
        # To make sure the file-dumper doesn't activate in the middle
        #
        self.logready = False
        
        #
        # First, produce a list of averaged profiles
        #  remember we keep both an accumulator and
        #  a counter, so that we can produce an average
        #  at log time.
        #
        outputs = []
        for x in range(self.nprofiles):
            outputs.append(np.divide(self.profiles[x],self.pcounts[x]))

        #
        # Create a housekeeping dictionary
        #
        d = {}
        t = time.gmtime()
        d["sampletime"] = self.sper
        d["samplerate"] = 1.0/self.sper
        d["freq"] = self.freq
        d["bw"] = self.bw
        d["time"] = "%04d%02d%02d-%02d:%02d:%02d" % (t.tm_year,
            t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
        d["lmst"] = cur_sidereal(self.longitude).replace(",",":")
        d["sequence"] = self.sequence
        d["subseq"] = self.subseq

        #
        # Construct the list of profiles we're going to put in the .json dict
        #  along with a bit of housekeeping information per profile
        #
        profiles = []
        for x in range(self.nprofiles):
            pd = {}
            pd["profile"] = list(outputs[x])
            pd["p0"] = self.periods[x]
            pd["shift"] = self.shifts[x]
            profiles.append(pd)
        d["profiles"] = profiles

        #
        # We keep a running record, and dump the entire record
        #   every LOGTIME.
        #
        # This allows us to have a syntax-complete JSON file
        #  every time we write the file.  It means that the I/O
        #  load increases as time moves on, but since we're only
        #  doing this once per minute (by default), and really not
        #  creating THAT much data, this seems to work OK
        #
        #
        self.jsonlets.append(d)

        #
        # Handle "subint" sub-integrations
        #
        if (self.subint != None and self.subint > 0):
            self.subtimer -= 1

            #
            # Time to start a new sub-integration
            #
            if (self.subtimer <= 0):
                self.subtimer = self.subint

                #
                # We reduce the current profile almost to nothing,
                #  so that the "new" sub-int has something to chain
                #  from, but only a little bit of influence from what
                #  has gone before
                #
                for x in range(self.nprofiles):
                    #
                    # So compute the average reduction
                    #
                    t = np.divide(self.profiles[x],self.pcounts[x])

                    #
                    # Multiply by 0.1
                    #
                    t = np.multiply(t,0.1)

                    #
                    # Start building up (mostly) "fresh"
                    #  profile
                    #
                    self.profiles[x] = np.array(t)
                    self.pcounts[x] = np.array([1.0]*self.plen)

                self.subseq += 1

        #
        # Raise a simple semaphore
        #
        self.logready = True

    def work(self, input_items, output_items):
        """Do dedispersion/folding"""

        #
        # Call it 'q' just so we don't have to use
        #  'input_items[0]' everywhere.
        #
        q = input_items[0]
        l = len(q)

        #
        # Record the arrival of a bouncing baby first sample
        #
        # This is for the benefit of the header writer, to
        #  record a sub-1-second accurate MJD estimate for
        #  the dataset.
        #
        # We make a half-hearted attempt to adjust for the number of
        #  samples in the buffer and work backwards.
        #
        if (self.first_sample == None):
            self.first_sample = time.time()-(len(q)*self.sper)

        #
        # We deal with data in "chunks"
        #
        # That are self.flen--the filterbank size
        #
        for i in range(int(l/self.flen)):
            #
            # To make the index expression not quite so
            #  agonizing.
            #
            bndx = i*self.flen

            #
            # Do delay/dedispersion logic
            #
            # We just use numpy to use entries in the delay matrix
            #  to determine which filterbank channels get to particpate
            #  in the sum.  While a channel is "delayed" they don't get
            #  to participate.
            #
            # When we've hit "self.maxdelay", there are no more entries
            #  in the matrix, and nothing is being delayed
            #
            if (self.delaycount < self.maxdelay):
                outvec = np.multiply(q[bndx:bndx+self.flen],self.delaymap[self.delaycount])
                outval = math.fsum(outvec)
                self.delaycount += 1
            #
            # When all the delay is dealt with, every channel gets
            #   to contribute to the sum
            #
            else:
                outval = math.fsum(q[bndx:bndx+self.flen])

            #
            # Only one thing uses this at the moment, but future stuff
            #
            self.outer_cnt += 1

            #
            #  Median filter
            #
            # self.MEDIANSIZE in length
            #
            self.mbuf[self.mcnt] = outval
            self.mcnt += 1

            #
            # Time to reset mcnt, and "fall" to the
            #   lower half of this loop
            #
            if (self.mcnt >= self.MEDIANSIZE):
                self.mcnt = 0
            else:
                continue

            #
            # Compute the median now that we have enough
            #  samples.
            #
            outval = np.median(self.mbuf)

            #
            # Do gross impulse removal -- reduce to average
            #
            # We don't do the comparison until after our threshold
            #  estimator has settled after start-up, which will be
            #  in terms of "outer" (fast) samples--kept in self.thrcount
            #
            #
            # self.thresh contains a longer-term average of the signal
            #  coming in to the folder, and is updated at 1Hz through
            #  the set_thresh() function coming out of the flow-graph
            #
            # If our sample exceeds this value by a factor of 2.5 or
            #  more (~4dB in power), replace it with a randomly-dithered
            #  version of the average
            #
            # We don't expect this to happen very often, so the expense
            #  of calling random.uniform() shouldn't affect performance
            #  very much.  If this IS happening a lot, then the passband is
            #  probably not that useful for pulsars...
            #
            #
            if (self.outer_cnt > self.thrcount and outval > (self.thresh*2.5)):
                outval = self.thresh*random.uniform(0.98,1.02)

            #
            # At this point, our sample rate is reduced by self.MEDIANSIZE
            #
            #
            # Outval now contains a single de-dispersed, median-filtered
            #   strong-impulse-removed power sample
            #

            #
            # Increment Mission Elapsed Time
            #
            self.MET += 1

            #
            # Turn into floating-point sample-period representation
            #
            # Do this here rather than inside the loop, since it would
            #  (maybe?) get re-computed needlessly inside the loop.
            #
            flmet = float(self.MET)*self.sper

            #
            # Determine where the current sample is to be placed in the
            #  time/phase bin buffer.
            #
            # Update all the time/phase bins (we have a number of profiles, each with
            #   a slightly-different estimate for P0).
            #
            for x in range(self.nprofiles):
                #
                # This re-expresses self.MET in terms of number of
                #   time/phase bins for ths particular estimate of
                #   P0.
                #
                # From sigProcPy3
                # abs(((int)(nbins*tj*(1+accel*(tj-tobs)/(2*c))/period + 0.5)))%nbins;
                #
                # We eliminate the central correction for binary pulsars
                #
                # The +0.5 arranges to round-up prior to integer truncation
                #

                #z = (float(self.plen)*(flmet/self.periods[x])) + 0.5

                #
                # We eliminate a divide here, by noticing that self.plen and
                #  self.periods[x] are constant, so can be combined, using
                #  the pax[] array.
                #
                z = (flmet * self.pax[x]) + 0.5

                #
                # Convert that to an int, then reduce modulo number
                #  of time/phase bins in a single estimate
                #  normally there'll be P0/W50 bins, possibly
                #  expanded by some small-integer ratio.
                #
                # J0332+5434, for example, gives an optimal number
                #   of time/phase bins of 108 but you might want to
                #   extend that to 216 or 432 to get higher-resolution
                #   of the pulse profile.
                #
                where = int(z) % int(self.plen)

                #
                # Update appropriate time/phase bin
                #
                self.profiles[x][where] += outval
                self.pcounts[x][where] += 1.0

            if (self.housekeeping == True):
                #
                # Decrement the log counter
                #
                self.logcount -= 1

                #
                # If time to log
                #
                if (self.logcount <= 0):
                    self.do_logging()
                    self.sequence += 1
                    self.logcount = self.INTERVAL


        return len(q)
