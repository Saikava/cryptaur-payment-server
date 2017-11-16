#! /usr/bin/env python2

import json, jsonrpclib
import config, database, notify

coinname="doge"
db=database.DepositAddresses(coinname)

rpcparams=config.config["coins"][coinname]
walletrpc=jsonrpclib.jsonrpc.Server("http://{0}:{1}@{2}:{3}".format(rpcparams["user"], rpcparams["password"], rpcparams["host"], rpcparams["port"]))


for userid in db.listPendingRequests(100):
    address=walletrpc.getnewaddress(str(userid))
    db.storeAddress(userid, address)
    print("Generated {0} deposit address {1} for user {2}".format(coinname.upper(), address, userid))

for userid,address in db.listUnnotifiedRequests(100):
    print("Notify {0} deposit address {1} for user {2}".format(coinname.upper(), address, userid))
    if notify.notify(coin=coinname, userid=userid, address=address):
        db.markAsNotified(userid)
        print("> Accepted!")
