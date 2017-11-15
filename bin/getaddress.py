#! /usr/bin/env python2

import sys, json
import config, database

coin=sys.argv[1]
userid=int(sys.argv[2])

address=database.getUserDepositAddress(coin, userid)

res={}
res["coin"]=coin
res["userid"]=userid
res["pending"]=(address is None)
res["address"]=address

print json.dumps({"result":res})
