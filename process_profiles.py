#!/usr/bin/env python2
import os
import sys
import json
import matplotlib.pyplot as plt
import numpy
import argparse
import random

parser = argparse.ArgumentParser()
parser.add_argument("--infile", default=None, required=True)
parser.add_argument("--name", default=None, required=True)
parser.add_argument("--outfile", default=None, required=True)
parser.add_argument("--random", action="store_true")
args = parser.parse_args()

fp = open (args.infile, "r")
name = args.name
inlines = fp.readlines()

#
# Do a bit of fix-up on the slightly-broken JSON from the pulsar
#  receiver.
#
ndx = len(inlines)-1

#
# Remove the trailing comma on the last line
#
inlines[ndx] = inlines[ndx].replace(",", "")

#
# Add a trailing "]" to make this a valid list
#
inlines.append("]\n")

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
    
    #
    # For each profile in the set
    #
    for profile in profset["profiles"]:
        
        #
        # Determine rough SNR
        #
        avg = sum(profile["profile"])
        avg -= max(profile["profile"])
        avg /= len(profile["profile"])
        
        mx = max(profile["profile"])
        
        #
        # If our rough SNR is better than what we
        #    already have...
        #
        if (not args.random and ((mx/avg) > maxratio)):
            maxratio = mx/avg
            
            #
            # Record it as "best"
            #
            best = {}
            best["time"] = str(set_time)
            best["shift"] = profile["shift"]
            best["profile"] = profile["profile"]
            best["p0"] = profile["p0"]
            best["sequence"] = set_seq
        if (args.random and (random.randint(1,1000000) % 40) == 0):
            #
            # Record it as "best"
            #
            best = {}
            best["time"] = str(set_time)
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
#
# Create x axis as "phase" of best profile
#
for v in range(l):
    x.append(float(v)/float(l))
    
#
# Plot normalized profile against "phase"
#
plt.plot(x, numpy.divide(best["profile"], max(best["profile"])))
plt.suptitle(name+": Best profile @ "+best["time"]+" seq: "+str(best["sequence"]))
plt.title("P0: " + str(best["p0"])+"s bins: %d SNR: %5.2f" % (l, maxratio))
plt.ylabel('Normalized Amplitude')
plt.xlabel('Pulsar Phase')
plt.grid(True)
plt.savefig(args.outfile)
