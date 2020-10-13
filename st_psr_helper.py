# this module will be imported in the into your flowgraph
import numpy
import sys
import time
import struct
import json

rfi_counter = 3
flatten_counter = 5
smoother = None
smoothed = False
smoothing_estimate = None
rfi_logging_counter = 12
mask_log_list = []
#
# Process static mask-list, as well as auto RFI masking, and
#  passband smoothing
#
most_recent_mask = None
def frqlst_to_mask(flist, fc, bw, nfb,rfi_poller,mjd,prefix,name):
    global rfi_counter
    global smoother
    global flatten_counter
    global smoothed
    global smoothing_estimate
    global most_recent_mask
    global rfi_logging_counter
    global mask_log_list
    global frozen_agc

    if smoother == None:
        smoother = [1.0]*len(rfi_poller)
        smoothing_estimate = numpy.array(rfi_poller)

    retmask = [1.0]*nfb
    flow = fc - bw/2.0
    fhigh = fc + bw/2.0
    freqs = flist.split(",")
    fper = bw/float(nfb)
    if len(flist) > 0:
        for f in freqs:
            ff = float(f)
            if (ff >= flow and ff <= fhigh):
                diff = ff - flow
                indx = int(diff/fper)
                retmask[indx] = 0.0
        retmask.reverse()

    #
    # Cant do any calculations if we're gettings zeros
    #
    if (0.0 in rfi_poller):
        most_recent_mask = retmask
        return retmask
    #
    # Auto RFI detect
    #
    if (rfi_counter > 0):
        rfi_counter -= 1
    else:
        avg = sum(rfi_poller)
        avg /= len(rfi_poller)
        idx = 0
        for v in rfi_poller:
            if (v > avg*3.5):
                retmask[idx] = 0.0
            idx += 1

    #
    # Passband flattening
    #
    if (flatten_counter > 0):
        flatten_counter -= 1
        smoothing_estimate = numpy.add(smoothing_estimate,rfi_poller)
        smoothing_estimate = numpy.divide(smoothing_estimate, 2.0)
    elif (smoothed == False):
        #
        # Grab the average of the central bits of the spectrum
        #
        avg = sum(rfi_poller[2:-2])
        avg /= (len(rfi_poller)-4.0)
        idx = 0
        #
        # Create a smoothing vector
        #
        for v in rfi_poller:
            smoother[idx] = avg/v
            idx += 1
        smoothed = True


    rv = numpy.multiply(smoother,retmask)
    most_recent_mask = retmask
    rfi_logging_counter -= 1
    if (rfi_logging_counter < 0):
        rfi_logging_counter = 12
        d = {}
        ltp = time.gmtime()
        ltime = "%04d%02d%02d-%02d:%02d:%02d" % (ltp.tm_year,
            ltp.tm_mon, ltp.tm_mday, ltp.tm_hour,
            ltp.tm_min, ltp.tm_sec)
        d["rfimask"] = list(retmask)
        d["smoothing"] = list(smoother)
        d["spectrum"] = list(numpy.multiply(numpy.log10(rfi_poller),10.0))
        d["time"] = ltime
        d["frozen_agc"] = list(frozen_agc)
        d["composite_mask"] = list(numpy.multiply(frozen_agc,list(retmask)))
        mask_log_list.append(d)
        fn = "%s/psr-%s-%8.2f-mask.json" % (prefix, name, mjd)
        fp = open(fn, "w")
        fp.write(json.dumps(mask_log_list,indent=4)+"\n")

    return rv

#
# After a little while, we freeze the AGC value, to prevent
#  any kind of pulsing
#
frozen_agc = None
agc_counter = 12
def process_agc(av):
    global frozen_agc
    global agc_counter
    global most_recent_mask

    mask = most_recent_mask
    #
    # Check for zeros
    #
    if (0.0 in av):
        return [1.0]*len(av)

    ret = numpy.array(av)
    ret = numpy.divide([0.90]*len(av), av)

    for i in range(len(mask)):
        if mask[i] <= 0.0:
            ret[i] = 0.0

    if (agc_counter > 0):
        agc_counter -= 1
        frozen_agc = ret
        return ret
    else:
        return numpy.multiply(frozen_agc,mask)


def find_rate(srate,fbsize,target):

    brate = float(srate)/float(fbsize)
    decim = float(brate)/float(target)

    #
    # If target FBRATE is already integral
    #
    if (decim == float(int(decim))):
        return target

    #
    # Try to find a an integral rate
    #
    for r in numpy.arange(target-100,target*2.5,5.0):
        decim = float(brate)/float(r)
        if (decim == float(int(decim))):
            return r


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

def build_header_info(outfile,source_name,source_ra,source_dec,freq,bw,fbrate,fbsize,first):
    global hdr_countdown
    global hdr_done

    if (first == None):
        return None

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
    t_start = (first / 86400.0) + 40587.0

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
    write_element_data(fp, 8, 'i')

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

    fp.close
    return True

import os
def do_exit(hfile, fbfile):
    try:
        fp = open(hfile, "ab")
        initial_size = os.stat(hfile).st_size
    except:
        return
    try:
        ifp = open(fbfile, "rb")
        fb_size = os.stat(fbfile).st_size
    except:
        return
    while True:
        inbuf = ifp.read(16384)
        if len(inbuf) <= 0:
            break
        fp.write(inbuf)
    fp.close()
    ifp.close()
    new_size = os.stat(hfile).st_size
    
    #
    # OK to remove unheadereed .int8 file if the concatenation succeeded
    #
    if (new_size == initial_size+fb_size):
		os.remove(fbfile)
    return
