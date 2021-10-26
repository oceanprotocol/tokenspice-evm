from enforce_typing import enforce_types
from typing import List
import random
from assets.agents import DataconsumerAgent
from assets.agents.PoolAgent import PoolAgent
from engine.AgentBase import AgentBase
from web3engine import bfactory, bpool, datatoken, dtfactory, globaltokens
from web3tools.web3util import toBase18
from util.constants import S_PER_DAY, S_PER_HOUR

@enforce_types
class DataconsumerAgent(DataconsumerAgent.DataconsumerAgent):
    def __init__(self, name: str, USD: float, OCEAN: float):
        super().__init__(name, USD, OCEAN)

        self._s_since_speculate = 0
        self._s_between_speculates = 8 * S_PER_HOUR #magic number
    def _candPoolAgents(self, state) -> List[PoolAgent]:
        """Pools that this agent can afford to buy 1.0 datatokens from,
        at least based on a first approximation. 
        """
        OCEAN_address = globaltokens.OCEAN_address()
        OCEAN = self.OCEAN()
        OCEAN_base = toBase18(OCEAN)

        pool_agents = state.agents.filterToPool()
        # exclude rugged pool
        for pool_name in state.ss.rugged_pools:
            try:
                del pool_agents[pool_name]
            except:
                pass
        
        all_pool_agents = pool_agents.values()
        
        cand_pool_agents = []
        for pool_agent in all_pool_agents:
            pool = pool_agent.pool
            DT_address = pool_agent.datatoken_address

            pool_DT_balance_base = pool.getBalance_base(DT_address)
            pool_OCEAN_balance_base = pool.getBalance_base(OCEAN_address)
            pool_DT_weight_base = pool.getDenormalizedWeight_base(DT_address)
            pool_OCEAN_weight_base = pool.getDenormalizedWeight_base(
                OCEAN_address)
            pool_swapFee_base = pool.getSwapFee_base()

            DT_amount_out_base = toBase18(1.0)

            spotPriceBefore_base = pool.getSpotPrice_base(
                tokenIn_address=OCEAN_address,
                tokenOut_address=DT_address)
            OCEANamountIn_base = pool.calcInGivenOut_base(
                tokenBalanceIn_base=pool_OCEAN_balance_base,
                tokenWeightIn_base=pool_OCEAN_weight_base,
                tokenBalanceOut_base=pool.getBalance_base(DT_address),
                tokenWeightOut_base=pool_DT_weight_base,
                tokenAmountOut_base=DT_amount_out_base,
                swapFee_base=pool_swapFee_base)

            if OCEANamountIn_base < OCEAN_base:
                cand_pool_agents.append(pool_agent)

        return cand_pool_agents