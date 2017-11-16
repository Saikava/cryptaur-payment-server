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
)""")

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

    def listPendingRequests(__self__, maxRequests):
        global db

        cur=db.cursor()
        cur.execute("SELECT userid FROM depositAddresses WHERE coinname=%s AND pending=1 LIMIT 0, %s;", (__self__.coinname, maxRequests))
        return [userid for (userid,) in cur.fetchall()]

    def storeAddress(__self__, userid, address):
        global db

        db.cursor().execute("UPDATE depositAddresses SET pending=0, notified=0, address=%s WHERE coinname=%s AND userid=%s;", (address, __self__.coinname, userid))
        db.commit()

    def listUnnotifiedRequests(__self__, maxRequests):
        global db

        cur=db.cursor()
        cur.execute("SELECT userid, address FROM depositAddresses WHERE coinname=%s AND pending=0 AND notified=0 LIMIT 0, %s;", (__self__.coinname, maxRequests))
        return list(cur.fetchall())

    def markAsNotified(__self__, userid):
        db.cursor().execute("UPDATE depositAddresses SET notified=1 WHERE coinname=%s AND userid=%s;", (__self__.coinname, userid))
        db.commit()
