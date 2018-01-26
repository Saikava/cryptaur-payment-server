#! /usr/bin/env python2

import sys, os, json, time
import config as configlib
import obfuscate

def returnJson(**args):
    sys.stdout.write(json.dumps(args))

coin="xem"
userid=int(sys.argv[1])

try:
    config=configlib.config["coins"][coin]
except:
    returnJson(error={"code": -1001, "message": "No configuration for coin", "data": coin})

res={}
res["coin"]=coin
res["userid"]=userid
res["pending"]=False
res["address"]=config["deposit-address"]["address"]
res["supplementary-data"]={"message": obfuscate.encodeUserId(userid, config["userid-obfuscate-key"])}

print json.dumps({"result":res})
