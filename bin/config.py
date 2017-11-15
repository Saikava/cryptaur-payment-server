#! /usr/bin/env python
# -*- coding: utf8 -*-

import sys, os, json

configfile=os.path.join(os.path.dirname(sys.argv[0]), os.pardir, "etc", "cryptaur", "payment.conf")
config=json.load(open(configfile, "rt"))
