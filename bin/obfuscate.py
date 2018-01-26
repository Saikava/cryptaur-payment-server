#! /usr/bin/env python2

import hashlib
import binascii


def xor(data1, data2):
    assert len(data1)==len(data2)
    return b"".join((chr(ord(a)^ord(b)) for a,b in zip(data1, data2)))

def encrypt(data, key):
    assert len(data)==8

    l=data[0:4]
    r=data[4:8]

    for i in range(8):
        l,r=r,xor(l, hashlib.sha256(r+key).digest()[0:4])

    return l+r

def decrypt(data, key):
    r=encrypt(data[4:8]+data[0:4], key)
    return r[4:8]+r[0:4]

def encodeUserId(userid, key):
    data=b"{0:08x}".format(userid)
    return binascii.b2a_hex(encrypt(data, binascii.a2b_hex(key)))

def decodeUserId(encoded, key):
    if len(encoded)==32:
        encoded=binascii.a2b_hex(encoded)

    return int(decrypt(binascii.a2b_hex(encoded), binascii.a2b_hex(key)), 16)
