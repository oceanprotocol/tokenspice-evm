#conftest.py for engine/test
# -this has some duplicate code with assets.agents.test.conftest.py,
#  that's ok since they evolve separately over time

from enforce_typing import enforce_types
import pytest
from typing import Union

from engine import AgentWallet, AgentBase
from web3tools import web3util, web3wallet
from web3tools.web3util import fromBase18, toBase18
from web3engine import bfactory, bpool, datatoken, dtfactory, globaltokens


#alice:
# 1. starts with an init OCEAN
# 2. creates a DT, and mints an init amount
# 3. creates a DT-OCEAN pool, and adds init liquidity

_OCEAN_INIT = 1000.0
_OCEAN_STAKE = 200.0
_DT_INIT = 100.0
_DT_STAKE = 20.0

_POOL_WEIGHT_DT    = 3.0
_POOL_WEIGHT_OCEAN = 7.0

@pytest.fixture
def alice_info():
    #only use this when there are >1 args into a test function and
    # we need addresses to line up. Otherwise, use a more specific function.
    return _alice_info()

@pytest.fixture
def alice_private_key() -> str:
    return _alice_info().private_key

@pytest.fixture
def alice_agent():
    return _alice_info().agent

@pytest.fixture
def alice_agent_wallet() -> AgentWallet.AgentWalletEvm:
    return _alice_info().agent_wallet

@pytest.fixture
def alice_web3wallet() -> web3wallet.Web3Wallet:
    return _alice_info().wallet

@pytest.fixture
def alice_DT() -> datatoken.Datatoken:
    return _alice_info().DT

@pytest.fixture
def alice_pool():
    return _alice_info().pool

@enforce_types
def _alice_info():
    return _make_info(private_key_name='TEST_PRIVATE_KEY1')

@enforce_types
def _make_info(private_key_name:str):
    class _Info:
        def __init__(self):
            self.private_key: Union[str, None] = None
            self.agent_wallet: Union[AgentWallet.AgentWalletEvm, None] = None
            self.web3wallet: Union[web3wallet, None] = None
            self.DT: Union[datatoken, None] = None
            self.pool: Union[bool, None] = None
    info = _Info()

    network = web3util.get_network()
    info.private_key = web3util.confFileValue(network, private_key_name)
    info.agent_wallet = AgentWallet.AgentWalletEvm(
        OCEAN=_OCEAN_INIT,private_key=info.private_key)
    info.web3wallet = info.agent_wallet._web3wallet

    info.DT = _createDT(info.web3wallet)
    info.pool = _createPool(DT=info.DT, web3_w=info.web3wallet)

    class MockAgent(AgentBase.AgentBaseEvm):
        def takeStep(self, state):
            pass
    info.agent = MockAgent("agent1",USD=0.0,OCEAN=0.0)
    info.agent._wallet = info.agent_wallet
    info.agent._wallet.resetCachedInfo() #needed b/c we munged the wallet

    #postconditions
    w = info.agent._wallet
    OCEAN_bal_base = globaltokens.OCEANtoken().balanceOf_base
    OCEAN1 = w.OCEAN()
    OCEAN2 = fromBase18(w._cached_OCEAN_base)
    OCEAN3 = fromBase18(OCEAN_bal_base(w._address))
    assert OCEAN1 == OCEAN2 == OCEAN3
    
    return info

@enforce_types
def _createDT(web3_w:web3wallet.Web3Wallet)-> datatoken.Datatoken:
    DT_address = dtfactory.DTFactory().createToken(
        'foo', 'DT1', 'DT1', toBase18(_DT_INIT),from_wallet=web3_w)
    DT = datatoken.Datatoken(DT_address)
    DT.mint(web3_w.address, toBase18(_DT_INIT), from_wallet=web3_w)
    return DT

@enforce_types
def _createPool(DT:datatoken.Datatoken, web3_w:web3wallet.Web3Wallet):
    OCEAN = globaltokens.OCEANtoken()
    
    #Create OCEAN-DT pool
    p_address = bfactory.BFactory().newBPool(from_wallet=web3_w)
    pool = bpool.BPool(p_address)

    DT.approve(pool.address, toBase18(_DT_STAKE), from_wallet=web3_w)
    OCEAN.approve(pool.address, toBase18(_OCEAN_STAKE),from_wallet=web3_w)

    pool.bind(DT.address, toBase18(_DT_STAKE),
              toBase18(_POOL_WEIGHT_DT), from_wallet=web3_w)
    pool.bind(OCEAN.address, toBase18(_OCEAN_STAKE),
              toBase18(_POOL_WEIGHT_OCEAN), from_wallet=web3_w)

    pool.finalize(from_wallet=web3_w)
    
    return pool
