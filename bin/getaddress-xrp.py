#! /usr/bin/env python2

import sys, os, json, time
import config as configlib

def returnJson(**args):
    sys.stdout.write(json.dumps(args))

coin="xrp"
userid=int(sys.argv[1])

try:
    config=configlib.config["coins"][coin]
except:
    returnJson(error={"code": -1001, "message": "No configuration for coin", "data": coin})

res={}
res["coin"]=coin
res["userid"]=userid
res["pending"]=False
res["address"]=config["deposit-address"]
res["supplementary-data"]={"DestinationTag": str(userid*config["obfuscate"]["multiplier"]%config["obfuscate"]["modulo"]^config["obfuscate"]["mask"])}

print json.dumps({"result":res})
