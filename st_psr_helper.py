# this module will be imported in the into your flowgraph
import numpy
import sys
import time
import struct

rfi_counter = 3
flatten_counter = 5
smoother = None
smoothed = False
smoothing_estimate = None
#
# Process static mask-list, as well as auto RFI masking, and
#  passband smoothing
#
most_recent_mask = None
def frqlst_to_mask(flist, fc, bw, nfb,rfi_poller):
    global rfi_counter
    global smoother
    global flatten_counter
    global smoothed
    global smoothing_estimate
    global most_recent_mask

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
    most_recent_mask = rv
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
    ret = numpy.divide([1.0]*len(av), av)

    for i in range(len(mask)):
        if mask[i] <= 0.0:
            ret[i] = 0.0

    if (agc_counter > 0):
        agc_counter -= 1
        frozen_agc = ret
        return ret
    else:
        return frozen_agc

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
def build_header_info(outfile,source_name,source_ra,source_dec,freq,bw,fbrate,fbsize):

    fp = open(outfile, "w")
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
    #
    t_start = (time.time() / 86400.0) + 40587.0

    #
    # The rest here is mostly due to Guillermo Gancio ganciogm@gmail.com
    #
    stx="HEADER_START"
    etx="HEADER_END"
    fp.write(struct.pack('i', len(stx))+stx)
    fp.flush()
    #--
    aux="rawdatafile"
    aux=struct.pack('i', len(aux))+aux
    fp.write(aux)
    fp.write(struct.pack('i', len(outfile))+outfile)
    #--
    aux="src_raj"
    aux=struct.pack('i', len(aux))+aux
    source_ra = convert_sigproct(source_ra)
    fp.write(aux)
    aux=struct.pack('d', source_ra)
    fp.write(aux)
    fp.flush()

    #--
    aux="src_dej"
    aux=struct.pack('i', len(aux))+aux
    fp.write(aux)
    source_dec= convert_sigproct(source_dec)
    aux=struct.pack('d', source_dec)
    fp.write(aux)
    #--
    aux="az_start"
    aux=struct.pack('i', len(aux))+aux
    fp.write(aux)
    aux=struct.pack('d', 0.0)
    fp.write(aux)
    #--
    aux="za_start"
    aux=struct.pack('i', len(aux))+aux
    fp.write(aux)
    aux=struct.pack('d', 0.0)
    fp.write(aux)
    #--
    aux="tstart"
    aux=struct.pack('i', len(aux))+aux
    fp.write(aux)
    aux=struct.pack('d', float(t_start))
    fp.write(aux)
    #--
    aux="foff"
    aux=struct.pack('i', len(aux))+aux
    fp.write(aux)
    aux=struct.pack('d', f_off)
    fp.write(aux)
    #--
    aux="fch1"
    aux=struct.pack('i', len(aux))+aux
    fp.write(aux)
    aux=struct.pack('d', high_freq)
    fp.write(aux)
    #--
    aux="nchans"
    aux=struct.pack('i', len(aux))+aux
    fp.write(aux)
    aux=struct.pack('i', sub_bands)
    fp.write(aux)
    #--
    aux="data_type"
    aux=struct.pack('i', len(aux))+aux
    fp.write(aux)
    aux=struct.pack('i', 1)
    fp.write(aux)
    #--
    aux="ibeam"
    aux=struct.pack('i', len(aux))+aux
    fp.write(aux)
    aux=struct.pack('i', 1)
    fp.write(aux)
    #--
    aux="nbits"
    aux=struct.pack('i', len(aux))+aux
    fp.write(aux)
    aux=struct.pack('i', 8)
    fp.write(aux)
    #--
    aux="tsamp"
    aux=struct.pack('i', len(aux))+aux
    fp.write(aux)
    aux=struct.pack('d', tsamp)
    fp.write(aux)
    #--
    aux="nbeams"
    aux=struct.pack('i', len(aux))+aux
    fp.write(aux)
    aux=struct.pack('i', 1)
    fp.write(aux)
    #--
    aux="nifs"
    aux=struct.pack('i', len(aux))+aux
    fp.write(aux)
    aux=struct.pack('i', 1)
    fp.write(aux)
    #--
    aux="source_name"
    fp.write(struct.pack('i', len(aux))+aux)
    fp.write(struct.pack('i', len(source_name))+source_name)
    #--
    aux="machine_id"
    aux=struct.pack('i', len(aux))+aux
    fp.write(aux)
    aux=struct.pack('i', 20)
    fp.write(aux)
    #--
    aux="telescope_id"
    aux=struct.pack('i', len(aux))+aux
    fp.write(aux)
    aux=struct.pack('i', 20)
    fp.write(aux)
    #--
    fp.write(struct.pack('i', len(etx)))
    fp.write(etx)
    fp.flush()
    fp.close
    return True
