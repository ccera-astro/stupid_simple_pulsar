# this module will be imported in the into your flowgraph
try:
    import xmlrpclib as xmlrpc
except:
    import xmlrpc.client as xmlrpc
import numpy
import random


def get_pname(port):
    try:
        rpchandle = xmlrpc.ServerProxy("http://localhost:%d" % port, allow_none=True)
        r = rpchandle.get_pname()
    except:
        r = "????"
    return r

rpchandle = None
inited = False
def get_profile(pacer,port,outsize):
    global rpchandle
    global inited
    outp = [0.0]*outsize
    try:
        if (inited == False):
            rpchandle = xmlrpc.ServerProxy("http://localhost:%d" % port, allow_none=True)
        r = rpchandle.get_current_profile()
        r = numpy.divide(r,max(r))
        r = list(r)
        
        #
        # Re-center
        #
        l = len(r)
        newr = numpy.zeros(l)
        indx = r.index(max(r))
        ondx = int(l/2)
        for i in range(l):
            newr[ondx] = r[indx]
            indx += 1
            indx = indx % l
            
            ondx += 1
            ondx = ondx % l
    except:
        return ([0.0]*outsize)
    
    x = numpy.arange(0.0,float(outsize),1.0)
    x2 = numpy.arange(0.0,float(outsize),float(outsize)/float(l))
    y = newr
    newoutp = numpy.interp(x,x2,y)
    return newoutp
    
