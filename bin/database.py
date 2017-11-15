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
  address TEXT(255),
  PRIMARY KEY(coinname(16), userid)
)""")

def getUserDepositAddress(coinname, userid):
    cur=db.cursor()
    res=cur.execute("SELECT pending, address FROM depositAddresses WHERE coinname=%s AND userid=%s LIMIT 0, 1;", (coinname, userid))
    if res==0:
        db.cursor().execute("INSERT INTO depositAddresses (coinname, userid, pending) VALUES (%s, %s, %s);", (coinname, userid, 1))
        db.commit()
        return None
    else:
        pending,address=cur.fetchone()
        if pending:
            return None
        else:
            return address
