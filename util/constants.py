#Note: this file no longer contains magic numbers, just useful
# numbers for running TokenSPICE. Magic numbers have been
# moved into netlists.

from util.configutil import CONF_FILE_PATH

import configparser, os
config = configparser.ConfigParser()
config.read(os.path.expanduser(CONF_FILE_PATH))

import logging
log = logging.getLogger('constants')

import brownie
BROWNIE_PROJECT = brownie.project.load('./', name="MyProject")
brownie.network.connect('development') #FIXME: may need to be 'ganache', since brownie auto-reverts in 'development'

GOD_ACCOUNT = brownie.network.accounts[0]

SAFETY = config['general'].getboolean('safety')
assert SAFETY is not None

from enforce_typing import enforce_types
if not SAFETY:
    # do nothing, just return the original function
    def noop(f):
        return f
    enforce_types = noop

#big numbers
import math
INF = math.inf
HUGEINT = 2**255 #biggest int that can be passed into contracts
 
#number of seconds in an hour, etc.
S_PER_MIN   = 60
S_PER_HOUR  = S_PER_MIN * 60 
S_PER_DAY   = S_PER_HOUR * 24
S_PER_WEEK  = S_PER_DAY * 7
S_PER_MONTH = S_PER_DAY * 30
S_PER_YEAR  = S_PER_DAY * 365

#Number of half-lives that bitcoin stops after.
# https://en.bitcoin.it/wiki/Controlled_supply#Projected_Bitcoins_Long_Term
BITCOIN_NUM_HALF_LIVES = 34

#evm stuff
GASLIMIT_DEFAULT = 5000000
BURN_ADDRESS = '0x000000000000000000000000000000000000dEaD'
