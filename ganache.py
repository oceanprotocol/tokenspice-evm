#!/usr/bin/env python

import eth_utils
import os

from web3tools.web3util import confFileValue

# Port in ganache_url must match ganache-cli call
port_number = '8545'
ganache_url = confFileValue('general', 'GANACHE_URL')
assert port_number in ganache_url

# get ganache-cli going, populating accounts found in conf file

# grab private keys
alice_private_key = confFileValue('ganache', 'TEST_PRIVATE_KEY1')
bob_private_key = confFileValue('ganache', 'TEST_PRIVATE_KEY2')
factory_deployer_private_key = confFileValue(
    'ganache', 'FACTORY_DEPLOYER_PRIVATE_KEY')

# launch ganache-cli and give each private account 100 eth.
amount_eth = 100
amount_wei = eth_utils.to_wei(amount_eth, 'ether')
os.system(
    f'ganache-cli --port {port_number} --gasLimit 10000000000 --gasPrice 1 ---hardfork istanbul --account="{alice_private_key},{amount_wei}" --account="{bob_private_key},{amount_wei}" --account="{factory_deployer_private_key},{amount_wei}" &')
