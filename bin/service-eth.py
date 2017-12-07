#! /usr/bin/env python2

import sys, os, json, time
import database, notify
import config as configlib

sys.path.insert(0, os.path.join(os.path.dirname(sys.argv[0]), "jsonrpclib"))
import jsonrpclib

filename=os.path.splitext(os.path.basename(sys.argv[0]))[0]
if not filename.startswith("service-"):
    sys.exit("Failed to determine coin name")
coinname=filename.replace("service-", "")

try:
    config=configlib.config["coins"][coinname]
except:
    sys.exit('No configuration for coin "{0}"'.format(coinname))

walletrpc=jsonrpclib.jsonrpc.Server("http://{0}:{1}".format(config["host"], config["port"]))

accountIsLocked=True


def depositNotify(txid, vout, userid, amount, conf):
    global coinname

    print("Notify deposit {0} {1} {2} for user {3} with {4} confirmations".format(txid, amount, coinname.upper(), userid, conf))
    if notify.notify(reason="deposit", coin=coinname.upper(), txid=txid, vout=vout, userid=userid, amount=amount, conf=conf):
        print("> Accepted!")
        return True
    else:
        print("> Rejected!")
        return False

def processDepositAddressRequests():
    global walletrpc, accountIsLocked

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

def processIncomingDeposits():
    global walletrpc

    dbd=database.Deposits(coinname)

    lastCheckedBlock=dbd.getLastCheckedBlockHeight()
    fromBlock=0 if lastCheckedBlock is None else lastCheckedBlock+1
    toBlock=int(walletrpc.eth_blockNumber(), 16)

    new_txlist={}
    if fromBlock<=toBlock:
        res=walletrpc.eth_getLogs({"fromBlock": hex(fromBlock), "toBlock": hex(toBlock), "address": config["contract-address"], "topics": ["0x028be863b16e1ebb120a887a86a8c08b41d33e317f4307ef113b1ff7e7a03873"]})

        for logEntry in res:
            txid=logEntry["transactionHash"]
            userid=int(logEntry["data"][-72:-64], 16)
            amount=str(int(logEntry["data"][-64:], 16)).rjust(19, '0')
            amount=amount[:-18]+"."+amount[-18:]
            blockNumber=int(logEntry["blockNumber"], 16)

            new_txlist[(txid,0)]=(userid,amount,blockNumber)

    old_txlist=dbd.listUnacceptedDeposits()
    new_unacceptedList={}

    for (txid,vout),tx in new_txlist.items():
        userid,amount,blockHeight=tx

        conf=0
        if blockHeight is not None:
            conf=toBlock-blockHeight+1

        if (txid,vout) not in old_txlist:
            if not depositNotify(txid, vout, userid, amount, conf):
                new_unacceptedList[(txid,vout)]=tx
        else:
            if not depositNotify(txid, vout, userid, amount, conf):
                new_unacceptedList[(txid,vout)]=tx
            del old_txlist[(txid,vout)]

    for (txid,vout),tx in old_txlist.items():
        userid,amount,blockHeight=tx

        conf=0
        if blockHeight is not None:
            conf=toBlock-blockHeight+1

        # TODO: check transaction because it may have ceased to exist

        if not depositNotify(txid, vout, userid, amount, conf):
            new_unacceptedList[(txid,vout)]=tx

    dbd.setLastCheckedBlockHeight(toBlock, new_unacceptedList)

processDepositAddressRequests()
processIncomingDeposits()
