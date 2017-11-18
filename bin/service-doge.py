#! /usr/bin/env python2

import json, jsonrpclib
import config, database, notify

coinname="doge"
trustWalletAccounts=False

def depositNotify(txid, vout, userid, amount, conf):
    global coinname

    print("Notify deposit {0}-{1} {2} {3} for user {4} with {5} confirmations".format(txid, vout, amount, coinname.upper(), userid, conf))
    if notify.notify(coin=coinname.upper(), txid=txid, vout=vout, userid=userid, amount=amount, conf=conf):
        print("> Accepted!")
        return True
    else:
        print("> Rejected!")
        return False

def processDepositAddressRequests():
    global walletrpc

    dbda=database.DepositAddresses(coinname)
    for userid in dbda.listPendingRequests(100):
        address=walletrpc.getnewaddress(str(userid))
        dbda.storeAddress(userid, address)
        print("Generated {0} deposit address {1} for user {2}".format(coinname.upper(), address, userid))

    for userid,address in dbda.listUnnotifiedRequests(100):
        print("Notify {0} deposit address {1} for user {2}".format(coinname.upper(), address, userid))
        if notify.notify(coin=coinname, userid=userid, address=address):
            dbda.markAsNotified(userid)
            print("> Accepted!")

def processIncomingDeposits():
    global walletrpc

    dbd=database.Deposits(coinname)
    dbda=database.DepositAddresses(coinname)

    lastCheckedBlock=dbd.getLastCheckedBlockHeight()

    if lastCheckedBlock is None:
        res=walletrpc.listsinceblock("", 1)
    else:
        res=walletrpc.listsinceblock(walletrpc.getblockhash(lastCheckedBlock), 1)

    topBlockHash=res["lastblock"]
    topBlockHeight=walletrpc.getblock(topBlockHash, True)["height"]

    new_txlist={}
    for tx in res["transactions"]:
        # It's not an incoming transaction
        if tx["category"]!="receive":
            continue

        # Extract account id - either directly from the transaction or indirectly
        # (use our database to find userid by receiving address)
        if trustWalletAccounts:
            try:
                account=int(tx["account"])
            except:
                continue
        else:
            account=dbda.getUseridByAddress(tx["address"])
            if account is None:
                continue

        # block height of transaction
        conf=tx["confirmations"]
        if conf==0:
            new_txlist[(tx["txid"],tx["vout"])]=(account,str(tx["amount"]),None)
        else:
            new_txlist[(tx["txid"],tx["vout"])]=(account,str(tx["amount"]),topBlockHeight-conf+1)

    old_txlist=dbd.listUnacceptedDeposits()
    new_unacceptedList={}

    for (txid,vout),tx in new_txlist.items():
        userid,amount,blockHeight=tx

        conf=0
        if blockHeight is not None:
            conf=topBlockHeight-blockHeight+1

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
            conf=topBlockHeight-blockHeight+1

        # TODO: check transaction because it may have ceased to exist

        if not depositNotify(txid, vout, userid, amount, conf):
            new_unacceptedList[(txid,vout)]=tx

    dbd.setLastCheckedBlockHeight(topBlockHeight, new_unacceptedList)


rpcparams=config.config["coins"][coinname]
walletrpc=jsonrpclib.jsonrpc.Server("http://{0}:{1}@{2}:{3}".format(rpcparams["user"], rpcparams["password"], rpcparams["host"], rpcparams["port"]))

processDepositAddressRequests()
processIncomingDeposits()
