# this module will be imported in the into your flowgraph
import numpy
import sys
import time
import struct
import json

smoothing_dict = {
    "smoother" : None,
    "estimate" : None
}

rfi_dict = {
    "mask_logs" : [],
    "recent_mask" : None,
    "recent_premask" : None,
    "persistence" : None
}

agc_dict = {
    "frozen_agc" : None,
    "counter" : 15
}

uber_dict = {
    "smoothing" : smoothing_dict,
    "rfi" : rfi_dict,
    "agc" : agc_dict,
}

#
# State transition handler for smoothing
#
def st_do_smoothing(state,args,d):

    spec = args["rfi_poller"]

    if (state == INIT):
        d["smoother"] = [1.0]*len(spec)
        d["estimate"] = numpy.array(spec)
        return ((1,d["smoother"]))
    elif (state == WAITING):
        d["estimate"] = numpy.add(d["estimate"],spec)
        d["estimate"] = numpy.divide(d["estimate"], 2.0)
        return ((1, d["smoother"]))
    elif (state == READY):
        #
        # Grab the average of the central bits of the spectrum
        #
        avg = sum(d["estimate"][2:-2])
        avg /= (len(d["estimate"])-4.0)
        idx = 0
        #
        # Create a smoothing vector
        #
        for v in spec:
            d["smoother"][idx] = avg/v
            idx += 1

        return ((1,d["smoother"]))
    else:
        return ((0,d["smoother"]))

#
# Handler for RFI logging
#
def st_do_rfilog(state,args,ud):

    smoother = ud["smoothing"]["smoother"]
    frozen_agc = ud["agc"]["frozen_agc"]
    recent_premask = ud["rfi"]["recent_premask"]

    prefix = args["prefix"]
    name = args["name"]
    mjd = args["mjd"]
    spec = args["rfi_poller"]


    d = {}
    ltp = time.gmtime()
    ltime = "%04d%02d%02d-%02d:%02d:%02d" % (ltp.tm_year,
        ltp.tm_mon, ltp.tm_mday, ltp.tm_hour,
        ltp.tm_min, ltp.tm_sec)
    d["rfimask"] = list(ud["rfi"]["recent_premask"])
    d["persistence"] = list(ud["rfi"]["persistence"])
    d["smoothing"] = list(ud["smoothing"]["smoother"])
    d["spectrum"] = list(numpy.multiply(numpy.log10(spec),10.0))
    d["time"] = ltime
    d["frozen_agc"] = list(ud["agc"]["frozen_agc"])
    d["composite_mask"] = list(numpy.multiply(ud["agc"]["frozen_agc"],
        ud["rfi"]["recent_premask"]) )
    ud["rfi"]["mask_logs"].append(d)
    fn = "%s/psr-%s-%8.2f-mask.json" % (prefix, name, mjd)
    fp = open(fn, "w")
    fp.write(json.dumps(ud["rfi"]["mask_logs"],indent=4)+"\n")

    return ((0,0))

#
# Handler for RFI evalution
#
def st_do_rfi(state,args,d):

    spec = args["rfi_poller"]
    

    #
    # Cant do any further calculations if we're gettings zeros
    #
    if (0.0 in spec):
        return ((0,[1.0]*len(spec)))

    if (state == INIT):
        d["persistence"] = [0]*len(spec)
        return ((1,[1.0]*len(spec)))

    #
    # Auto RFI detect
    #
    #
    # We hold off for a bit until we have a better "view" of
    #  the spectrum
    #
    avg = numpy.mean(spec)
    idx = 0
    retmask = [1.0]*len(spec)
    for v in spec:
        if (v > avg*3.5):
            retmask[idx] = 0.0
        idx += 1

    return ((0,retmask))

#
# States
#
INIT = 0
READY = 1
COUNTING = 2
WAITING = 3
PROCESSING = 4
state_strings = ["INIT", "READY", "COUNTING", "WAITING", "PROCESSING"]

#
# Indexes into list for struct-like
#
# (Yes we could do this by creating a data-only "class", but
#   so much work, so few bullets)
#
ST_TINIT = 0  # Timer value
ST_STATE = 1  # Current state *index*
ST_STATES = 2 # List of states
ST_FUNC = 3   # function pointer
ST_DICT = 4   # State handler data


#
# Bit of a state machine table
#
rfi_stable = {
# name : timer-init current-state statelist function state-data
    "rfi": [10,  0, [INIT,PROCESSING], st_do_rfi, rfi_dict],
    "smoothing": [2,  0, [INIT,WAITING,WAITING,READY,PROCESSING], st_do_smoothing, smoothing_dict],
    "logging" : [15,  0, [COUNTING], st_do_rfilog, uber_dict]
}
st_counter = 0.0


def get_st_valid(d,key):
    return d[key][0]

def get_st_value(d,key):
    return d[key][1]

#
# Process static mask-list, as well as auto RFI masking, and
#  passband smoothing
#

last_time = time.time()
def frqlst_to_mask(flist, fc, bw, nfb,rfi_poller,mjd,prefix,name,eval_rate):
    #
    # State table
    #
    global rfi_stable

    #
    # State counter
    #
    global st_counter

    #
    # Last time were here
    #
    global last_time

    #
    # Dictionary of dictionaries for state variables
    #
    global uber_dict

    #
    # Neither *args nor **kwargs is quite right for what I want do do here...
    #
    args = {
        "flist" : flist,
        "fc" : fc,
        "bw" : bw,
        "nfb" : nfb,
        "rfi_poller" : rfi_poller,
        "mjd" : mjd,
        "prefix" : prefix,
        "name" : name,
        "eval_rate" : eval_rate
    }

    if rfi_poller == None or 0.0 in rfi_poller:
        return [1.0]*len(rfi_poller)

    #
    # Special structuring for "smoothing"
    #
    # Might generalize this at some point
    #
    bunchawaits = [WAITING]*int(5*eval_rate)
    rfi_stable["smoothing"][ST_STATES] = [INIT]+bunchawaits+[READY,PROCESSING]

    #
    # These states use the (seconds) timer
    #
    timed_states = [INIT,COUNTING]

    #
    # We get called at some arbitrary rate, usually greater than 1Hz
    #
    # But timed states are in 1Hz
    #
    do_timed_states = False
    now = time.time()
    if ((now - last_time) >= 1.0):
        st_counter += 1
        st_intcnt = st_counter
        last_time = now
        do_timed_states = True

    #
    # Go down the state table
    #
    odict = {}
    for key in rfi_stable:

        #
        # Get our dictionary entry
        #
        st = rfi_stable[key]
        state = st[ST_STATES][st[ST_STATE]]

        #
        # Output dict, indexed by state-machine name
        # A list with a "Valid" indicator in position 0
        #
        odict[key] = [False, 0]
        rv = [0,0]
        #
        # Time to invoke this state transition
        #
        #
        # Call function if timer expired an a timed state
        #
        #
        if (do_timed_states == True and state in timed_states and st_intcnt != 0 and (st_intcnt % st[ST_TINIT]) == 0):
            rv = st[ST_FUNC](state,args,st[ST_DICT])
            odict[key] = [True, rv[1]]

        #
        # Not in timed_states?  Call it every damned time we get here
        #
        elif (state not in timed_states):
            rv = st[ST_FUNC](state,args,st[ST_DICT])
            odict[key] = [True, rv[1]]

        #
        # If the function says to advance to next state, do so
        #
        if (odict[key][0] == True and rv[0] != 0):
            st[ST_STATE] += 1
            st[ST_STATE] = st[ST_STATE] % len(st[ST_STATES])

    #
    # Compute static mask first
    #
    retmask = [1.0]*nfb

    #
    # If there is a static list
    #
    if len(flist) > 0:

        #
        # Compute frequency end points
        #
        flow = fc - bw/2.0
        fhigh = fc + bw/2.0
        freqs = flist.split(",")
        fper = bw/float(nfb)
        for f in freqs:
            ff = float(f)
            #
            # Is within our frequency window?
            #
            if (ff >= flow and ff <= fhigh):
                diff = ff - flow
                indx = int(diff/fper)
                retmask[indx] = 0.0
        retmask.reverse()

    #
    # Convolve with the dynamic mask computed by the state-machine call
    #  (if valid)
    #
    if (get_st_valid(odict,"rfi") == True):
        retmask = numpy.multiply(retmask,get_st_value(odict,"rfi"))
        uber_dict["rfi"]["recent_premask"] = retmask
        for i in range(len(retmask)):
            if (retmask[i] == 0.0):
                uber_dict["rfi"]["persistence"][i] = 5
    else:
        uber_dict["rfi"]["recent_premask"] = retmask
        uber_dict["rfi"]["persistence"] = [0]*len(retmask)

    #
    # Make an RFI detection "sticky" for a bit
    #
    for i in range(len(retmask)):
        if (uber_dict["rfi"]["persistence"][i] > 0):
            retmask[i] = 0.0
            uber_dict["rfi"]["persistence"][i] -= 1
    
    if (get_st_valid(odict,"smoothing") == True):
        smoother = get_st_value(odict, "smoothing")
    else:
        smoother = [1.0]*len(rfi_poller)

    #
    # Our output aggregate mask is the
    #  composition of the smoother and the
    #  RFI mask
    #
    rv = numpy.multiply(smoother,retmask)
    uber_dict["rfi"]["recent_mask"] = retmask

    return rv

#
# After a little while, we freeze the AGC value, to prevent
#  any kind of pulsing
#
def process_agc(av):
    global uber_dict

    mask = uber_dict["rfi"]["recent_mask"]

    #
    # Check for zeros
    #
    if (0.0 in av):
        return [1.0]*len(av)

    ret = numpy.array(av)
    ret = numpy.add(av,1.0e-8)
    ret = numpy.divide([0.90]*len(av), av)

    for i in range(len(mask)):
        if mask[i] != 1.0:
            ret[i] = 0.0

    if (uber_dict["agc"]["counter"] > 0):
        uber_dict["agc"]["counter"] -=1
        uber_dict["agc"]["frozen_agc"] = ret
        return ret
    else:
        return numpy.multiply(uber_dict["agc"]["frozen_agc"],mask)

#
# Find a filter-bank output rate this produces strictly-integer
#  decimation.
#
def find_rate(srate,fbsize,target):

    brate = float(srate)/float(fbsize)
    decim = float(brate)/float(target)

    #
    # If target FBRATE is already integral
    #
    if (decim == float(int(decim))):
        return target

    rate = 3125.0*4.0
    
    decim = int(srate/fbsize/rate)
    rate = float(srate)/float(fbsize)/float(decim)
    return rate


#
# Convert to the weirdness that is the hybrid floating-point
#  time format used by SIGPROC
#
def convert_sigproct(v):
    itime = int(v*3600.0)
    hours = itime/3600
    minutes = (itime-(hours*3600))/60
    seconds = itime - (hours*3600) - (minutes*60)
    timestr="%02d%02d%02d.0" % (hours, minutes, seconds)
    return(float(timestr))
#
# This will cause a header block to be prepended to the output file
#
# Thanks to Guillermo Gancio (ganciogm@gmail.com) for the inspiration
#   and much of the code
#
# This seems to be broken for Python3
#
#
# This will cause a header block to be prepended to the output file
#
# Thanks to Guillermo Gancio (ganciogm@gmail.com) for the inspiration
#   and much of the code
#
# This seems to be broken for Python3
#
import time
import struct
import sys

def write_element_name(fp,elem):
    fp.write(struct.pack('i',len(elem)))
    if (sys.version_info[0] >= 3):
        fp.write(bytes(elem, encoding='utf8'))
    else:
        fp.write(elem)

def write_element_data(fp,elem,t):
    if (t != None and t != "str"):
        fp.write(struct.pack(t, elem))
    else:
        fp.write(struct.pack('i', len(elem)))
        if (sys.version_info[0] >= 3):
            fp.write(bytes(elem, encoding='utf8'))
        else:
            fp.write(elem)

#
# Convert to the weirdness that is the hybrid floating-point
#  time format used by SIGPROC
#
def convert_sigproct(v):
    itime = int(v*3600.0)
    hours = itime/3600
    minutes = (itime-(hours*3600))/60
    seconds = itime - (hours*3600) - (minutes*60)
    timestr="%02d%02d%02d.0" % (hours, minutes, seconds)
    return(float(timestr))

hdr_done = False
def build_header_info(outfile,source_name,source_ra,source_dec,freq,bw,fbrate,fbsize,flout,first):
    global hdr_done

    if (first == None or first < 86400.0):
        return None


    if (hdr_done == False):

        fp = open(outfile, "wb")
        #
        # Time for one sample, in sec
        #
        tsamp=1.0/fbrate

        #
        # Frequency offset between channels, in MHz
        #
        f_off=bw/fbsize
        f_off /= 1.0e6
        f_off *= -1

        #
        # Highest frequency represented in FB, in MHz
        #
        high_freq = freq+(bw/2.0)
        high_freq  /= 1.0e6
        high_freq -= (f_off/2.0)

        #
        # Lowest
        #
        low_freq = freq-(bw/2.0)
        low_freq /= 1.0e6
        low_freq += (f_off/2.0)

        #
        # Number of subbands
        #
        sub_bands=fbsize


        #
        # MJD
        # Super approximate!
        #
        t_start = ((time.time()+1.0) / 86400.0) + 40587.0

        #
        # The rest here is mostly due to Guillermo Gancio ganciogm@gmail.com
        #
        stx="HEADER_START"
        etx="HEADER_END"
        write_element_name(fp,stx)

        #--
        #
        write_element_name(fp,"rawdatafile")
        write_element_data(fp, outfile, "str")

        #--
        #
        write_element_name(fp, "src_raj")
        source_ra = convert_sigproct(source_ra)
        write_element_data (fp, source_ra, 'd')

        #--
        #
        write_element_name(fp, "src_dej")
        source_dec= convert_sigproct(source_dec)
        write_element_data(fp, source_dec, 'd')
        #--
        #
        write_element_name(fp, "az_start")
        write_element_data(fp, 0.0, 'd')

        #--
        #
        write_element_name(fp, "za_start")
        write_element_data(fp, 0.0, 'd')

        #--
        #
        write_element_name(fp, "tstart")
        write_element_data(fp, float(t_start), 'd')

        #--
        #
        write_element_name(fp, "foff")
        write_element_data(fp, f_off, 'd')

        #--
        #
        write_element_name(fp, "fch1")
        write_element_data(fp, high_freq, 'd')

        #--
        #
        write_element_name(fp, "nchans")
        write_element_data(fp, sub_bands, 'i')

        #--
        #
        write_element_name(fp, "data_type")
        write_element_data(fp, 1, 'i')

        #--
        #
        write_element_name(fp, "ibeam")
        write_element_data(fp, 1, 'i')

        #--
        #
        write_element_name(fp, "nbits")
        nb = 8 if flout <= 0 else 32
        write_element_data(fp, nb, 'i')

        #--
        #
        write_element_name(fp, "tsamp")
        write_element_data(fp, tsamp, 'd')

        #--
        #
        write_element_name(fp, "nbeams")
        write_element_data(fp, 1, 'i')

        #--
        #
        write_element_name(fp, "nifs")
        write_element_data(fp, 1, 'i')

        #--
        #
        write_element_name(fp, "source_name")
        write_element_data(fp, source_name, "str")

        #--
        #
        write_element_name(fp, "machine_id")
        write_element_data(fp, 20, 'i')

        #--
        #
        write_element_name(fp, "telescope_id")
        write_element_data(fp, 20, 'i')

        #--
        write_element_name(fp, etx)

        fp.close()
        hdr_done = True
        return True
    else:
        return False


def get_wrenabled(pacer):
    global hdr_done

    return hdr_done
