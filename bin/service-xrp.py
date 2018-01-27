#! /usr/bin/env python2

import sys, os, io, json, time, binascii, traceback
import database, notify
import config as configlib
import logger as loggerlib
import pycurl


coinname="xrp"
logger=loggerlib.Logger(os.path.join(os.path.dirname(sys.argv[0]), os.pardir, "var", "log", "deposits-{0}.log".format(coinname)))

try:
    config=configlib.config["coins"][coinname]
except:
    sys.exit('No configuration for coin "{0}"'.format(coinname))


def depositNotify(txid, vout, userid, amount, conf):
    global coinname

    logger.message("Notify deposit {0} {1} {2} for user {3} with {4} confirmation(s)".format(txid, amount, coinname.upper(), userid, conf))

    if notify.notify(reason="deposit", coin=coinname.upper(), txid=txid, vout=vout, userid=userid, amount=amount, conf=conf):
        logger.message("> Accepted!")
        return True
    else:
        logger.message("> Rejected!")
        return False

def send_request(method, **params):

    data=json.dumps({"method": method, "params": [params]})
    buf=io.BytesIO()

    c=pycurl.Curl()
    c.setopt(pycurl.URL, "http://{0}:{1}/".format(config["host"], config["port"]))
#        c.setopt(pycurl.HTTPHEADER, ["Content-Type: application/json", "Accept: application/json", "HMAC-Signature: {0}".format(binascii.b2a_hex(digest))])
    c.setopt(pycurl.POST, 1)
    c.setopt(pycurl.POSTFIELDS, data)
    c.setopt(pycurl.IPRESOLVE, 1)
    c.setopt(pycurl.WRITEFUNCTION, buf.write)
    c.setopt(pycurl.TIMEOUT, 30)
    c.setopt(pycurl.CONNECTTIMEOUT, 10)
    c.perform()
    c.close()

    return json.loads(buf.getvalue())

def transactions(ledger_index_min=0):
    try:
        j=send_request("account_tx", ledger_index_min=ledger_index_min, ledger_index_max=-1, account=config["deposit-address"], forward=True)
        return j["result"]["transactions"]
    except:
        traceback.print_exc()
        return []

dbd=database.Deposits(coinname)

lastBlock=dbd.getLastCheckedBlockHeight()
if lastBlock is None:
    lastBlock=0


topBlockHeight=send_request("ledger_closed")["result"]["ledger_index"]

old_txlist=dbd.listUnacceptedDeposits()
new_unacceptedList={}
if len(old_txlist)>0:
    logger.message("{0} previously unconfirmed transaction(s) found".format(len(old_txlist)))

for ((txhash, vout), (userid, amount, blockHeight)) in old_txlist.items():
    if not depositNotify(txhash, vout, userid, amount, topBlockHeight-blockHeight+1):
        new_unacceptedList[(txhash, vout)]=(userid, amount, blockHeight)

tx_list=transactions(lastBlock+1)
new_lastBlock=lastBlock
for tx in tx_list:
    t=tx["tx"]
    if t["TransactionType"]=="Payment" and t["Destination"]==config["deposit-address"] and tx["validated"] and "DestinationTag" in t:
        txhash=t["hash"]
        amount=t["Amount"]
        amount=amount[:-6]+"."+amount[-6:]
        blockHeight=t["inLedger"]
        conf=topBlockHeight-blockHeight+1
        userid=((t["DestinationTag"]^config["obfuscate"]["mask"])*config["obfuscate"]["inv-multiplier"]%config["obfuscate"]["modulo"])

        if blockHeight>new_lastBlock:
            new_lastBlock=blockHeight

        if not depositNotify(txhash, 0, userid, amount, conf):
            new_unacceptedList[(txhash, 0)]=(userid, amount, blockHeight)

if len(new_unacceptedList)>0:
    logger.message("Saving {0} transaction(s) as unconfirmed".format(len(new_unacceptedList)))

dbd.setLastCheckedBlockHeight(new_lastBlock, new_unacceptedList)
