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

    def __init__(self, fbsize=16,smear=10.0,period=0.714520,filename='/dev/null',fbrate=2500.0,tbins=250,interval=30,
        tppms="0.0",freq=408.0e6,bw=2.56e6,
        longitude=-75.984,subint=0):  # only default arguments here
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='Stupid Pulsar Folder',   # will show up in GRC
            in_sig=[np.float32],
            out_sig=None
        )
        # if an attribute with the same name as a parameter is found,
        # a callback is registered (properties work, too).
        
        self.set_output_multiple(fbsize)
        self.maxdelay = round(smear * float(fbrate))
        self.maxdelay = int(self.maxdelay)
        self.delayincr = int(round(float(self.maxdelay) / float(fbsize)))
        
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
        #
        # How much time is in each bin?
        # The profile should be "exactly" as long as a single
        #   pulse period
        #
        self.tbint = []
        self.periods = []
        for shift in self.shifts:
            self.tbint.append((self.p0*(1.0+shift))/float(tbins))
            self.periods.append((self.p0*(1.0+shift)))
        
        #
        # The profile length
        #   
        self.plen = int(tbins)
        
        #
        # Sample period
        #
        self.sper = 1.0/float(fbrate)
        
        #
        # Mission Elapsed Time
        # This is moved along at every time samples arrival--incremented
        #   by 'self.sper'
        #
        self.MET = 0.0
        
        #
        # Open the output file
        #
        self.fname = filename
        self.sequence = 0
        
        #
        # The logging interval
        #
        self.INTERVAL = int(fbrate*interval)
        self.logcount = self.INTERVAL
        self.jsonlets = []
        
        self.bw = bw
        self.freq = freq
        self.longitude = longitude
        
        self.randlist = []
        for i in range(0,100000):
            self.randlist.append(random.randint(0,1))
        self.nrand = len(self.randlist)
        self.randcnt = 0
        
        self.subint = subint
        self.subtimer = self.subint
        self.subseq = 0
        
        self.first_sample = None
    
    def get_profile(self):
        mid = int(self.nprofiles/2)
        if (0 in self.pcounts[mid]):
            return [0.0]*self.plen
        l = []
        for v in np.divide(self.profiles[mid],self.pcounts[mid]):
            l.append(float(v))
        return l

    def first_sample_time(self):
        return self.first_sample

    def work(self, input_items, output_items):
        """Do dedispersion/folding"""
        q = input_items[0]
        l = len(q)
        if (self.first_sample == None):
            self.first_sample = time.time()
        for i in range(int(l/self.flen)):
            bndx = i*self.flen
            #
            # Do delay/dedispersion logic
            #
            if (self.maxdelay > 0):
                outval = 0.0
                #
                # start at 1 because
                #  we already know maxdelay > 1
                #
                for j in range(1,self.flen):
                    if ((self.maxdelay - (self.delayincr*j)) <= 0):
                        outval += q[bndx+j]
                self.maxdelay -= 1
            else:
                outval = math.fsum(q[bndx:bndx+self.flen])
            
            
            #
            # Outval now contains a single de-dispersed power sample
            #
            
            #
            # Increment Mission Elapsed Time
            #  sper is the sample period coming into the folder
            #
            self.MET += self.sper
            
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
                
                z = (float(self.plen)*self.MET/self.periods[x]) + 0.5
                    
                #
                # Convert that to an int, then reduce modulo number
                #  of time/phase bins in a single estimate
                #  normally there'll be P0/W50 bins, possibly
                #  expanded by some small-integer ratio.
                #
                # J0332+5434, for example, gives an optimal number
                #   of time/phase bins of 108 but you might want to
                #   extend that to 216 to get higher-resolution on
                #   the pulse profile.
                #
                where = int(z) % int(self.plen)
                
                #
                # Update appropriate time/phase bin
                #
                self.profiles[x][where] += outval
                self.pcounts[x][where] += 1.0
            
            #
            # Decrement the log counter
            #
            self.logcount -= 1
            
            #
            # If time to log, the output is the reduced-by-counts
            #  value of the profile.
            #
            if (self.logcount <= 0):
                outputs = []
                for x in range(self.nprofiles):
                    outputs.append(np.divide(self.profiles[x],self.pcounts[x]))
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
                self.sequence += 1
                profiles = []
                for x in range(self.nprofiles):
                    pd = {}
                    pd["profile"] = list(outputs[x])
                    pd["p0"] = self.p0*(1.0+self.shifts[x])
                    pd["shift"] = self.shifts[x]
                    profiles.append(pd)
                d["profiles"] = profiles
                self.jsonlets.append(d)
                self.logcount = self.INTERVAL
                if (self.subint > 0):
                    self.subtimer -= 1
                    if (self.subtimer <= 0):
                        self.subtimer = self.subint
                        d["subseq"] = self.subseq
                        for x in range(self.nprofiles):
                            self.profiles[x] = np.zeros(len(self.profiles[x]))
                            self.pcounts[x] = np.zeros(len(self.profiles[x]))
                fp = open(self.fname, "w")
                fp.write(json.dumps(self.jsonlets, indent=4)+"\n")
                fp.close()
            
            
        return len(q)

