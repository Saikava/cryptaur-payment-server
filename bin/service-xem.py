#! /usr/bin/env python2

import sys, os, json, time, httplib, binascii
import database, notify
import config as configlib
import logger as loggerlib

coinname="xem"
logger=loggerlib.Logger(os.path.join(os.path.dirname(sys.argv[0]), os.pardir, "var", "log", "deposits-{0}.log".format(coinname)))

try:
    config=configlib.config["coins"][coinname]
except:
    sys.exit('No configuration for coin "{0}"'.format(coinname))

class HttpException(Exception):
    def __init__(self, code, description):
        self.code=code
        self.description=description

    def __str__(self):
        return "NIS API HTTP error {0}: {1}".format(self.code, self.description)

def depositNotify(txid, vout, userid, amount, conf):
    global coinname

    logger.message("Notify deposit {0} {1} {2} for user {3} with {4} confirmations".format(txid, amount, coinname.upper(), userid, conf))

    if notify.notify(reason="deposit", coin=coinname.upper(), txid=txid, vout=vout, userid=userid, amount=amount, conf=conf):
        logger.message("> Accepted!")
        return True
    else:
        logger.message("> Rejected!")
        return False

def send_request(path, method = "GET", data = ""):
    h=httplib.HTTPConnection(config["host"], config["port"])
    headers={}
    if method=="POST":
        headers["Content-type"]="application/json"
    h.request(method, path, data, headers)
    r=h.getresponse()
    if r.status!=200:
        raise HttpException(r.status, r.reason)

    s=r.read()
    try:
        return json.loads(s)
    except:
        return Node

def blockCount():
    try:
        return send_request("/chain/height")["height"]
    except:
        return None

def balance():
    try:
        r=send_request("/account/get?address={0}".format(config["deposit-address"]["address"]))
        return r["account"]["balance"]/1000000.0
    except:
        return 0.0

def transactionList(tx_id = None):
    try:
        params={"value":config["deposit-address"]["privateKey"]}
        if tx_id is not None:
            params["id"]=str(tx_id)
        return send_request("/local/account/transfers/incoming", "POST", json.dumps(params))["data"]
    except:
        return []

dbd=database.Deposits(coinname)

last_tx_id=dbd.getLastCheckedBlockHeight()
tx_list=transactionList()
if len(tx_list)>0:
    while last_tx_id is None or tx_list[-1]["meta"]["id"]>last_tx_id:
        portion=transactionList(tx_list[-1]["meta"]["id"])
        if len(portion)==0:
            break
        tx_list+=portion

if last_tx_id is not None:
    while len(tx_list)>0 and tx_list[-1]["meta"]["id"]<=last_tx_id:
        del tx_list[-1]

topBlockHeight=blockCount()

old_txlist=dbd.listUnacceptedDeposits()
new_unacceptedList={}
if len(old_txlist)>0:
    logger.message("{0} previously unconfirmed transaction(s) found".format(len(old_txlist)))

for ((txhash, vout), (userid, amount, blockHeight)) in old_txlist.items():
    if not depositNotify(txhash, vout, userid, amount, topBlockHeight-blockHeight+1):
        new_unacceptedList[(txhash, vout)]=(userid, amount, blockHeight)

for tx in tx_list:
    try:
        txhash=tx["meta"]["hash"]["data"]
        blockHeight=tx["meta"]["height"]
        txtype=tx["transaction"]["type"]
        conf=topBlockHeight-blockHeight+1
    except:
        continue

    if txtype==257:
        txStruct=tx["transaction"]
    elif txtype==4100 and "otherTrans" in tx["transaction"] and "type" in tx["transaction"]["otherTrans"] and tx["transaction"]["otherTrans"]["type"]==257:
        txStruct=tx["transaction"]["otherTrans"]
    else:
        logger.message("Unknown transaction type txid:{0} type:{1}".format(txhash, txtype))
        txStruct=None

    if txStruct is not None:
        try:
            amountfp=txStruct["amount"]
            amount=amountfp/1000000.0
        except:
            logger.message("Unknown amount txid:{0}".format(txhash))
            continue

        try:
            userid=int(binascii.a2b_hex(txStruct["message"]["payload"]))
        except:
            logger.message("Unknown recipient txid:{0} amount:{1:.6f} height:{2}".format(txhash, amount, blockHeight))
            continue

        if not depositNotify(txhash, 0, userid, amount, conf):
            new_unacceptedList[(txhash, 0)]=(userid, amount, blockHeight)

if len(new_unacceptedList)>0:
    logger.message("Saving {0} transaction(s) as unconfirmed".format(len(new_unacceptedList)))

if len(tx_list)>0:
    dbd.setLastCheckedBlockHeight(tx_list[0]["meta"]["id"], new_unacceptedList)
else:
    dbd.setLastCheckedBlockHeight(last_tx_id, new_unacceptedList)

if "transfer" in config and balance()>=config["transfer"]["min-amount"]+config["transfer"]["fee"]:
    fee=config["transfer"]["fee"]
    amount=balance()-fee
    address=config["transfer"]["address"]

    logger.message("Forwarding {0:.6f} XEM to {1}".format(amount, address))
    try:
        ts=send_request("/chain/last-block")["timeStamp"]

        transfer={}
        transfer["timeStamp"]=ts
        transfer["deadline"]=ts+3600
        transfer["amount"]=int(amount*1000000)
        transfer["fee"]=int(fee*1000000)
        transfer["recipient"]=address
        transfer["type"]=257
        #transfer["message"]={}
        transfer["version"]=0x68000001
        transfer["signer"]=config["deposit-address"]["publicKey"]
        r=send_request("/transaction/prepare-announce", "POST", json.dumps({"transaction": transfer, "privateKey": config["deposit-address"]["privateKey"]}))
        logger.message("> {0} {1} {2}".format(r["message"], r["code"], r["transactionHash"]["data"]))
    except:
        logger.message("> Failed")
