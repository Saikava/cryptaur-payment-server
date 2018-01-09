#! /usr/bin/env python2

import sys, os, json, time
import database, notify
import config as configlib

sys.path.insert(0, os.path.join(os.path.dirname(sys.argv[0]), "jsonrpclib"))
import jsonrpclib

filename=os.path.splitext(os.path.basename(sys.argv[0]))[0]
if not filename.startswith("service2-"):
    sys.exit("Failed to determine coin name")
coinname=filename.replace("service2-", "")


try:
    config=configlib.config["coins"][coinname]
except:
    sys.exit('No configuration for coin "{0}"'.format(coinname))

walletrpc=jsonrpclib.jsonrpc.Server("http://{0}:{1}".format(config["host"], config["port"]))

# Overloading hex function - geth doesn't like L suffix
def hex(n):
    return "0x{0:x}".format(n)

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
    global walletrpc

    dbda=database.DepositAddresses(coinname)
    dbd=database.Deposits(coinname)

    topBlock=int(walletrpc.eth_blockNumber(), 16)

    for userid in dbda.listPendingRequests(100):
        address=walletrpc.personal_newAccount(config["password"])
        dbda.storeAddress(userid, address)
        dbd.setLastCheckedBlockHeight2(userid, topBlock)

    for userid,address in dbda.listUnnotifiedRequests(100):
        print("Notify {0} deposit address {1} for user {2}".format(coinname.upper(), address, userid))
        if notify.notify(reason="address", coin=coinname, userid=userid, address=address):
            dbda.markAsNotified(userid)
            print("> Accepted!")
        else:
            print("> Rejected!")

def findDepositsInBlock(address, block, balanceDifference):
    global walletrpc

    num=int(walletrpc.eth_getBlockTransactionCountByNumber(hex(block)), 16)
    res=[]

    for index in range(num):
        tx=walletrpc.eth_getTransactionByBlockNumberAndIndex(hex(block), hex(index))
        if tx["to"]==address:
            value=int(tx["value"], 16)
            balanceDifference-=value

            value=str(value).rjust(19, '0')
            value=value[:-18]+"."+value[-18:]

            res.append((tx["hash"], block, value))

    if balanceDifference!=0:
        value=str(balanceDifference).rjust(19, '0')
        value=value[:-18]+"."+value[-18:]

        res.append((walletrpc.eth_getBlockByNumber(hex(block), False)["hash"], block, value))

    return res

def findDepositsInBlockRange(address, low, high, lowBalance = None, highBalance = None):
    global walletrpc

    if low>=high:
        return []

    if lowBalance is None:
        lowBalance=int(walletrpc.eth_getBalance(address, hex(low)), 16)
    if highBalance is None:
        highBalance=int(walletrpc.eth_getBalance(address, hex(high)), 16)

    if lowBalance==highBalance:
        return []

    if low+1==high:
        return findDepositsInBlock(address, high, highBalance-lowBalance)

    mid=(low+high)//2

    midBalance=int(walletrpc.eth_getBalance(address, hex(mid)), 16)

    return findDepositsInBlockRange(address, low, mid, lowBalance, midBalance)+findDepositsInBlockRange(address, mid, high, midBalance, highBalance)

def processIncomingDeposits():
    global walletrpc

    dbda=database.DepositAddresses(coinname)
    dbd=database.Deposits(coinname)

    for userid,address in dbda.listAllDepositAddresses():
        lastCheckedBlock=dbd.getLastCheckedBlockHeight(userid)
        if lastCheckedBlock is None:
            lastCheckedBlock=0

        requiredConfirmations=10
        topBlockHeight=int(walletrpc.eth_blockNumber(), 16)
        checkUpToBlock=topBlockHeight-requiredConfirmations

        if lastCheckedBlock>=checkUpToBlock:
            continue

        old_txlist=dbd.listUnacceptedDeposits(userid)
        new_unacceptedList={}

        forwardtx=dbd.getForwardTransaction(userid)
        forwardtxBlock=None
        if forwardtx is not None:
            receipt=walletrpc.eth_getTransactionReceipt(forwardtx)
            if receipt is not None:
                forwardtxBlock=int(receipt["blockNumber"], 16)
                gasUsed=int(receipt["gasUsed"], 16)
                forwardtxInfo=walletrpc.eth_getTransactionByHash(forwardtx)
                gasPrice=int(forwardtxInfo["gasPrice"], 16)
                value=int(forwardtxInfo["value"], 16)
                forwardtxDebit=value+gasPrice*gasUsed

        if forwardtxBlock is None or forwardtxBlock>checkUpToBlock:
            for (txhash,blockHeight,amount) in findDepositsInBlockRange(address, lastCheckedBlock, checkUpToBlock):
                if not depositNotify(txhash, 0, userid, amount, topBlockHeight-blockHeight+1):
                    new_unacceptedList[txhash]=(amount, blockHeight)
            newLastCheckedBlock=checkUpToBlock
            shouldResetForwardTxHash=False
        else:
            for (txhash,blockHeight,amount) in findDepositsInBlockRange(address, lastCheckedBlock, forwardtxBlock-1):
                if not depositNotify(txhash, 0, userid, amount, topBlockHeight-blockHeight+1):
                    new_unacceptedList[txhash]=(amount, blockHeight)
            balanceBefore=int(walletrpc.eth_getBalance(address, hex(forwardtxBlock-1)), 16)
            balanceAfter=int(walletrpc.eth_getBalance(address, hex(forwardtxBlock)), 16)

#            print balanceAfter, balanceBefore, forwardtxDebit
#            sys.exit(1)

            for (txhash,blockHeight,amount) in findDepositsInBlock(address, forwardtxBlock, balanceAfter-balanceBefore+forwardtxDebit):
                if not depositNotify(txhash, 0, userid, amount, topBlockHeight-blockHeight+1):
                    new_unacceptedList[txhash]=(amount, blockHeight)
            newLastCheckedBlock=forwardtxBlock
            shouldResetForwardTxHash=True

        for (txhash,(amount,blockHeight)) in old_txlist.items():
            if not depositNotify(txhash, 0, userid, amount, topBlockHeight-blockHeight+1):
                new_unacceptedList[txhash]=(amount, blockHeight)

        if new_unacceptedList==old_txlist:
            new_unacceptedList=None

        dbd.setLastCheckedBlockHeight2(userid=userid, lastCheckedBlock=newLastCheckedBlock, unacceptedTransactions=new_unacceptedList, resetForwardTx=shouldResetForwardTxHash)

        if forwardtx is None and "transfer" in config:
            balance=int(walletrpc.eth_getBalance(address, "latest"), 16)
            if balance>=1E18*config["transfer"]["min-amount"]:
                print "Forwarding money to {0}...".format(config["transfer"]["address"])
                gasPrice=int(walletrpc.eth_gasPrice(), 16)
                gas=config["transfer"]["gas-amount"]

                walletrpc.personal_unlockAccount(address, config["password"])

#                print {"from": address, "to": config["transfer"]["address"], "gasPrice": hex(gasPrice), "gas": hex(gas), "value": hex(balance-gas*gasPrice)}
                txhash=walletrpc.eth_sendTransaction({"from": address, "to": config["transfer"]["address"], "gasPrice": hex(gasPrice), "gas": hex(gas), "value": hex(balance-gas*gasPrice)})
                dbd.setForwardTransaction(userid, txhash)
                print "> OK ({0})".format(txhash)

processDepositAddressRequests()
processIncomingDeposits()
