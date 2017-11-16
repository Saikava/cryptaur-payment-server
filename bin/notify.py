#! /usr/bin/env python

import io, binascii, pycurl, json, hashlib, hmac, time
import config

url=config.config["notify-url"]
key=config.config["notify-key"]


def notify(**args):
    args["nonce"]=int(time.time()*1000)
    data=json.dumps(args, sort_keys=True)
    digest=hmac.new(binascii.a2b_hex(key), data.encode("latin1"), hashlib.sha256).digest()

    buf=io.BytesIO()

    c=pycurl.Curl()
    c.setopt(pycurl.URL, url)
    c.setopt(pycurl.HTTPHEADER, ["Content-Type: application/json", "Accept: application/json", "HMAC-Signature: {0}".format(binascii.b2a_hex(digest))])
    c.setopt(pycurl.POST, 1)
    c.setopt(pycurl.POSTFIELDS, data)
    c.setopt(pycurl.IPRESOLVE, 1)
    c.setopt(pycurl.WRITEFUNCTION, buf.write)
    c.setopt(pycurl.TIMEOUT, 30)
    c.setopt(pycurl.CONNECTTIMEOUT, 10)
    c.perform()
    c.close()

    try:
        return json.loads(buf.getvalue())["accept"]
    except:
        return False
