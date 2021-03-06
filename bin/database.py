#! /usr/bin/env python
# -*- coding: utf8 -*-

import os, pymysql, sys, config

dbconfig=config.config["database"]
db=pymysql.connect(host=dbconfig["host"], user=dbconfig["user"], passwd=dbconfig["password"], db=dbconfig["dbname"])

db.cursor().execute("""CREATE TABLE IF NOT EXISTS depositAddresses
(
  coinname TEXT(16) NOT NULL,
  userid INT NOT NULL,
  pending BOOLEAN NOT NULL,
  notified BOOLEAN NOT NULL,
  address TEXT(255),
  PRIMARY KEY(coinname(16), userid)
);

CREATE TABLE IF NOT EXISTS addressToUserID
(
  coinname TEXT(16) NOT NULL,
  address TEXT(127) NOT NULL,
  userid INT NOT NULL,
  PRIMARY KEY(coinname(16), address(127))
);

CREATE TABLE IF NOT EXISTS lastCheckedBlockHeight
(
  coinname TEXT(16) NOT NULL,
  blockHeight INT,
  PRIMARY KEY(coinname(16))
);

CREATE TABLE IF NOT EXISTS lastCheckedBlockHeight2
(
  coinname TEXT(16) NOT NULL,
  userid INT NOT NULL,
  blockHeight INT,
  PRIMARY KEY(coinname(16), userid)
);

CREATE TABLE IF NOT EXISTS unacceptedTransactions
(
  coinname TEXT(16) NOT NULL,
  txhash TEXT(127) NOT NULL,
  vout INT NOT NULL,
  amount TEXT(100) NOT NULL,
  blockHeight INT,
  userid INT NOT NULL,
  PRIMARY KEY(coinname(16), txhash(127), vout)
);

CREATE TABLE IF NOT EXISTS unacceptedTransactions2
(
  coinname TEXT(16) NOT NULL,
  txhash TEXT(127) NOT NULL,
  userid INT NOT NULL,
  amount TEXT(100) NOT NULL,
  blockHeight INT NOT NULL,
  PRIMARY KEY(coinname(16), txhash(127), userid)
);

CREATE TABLE IF NOT EXISTS forwardTransaction
(
  coinname TEXT(16) NOT NULL,
  userid INT NOT NULL,
  txhash TEXT(127),
  PRIMARY KEY(coinname(16), userid)
);
""")
db.commit()

class DepositAddresses:
    def __init__(__self__, coinname):
        __self__.coinname=coinname;

    def getAddress(__self__, userid):
        global db

        cur=db.cursor()
        res=cur.execute("SELECT pending, address FROM depositAddresses WHERE coinname=%s AND userid=%s LIMIT 0, 1;", (__self__.coinname, userid))
        if res==0:
            db.cursor().execute("INSERT INTO depositAddresses (coinname, userid, pending, notified) VALUES (%s, %s, 1, 0);", (__self__.coinname, userid))
            db.commit()
            return None
        else:
            pending,address=cur.fetchone()
            if pending:
                return None
            else:
                return address

    def getUseridByAddress(__self__, address):
        global db

        cur=db.cursor()
        n=cur.execute("SELECT userid FROM addressToUserID WHERE coinname=%s AND address=%s LIMIT 0, 1;", (__self__.coinname, address))
        return None if n==0 else cur.fetchone()[0]

    def listPendingRequests(__self__, maxRequests):
        global db

        cur=db.cursor()
        cur.execute("SELECT userid FROM depositAddresses WHERE coinname=%s AND pending=1 LIMIT 0, %s;", (__self__.coinname, maxRequests))
        return [userid for (userid,) in cur.fetchall()]

    def storeAddress(__self__, userid, address):
        global db

        db.cursor().execute("UPDATE depositAddresses SET pending=0, notified=0, address=%s WHERE coinname=%s AND userid=%s;", (address, __self__.coinname, userid))
        db.cursor().execute("INSERT INTO addressToUserID (coinname, address, userid) VALUES (%s, %s, %s);", (__self__.coinname, address, userid))
        db.commit()

    def listUnnotifiedRequests(__self__, maxRequests):
        global db

        cur=db.cursor()
        cur.execute("SELECT userid, address FROM depositAddresses WHERE coinname=%s AND pending=0 AND notified=0 LIMIT 0, %s;", (__self__.coinname, maxRequests))
        return list(cur.fetchall())

    def markAsNotified(__self__, userid):
        db.cursor().execute("UPDATE depositAddresses SET notified=1 WHERE coinname=%s AND userid=%s;", (__self__.coinname, userid))
        db.commit()

    def listAllDepositAddresses(__self__):
        cur=db.cursor()
        cur.execute("SELECT userid, address FROM depositAddresses WHERE coinname=%s AND pending=0 AND notified=1;", (__self__.coinname, ))
        return list(cur.fetchall())

class Deposits:
    def __init__(__self__, coinname):
        __self__.coinname=coinname

    def getLastCheckedBlockHeight(__self__, userid=None):
        global db

        cur=db.cursor()

        if userid is None:
            n=cur.execute("SELECT blockHeight FROM lastCheckedBlockHeight WHERE coinname=%s;", (__self__.coinname, ))
        else:
            n=cur.execute("SELECT blockHeight FROM lastCheckedBlockHeight2 WHERE coinname=%s AND userid=%s;", (__self__.coinname, userid))
        if n==0:
            return None
        else:
            return cur.fetchone()[0]

    def listUnacceptedDeposits(__self__, userid=None):
        global db

        cur=db.cursor()
        if userid is None:
            cur.execute("SELECT txhash, vout, userid, amount, blockHeight FROM unacceptedTransactions WHERE coinname=%s;", (__self__.coinname, ))
            return {(txhash, vout):(userid, amount, blockHeight) for txhash, vout, userid, amount, blockHeight in cur.fetchall()}
        else:
            cur.execute("SELECT txhash, amount, blockHeight FROM unacceptedTransactions2 WHERE coinname=%s AND userid=%s;", (__self__.coinname, userid))
            return {txhash:(amount, blockHeight) for txhash, amount, blockHeight in cur.fetchall()}

    def setLastCheckedBlockHeight(__self__, blockHeight, unacceptedTransactions):
        global db

        db.cursor().execute("INSERT INTO lastCheckedBlockHeight VALUES (%s, %s) ON DUPLICATE KEY UPDATE blockHeight=%s;", (__self__.coinname, blockHeight, blockHeight))
        db.cursor().execute("DELETE FROM unacceptedTransactions WHERE coinname=%s;", (__self__.coinname,))
        for (txid,vout),(userid,amount,blockHeight) in unacceptedTransactions.items():
            db.cursor().execute("INSERT INTO unacceptedTransactions VALUES (%s, %s, %s, %s, %s, %s);", (__self__.coinname, txid, vout, amount, blockHeight, userid))
        db.commit()

    def setLastCheckedBlockHeight2(__self__, userid, lastCheckedBlock, unacceptedTransactions=None, resetForwardTx=False):
        global db

        db.cursor().execute("INSERT INTO lastCheckedBlockHeight2 VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE blockHeight=%s;", (__self__.coinname, userid, lastCheckedBlock, lastCheckedBlock))
        if unacceptedTransactions is not None:
            db.cursor().execute("DELETE FROM unacceptedTransactions2 WHERE coinname=%s AND userid=%s;", (__self__.coinname, userid))
            for (txid,(amount,blockHeight)) in unacceptedTransactions.items():
                db.cursor().execute("INSERT INTO unacceptedTransactions2 VALUES (%s, %s, %s, %s, %s);", (__self__.coinname, txid, userid, amount, blockHeight))
        if resetForwardTx:
            db.cursor().execute("INSERT INTO forwardTransaction VALUES (%s, %s, NULL) ON DUPLICATE KEY UPDATE txhash=NULL;", (__self__.coinname, userid))
        db.commit()

    def getForwardTransaction(__self__, userid):
        global db

        cur=db.cursor()
        n=cur.execute("SELECT txhash FROM forwardTransaction WHERE coinname=%s AND userid=%s LIMIT 0, 1;", (__self__.coinname, userid))
        if n==0:
            return None
        else:
            return cur.fetchone()[0]

    def setForwardTransaction(__self__, userid, txhash):
        global db

        db.cursor().execute("INSERT INTO forwardTransaction VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE txhash=%s;", (__self__.coinname, userid, txhash, txhash))
        db.commit()
