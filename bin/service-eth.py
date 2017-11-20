#! /usr/bin/env python2

import json, jsonrpclib, time
import config, database, notify
import config as configlib

coinname="eth"
config=configlib.config["coins"][coinname]
walletrpc=jsonrpclib.jsonrpc.Server("http://{0}:{1}".format(config["host"], config["port"]))

accountIsLocked=True


def processDepositAddressRequests():
    global accountIsLocked

    dbda=database.DepositAddresses(coinname)

    pendingTransactions=[]
    for userid in dbda.listPendingRequests(100):
        useridAsHex=hex(userid)[2:].rjust(64, '0')

        address=walletrpc.eth_call({"from": config["deposit-master"], "to": config["contract-address"], "data": "0x877806af"+useridAsHex}, "latest")
        if address!="0x"+64*"0":
            address="0x"+address[-40:]
            dbda.storeAddress(userid, address)
        else:
            if accountIsLocked:
                walletrpc.personal_unlockAccount(config["deposit-master"], config["password"])
                accountIsLocked=False

            txhash=walletrpc.eth_sendTransaction({"from": config["deposit-master"], "to": config["contract-address"], "data": "0x32331feb"+useridAsHex, "gas": "0x493e0"})
            pendingTransactions.append(txhash)

    for txhash in pendingTransactions:
        while 1:
            receipt=walletrpc.eth_getTransactionReceipt(txhash)
            if receipt is not None:
                break
            time.sleep(1)

        for logentry in receipt["logs"]:
            if len(logentry["topics"])==1 and logentry["topics"][0]=="0xd3c75d3774b298f1efe8351f0635db8123b649572a5b810e96f5b97e11f43031":
                userid=int(logentry["data"][-72:-64], 16)
                address="0x"+logentry["data"][-40:]
                dbda.storeAddress(userid, address)
                break

    for userid,address in dbda.listUnnotifiedRequests(100):
        print("Notify {0} deposit address {1} for user {2}".format(coinname.upper(), address, userid))
        if notify.notify(reason="address", coin=coinname, userid=userid, address=address):
            dbda.markAsNotified(userid)
            print("> Accepted!")
        else:
            print("> Rejected!")


processDepositAddressRequests()
