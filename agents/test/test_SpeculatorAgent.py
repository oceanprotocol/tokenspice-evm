from enforce_typing import enforce_types
import pytest

from agents.PoolAgent import PoolAgent
from agents.SpeculatorAgent import SpeculatorAgent
from engine.AgentDict import AgentDict
from util.constants import S_PER_HOUR


class MockSS:
    def __init__(self):
        # seconds per tick
        self.time_step: int = S_PER_HOUR


class MockState:
    def __init__(self):
        self.agents = AgentDict({})
        self.ss = MockSS()

    def addAgent(self, agent):
        self.agents[agent.name] = agent


@enforce_types
def test_constructor1():
    agent = SpeculatorAgent("agent1", 0.1, 0.2)
    assert agent.USD() == 0.1
    assert agent.OCEAN() == 0.2
    assert agent._s_between_speculates > 0


@enforce_types
def test_constructor2():
    agent = SpeculatorAgent("agent1", 0.1, 0.2, 3)
    assert agent._s_between_speculates == 3


@enforce_types
def test_doSpeculateAction(alice_info):
    alice_pool = alice_info.pool
    state = MockState()

    agent = SpeculatorAgent("agent1", USD=0.0, OCEAN=0.0)

    assert agent._s_since_speculate == 0
    assert agent._s_between_speculates > 0

    assert not agent._doSpeculateAction(state)

    agent._s_since_speculate += agent._s_between_speculates
    assert not state.agents.filterToPool().values()
    assert not agent._doSpeculateAction(state)  # still no, since no pools

    state.agents["pool1"] = PoolAgent("pool1", alice_pool)
    assert state.agents.filterToPool().values()

    assert agent._doSpeculateAction(state)


@enforce_types
def test_speculateAction_nopools(alice_info):
    alice_pool = alice_info.pool
    state = MockState()

    agent = SpeculatorAgent("agent1", USD=0.0, OCEAN=1000.0)

    assert not agent._poolsForSpeculate(state)
    assert not agent._doSpeculateAction(state)
    with pytest.raises(AssertionError):
        agent._speculateAction(state)  # error because no pools


@enforce_types
def test_speculateAction_with_rugged_pools(alice_info):
    alice_pool = alice_info.pool
    state = MockState()
    state.agents["pool1"] = PoolAgent("pool1", alice_pool)
    state.rugged_pools = ["pool1"]

    agent = SpeculatorAgent("agent1", USD=0.0, OCEAN=500.0)

    assert not agent._poolsForSpeculate(state)
    assert not agent._doSpeculateAction(state)
    with pytest.raises(AssertionError):
        agent._speculateAction(state)  # error because no good pools


@enforce_types
def test_speculateAction_with_good_pools(alice_info):
    alice_pool = alice_info.pool
    state = MockState()
    state.agents["pool1"] = PoolAgent("pool1", alice_pool)

    agent = SpeculatorAgent("agent1", USD=0.0, OCEAN=500.0)

    assert agent._poolsForSpeculate(state)

    assert not agent._doSpeculateAction(state)  # not enough time passsed
    agent._s_since_speculate += agent._s_between_speculates  # make time pass
    assert agent._doSpeculateAction(state)  # now, enough time passed

    dt = state.agents["pool1"].datatoken
    assert agent.OCEAN() == 500.0
    assert agent.DT(dt) == 0.0

    agent._speculateAction(state)
    assert agent.OCEAN() < 500.0
    assert agent.DT(dt) > 0.0


@enforce_types
def test_take_step(alice_info):
    alice_pool = alice_info.pool
    state = MockState()
    state.agents["pool1"] = PoolAgent("pool1", alice_pool)

    agent = SpeculatorAgent("agent1", USD=0.0, OCEAN=500.0)

    num_speculates = num_loops = 0
    while num_speculates < 5 and num_loops < 10000:
        agent.takeStep(state)
        if num_loops > 0 and agent._s_since_speculate == 0:
            num_speculates += 1
        num_loops += 1

    assert num_speculates > 0, "should have had at least one speculate"
