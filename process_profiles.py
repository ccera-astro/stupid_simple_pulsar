#!/usr/bin/env python2
import os
import sys
import json
import math
import matplotlib.pyplot as plt
import numpy
import argparse
import random

parser = argparse.ArgumentParser()
parser.add_argument("--infile", default=None, required=True)
parser.add_argument("--name", default=None, required=True)
parser.add_argument("--outfile", default=None, required=True)
parser.add_argument("--random", action="store_true")
parser.add_argument("--outjson", default=None)
args = parser.parse_args()

fp = open (args.infile, "r")
name = args.name
inlines = fp.readlines()

#
# Turn all those lines into a single string
#
megastr = ""
for l in inlines:
    megastr += l

#
# Parse with JSON
#
profsets = json.loads(megastr)


#
# To track the profile with the highest SNR
#
maxratio = 0.00

#
# Find the "best" profile--the one with the highest apparent SNR
#

#
# For each profile set
#
for profset in profsets:

    set_time = profset["time"]
    set_seq = profset["sequence"]
    #set_lmst = profset["lmst"]
    
    #
    # For each profile in the set
    #
    nprof = len(profset["profiles"])
    for profile in profset["profiles"]:
        
        demaxed =list(profile["profile"])
        idx = demaxed.index(max(demaxed))
        demaxed[idx] = numpy.mean(demaxed)
        #
        # Determine rough SNR
        #
        avg = numpy.mean(demaxed)
        
       
        stddev = numpy.std(demaxed)
        

        mx = max(profile["profile"])-avg
        mx = mx/stddev
        
        #
        # If our rough SNR is better than what we
        #    already have...
        #
        if (not args.random and mx > maxratio):
            maxratio = mx
            #
            # Record it as "best"
            #
            best = {}
            best["time"] = str(set_time)
            best["shift"] = profile["shift"]
            best["profile"] = profile["profile"]
            best["p0"] = profile["p0"]
            best["sequence"] = set_seq
        elif (args.random and random.randint(0,len(profsets)*nprof/2) == 0):
            #
            # Record it as "best"
            #
            maxratio = mx
            best = {}
            best["time"] = str(set_time)
            best["lmst"] = set_lmst
            best["shift"] = profile["shift"]
            best["profile"] = profile["profile"]
            best["p0"] = profile["p0"]
            best["sequence"] = set_seq
            break

#
# Create a plot of it...
#
x = []
l = len(best["profile"])
q = best["profile"]
mxi = q.index(max(q))
newq = numpy.zeros(l)

#
# reorder so that max signal is right in the middle
#
indx = mxi
ondx = int(l/2)

for i in range(l):
    newq[ondx] = q[indx]
    indx += 1
    indx = indx % l
    ondx += 1
    ondx = ondx % l
#
# Create x axis as "phase" of best profile
#
for v in range(l):
    x.append(float(v)/float(l))
    
#
# Plot normalized profile against "phase"
#
lbl="Fc:%dM/Bw:%-.2fM/Tsamp:%-.2fus" % (profset["freq"]/1.0e6, profset["bw"]/1.0e6, profset["sampletime"]*1.0e6)
plt.plot(x, numpy.divide(newq, max(best["profile"])), label=lbl)
plt.suptitle(name+": Best profile @ "+best["time"]+" seq: "+str(best["sequence"]))
plt.legend(loc='lower left', fontsize='small')

maxratdb = math.log(maxratio)/math.log(10.0)
maxratdb *= 10.0
best["profile"] = list(newq)
best["snr"] = maxratio-1.0
best["snrdB"] = maxratdb

plt.title("P0: " + str(best["p0"])+"s bins: %d SNR: %5.2fdB" % (l, maxratdb))
plt.ylabel('Normalized Amplitude')
plt.xlabel('Pulsar Phase')
plt.grid(True)
plt.savefig(args.outfile)

#
# Save some summary data from our best-profile search
#
if (args.outjson != None):
    fp = open(args.outjson, "w")
    fp.write(json.dumps(best, indent=4)+"\n")
    fp.close()
