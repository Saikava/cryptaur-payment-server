#! /usr/bin/env python2

import sys, os, json, time
import config as configlib

sys.path.insert(0, os.path.join(os.path.dirname(sys.argv[0]), "jsonrpclib"))
import jsonrpclib

def returnJson(**args):
    sys.stdout.write(json.dumps(args))
    sys.exit(0)

filename=os.path.splitext(os.path.basename(sys.argv[0]))[0]
if not filename.startswith("getinfo-"):
    returnJson(error={"code": -1000, "message": "Failed to determine coin name"})
coinname=filename.replace("getinfo-", "")

try:
    config=configlib.config["coins"][coinname]
except:
    returnJson(error={"code": -1001, "message": "No configuration for coin", "data": coinname})

walletrpc=jsonrpclib.jsonrpc.Server("http://{0}:{1}".format(config["host"], config["port"]))

depositMasterAddress=config["deposit-master"]
depositMasterBalance=walletrpc.eth_getBalance(depositMasterAddress, "latest")
depositMasterBalance=str(int(depositMasterBalance, 16)).rjust(19, '0')
depositMasterBalance=depositMasterBalance[:-18]+"."+depositMasterBalance[-18:]

returnJson(result={"deposit-master": {"address": depositMasterAddress, "balance": depositMasterBalance}})
