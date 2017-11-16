#! /usr/bin/env python2

import json, jsonrpclib
import config, database, notify

coinname="doge"

rpcparams=config.config["coins"][coinname]
walletrpc=jsonrpclib.jsonrpc.Server("http://{0}:{1}@{2}:{3}".format(rpcparams["user"], rpcparams["password"], rpcparams["host"], rpcparams["port"]))


for userid in database.listPendingAddressRequests(coinname, 5):
    address=walletrpc.getnewaddress(str(userid))
    database.storeDepositAddress(coinname, userid, address)
    print("Generated {0} deposit address {1} for user {2}".format(coinname.upper(), address, userid))

    notify.notify(coin=coinname, userid=userid, address=address)
