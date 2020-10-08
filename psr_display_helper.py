# this module will be imported in the into your flowgraph
try:
    import xmlrpclib as xmlrpc
except:
    import xmlrpc.client as xmlrpc

rpchandle = None
inited = False
def get_profile(nbins,pacer,port):
    global rpchandle
    global inited
    try:
        if (inited == False):
            rpchandle = xmlrpc.ServerProxy("http://localhost:%d" % port, allow_none=True)
        r = rpchandle.get_current_profile()
        inited = True
    except:
        return ([0.0]*nbins)
    return r
    
