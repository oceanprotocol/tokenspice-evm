"""
w3sl_noevm:
Netlist to simulate Web3 Sustainability Loop (w3sl), with no EVM
"""
from enforce_typing import enforce_types
from typing import List, Set

from assets.agents import MinterAgents
from assets.agents.BaseAgent import BaseAgent
from assets.agents.GrantGivingAgent import GrantGivingAgent
from assets.agents.GrantTakingAgent import GrantTakingAgent
from assets.agents.MarketplacesAgent import MarketplacesAgent
from assets.agents.OCEANBurnerAgent import OCEANBurnerAgent
from assets.agents.RouterAgent import RouterAgent

from engine import SimStateBase, KPIsBase, SimStrategyBase
from util import valuation
from util.constants import * #S_PER_HOUR, etc

@enforce_types
class SimStrategy(SimStrategyBase.SimStrategyBase):
    def __init__(self):
        #===initialize self.time_step, max_ticks====
        super().__init__()

        #===set base-class values we want for this netlist====
        self.setTimeStep(S_PER_HOUR)
        max_days = 10
        self.setMaxTicks(max_days * S_PER_DAY / self.time_step + 1)

        #===new attributes specific to this netlist===

        #initial # mkts
        self.init_n_marketplaces = 1

        #for computing annualGrowthRate() of # marketplaces, revenue/mktplace
        #-total marketplaces' growth = (1+annualGrowthRate)^2 - 1
        #-so, if we want upper bound of total marketplaces' growth of 50%,
        # we need max_growth_rate = 22.5%.
        #-and, if we want lower bound of total growth of -25%,
        # we need growth_rate_if_0_sales = -11.8%
        self.growth_rate_if_0_sales = -0.118
        self.max_growth_rate = 0.415
        self.tau = 0.6

    def annualMktsGrowthRate(self, ratio_RND_to_sales: float) -> float:
        """
        Growth rate for marketplaces. Starts low, and increases as
        the ($ into R&D)/($ from sales) goes up, but w/ diminishing returns.

        Modeled as an exponential decay function. 
        -Input x: ratio_RND_to_sales
        -Output y: growth rate
        -Func params:
          -self.tau: at x=tau, y has increased by 50% of its possible increase
          -          at x=2*tau, y ... 75% ...
          -self.growth_rate_if_0_sales 
          -self.max_growth_rate
        """
        mult = self.max_growth_rate - self.growth_rate_if_0_sales
        growth_rate: float = self.growth_rate_if_0_sales + mult * (1.0 - math.pow(0.5, ratio_RND_to_sales/self.tau))
        return growth_rate
    
@enforce_types
class SimState(SimStateBase.SimStateBase):
    
    def __init__(self):
        #initialize self.tick, ss, agents, kpis
        super().__init__()

        #now, fill in actual values for ss, agents, kpis
        self.ss = SimStrategy()
        ss = self.ss #for convenience as we go forward
                        
        #used to manage names
        self._next_free_marketplace_number = 0

        #used to add agents
        self._marketplace_tick_previous_add = 0
        
        #as ecosystem improves, these parameters may change / improve
        self._marketplace_percent_toll_to_ocean = 0.002 #magic number
        self._percent_burn: float = 0.05 #to burning, vs to DAO #magic number

        self._total_OCEAN_minted: float = 0.0
        self._total_OCEAN_burned: float = 0.0
        self._total_OCEAN_burned_USD: float = 0.0

        self._speculation_valuation = 150e6 #in USD #magic number
        self._percent_increase_speculation_valuation_per_s = 0.10 / S_PER_YEAR # ""

        #Instantiate and connnect agent instances. "Wire up the circuit"
        new_agents: Set[BaseAgent] = set()

        #Note: could replace MarketplacesAgent with DataecosystemAgent, for a
        # higher-fidelity simulation using EVM agents
        new_agents.add(MarketplacesAgent(
            name = "marketplaces1", USD=0.0, OCEAN=0.0,
            toll_agent_name = "opc_address",
            n_marketplaces = float(ss.init_n_marketplaces),
            revenue_per_marketplace_per_s = 20e3 / S_PER_MONTH, #magic number
            time_step = self.ss.time_step,
            ))

        new_agents.add(RouterAgent(
            name = "opc_address", USD=0.0, OCEAN=0.0,
            receiving_agents = {"ocean_dao" : self.percentToOceanDao,
                                "opc_burner" : self.percentToBurn}))

        new_agents.add(OCEANBurnerAgent(
            name = "opc_burner", USD=0.0, OCEAN=0.0))

        #func = MinterAgents.ExpFunc(H=4.0)
        func = MinterAgents.RampedExpFunc(H=4.0,
                                          T0=0.5, T1=1.0, T2=1.4, T3=3.0,
                                          M1=0.10, M2=0.25, M3=0.50)
        new_agents.add(MinterAgents.OCEANFuncMinterAgent(
            name = "ocean_51",
            receiving_agent_name = "ocean_dao",
            total_OCEAN_to_mint = UNMINTED_OCEAN_SUPPLY,
            s_between_mints = S_PER_DAY,
            func = func))
        
        new_agents.add(GrantGivingAgent(
            name = "opf_treasury_for_ocean_dao",
            USD = 0.0, OCEAN = OPF_TREASURY_OCEAN_FOR_OCEAN_DAO, 
            receiving_agent_name = "ocean_dao",
            s_between_grants = S_PER_MONTH, n_actions = 12 * 3))
        
        new_agents.add(GrantGivingAgent(
            name = "opf_treasury_for_opf_mgmt",
            USD = OPF_TREASURY_USD, OCEAN = OPF_TREASURY_OCEAN_FOR_OPF_MGMT,
            receiving_agent_name = "opf_mgmt",
            s_between_grants = S_PER_MONTH, n_actions = 12 * 3))
        
        new_agents.add(GrantGivingAgent(
            name = "bdb_treasury",
            USD = BDB_TREASURY_USD, OCEAN = BDB_TREASURY_OCEAN,
            receiving_agent_name = "bdb_mgmt",
            s_between_grants = S_PER_MONTH, n_actions = 17))
        
        new_agents.add(RouterAgent(
            name = "ocean_dao",
            receiving_agents = {"opc_workers" : funcOne},
            USD=0.0, OCEAN=0.0))
        
        new_agents.add(RouterAgent(
            name = "opf_mgmt",
            receiving_agents = {"opc_workers" : funcOne},
            USD=0.0, OCEAN=0.0))
                       
        new_agents.add(RouterAgent(
            name = "bdb_mgmt",
            receiving_agents = {"bdb_workers" : funcOne},
            USD=0.0, OCEAN=0.0))

        new_agents.add(GrantTakingAgent(
            name = "opc_workers", USD=0.0, OCEAN=0.0))

        new_agents.add(GrantTakingAgent(
            name = "bdb_workers", USD=0.0, OCEAN=0.0))

        for agent in new_agents:
            self.agents[agent.name] = agent

        #track certain metrics over time, so that we don't have to load
        self.kpis = KPIs(self.ss.time_step)
                    
    def takeStep(self) -> None:
        """This happens once per tick"""
        #update agents
        #update kpis (global state values)
        super().takeStep()
        
        #update global state values: other
        self._speculation_valuation *= (1.0 + self._percent_increase_speculation_valuation_per_s * self.ss.time_step)

    #==============================================================      
    def marketplacePercentTollToOcean(self) -> float:
        return self._marketplace_percent_toll_to_ocean
    
    def percentToBurn(self) -> float:
        return self._percent_burn

    def percentToOceanDao(self) -> float:
        return 1.0 - self._percent_burn
    
    #==============================================================
    def grantTakersSpentAtTick(self) -> float:
        return sum(
            agent.spentAtTick()
            for agent in self.agents.values()
            if isinstance(agent, GrantTakingAgent))

    #==============================================================
    def OCEANprice(self) -> float:
        """Estimated price of $OCEAN token, in USD"""
        price = valuation.OCEANprice(self.overallValuation(),
                                     self.OCEANsupply())
        assert price > 0.0
        return price
    
    #==============================================================
    def overallValuation(self) -> float: #in USD
        v = self.fundamentalsValuation() + \
            self.speculationValuation()
        assert v > 0.0
        return v
    
    def fundamentalsValuation(self) -> float: #in USD
        return self.kpis.valuationPS(30.0) #based on P/S=30
    
    def speculationValuation(self) -> float: #in USD
        return self._speculation_valuation
        
    #==============================================================
    def OCEANsupply(self) -> float:
        """Current OCEAN token supply"""
        return self.initialOCEAN() \
            + self.totalOCEANminted() \
            - self.totalOCEANburned()
        
    def initialOCEAN(self) -> float:
        return INIT_OCEAN_SUPPLY
        
    def totalOCEANminted(self) -> float:
        return self._total_OCEAN_minted
        
    def totalOCEANburned(self) -> float:
        return self._total_OCEAN_burned
        
    def totalOCEANburnedUSD(self) -> float:
        return self._total_OCEAN_burned_USD
    
    
def funcOne():
    return 1.0


@enforce_types
class KPIs(KPIsBase.KPIsBase):

    def __init__(self, time_step: int):
        super().__init__(time_step)
                
        #for these, append a new value with each tick
        self._granttakers_revenue_per_tick__per_tick: List[float] = []
        self._revenue_per_marketplace_per_s__per_tick: List[float] = []
        self._n_marketplaces__per_tick: List[int] = []
        self._marketplace_percent_toll_to_ocean__per_tick: List[float] = []
        self._total_OCEAN_minted__per_tick: List[float] = []
        self._total_OCEAN_burned__per_tick: List[float] = []
        self._total_OCEAN_minted_USD__per_tick: List[float] = []
        self._total_OCEAN_burned_USD__per_tick: List[float] = []

    def takeStep(self, state):        
        self._granttakers_revenue_per_tick__per_tick.append(
            state.grantTakersSpentAtTick())
        
        am = state.getAgent("marketplaces1")
        self._revenue_per_marketplace_per_s__per_tick.append(
            am.revenuePerMarketplacePerSecond())
        self._n_marketplaces__per_tick.append(am.numMarketplaces())
        self._marketplace_percent_toll_to_ocean__per_tick.append(
            state.marketplacePercentTollToOcean())

        O_minted = state.totalOCEANminted()
        O_burned = state.totalOCEANburned()
        self._total_OCEAN_minted__per_tick.append(O_minted)
        self._total_OCEAN_burned__per_tick.append(O_burned)

        O_price = state.OCEANprice()
        O_minted_USD = O_minted * O_price
        O_burned_USD = state.totalOCEANburnedUSD()
        self._total_OCEAN_minted_USD__per_tick.append(O_minted_USD)
        self._total_OCEAN_burned_USD__per_tick.append(O_burned_USD)

    def tick(self) -> int:
        """# ticks that have elapsed since the beginning of the run"""
        return len(self._revenue_per_marketplace_per_s__per_tick)
        
    #=======================================================================
    #growth rate
    def mktsRNDToSalesRatio(self) -> float:
        """Return the ratio ($ into ocean R&D) / ($ from ocean sales )
        We average over the last month. This is important
        because the grant takers often only get income monthly.
        """
        monthly_RND = self.grantTakersMonthlyRevenueNow()
        monthly_sales = self.oceanMonthlyRevenueNow()
        if monthly_RND == 0.0:
            ratio = 0.0
        else:
            ratio = monthly_RND / monthly_sales
        return ratio
        
    #=======================================================================
    #revenue numbers: grant takers
    def grantTakersMonthlyRevenueNow(self) -> float:
        ticks_1mo = self._ticksOneMonth()
        rev_per_tick = self._granttakers_revenue_per_tick__per_tick
        return float(sum(rev_per_tick[-ticks_1mo:]))
        
    #=======================================================================
    #revenue numbers: 1 marketplace
    def onemktMonthlyRevenueNow(self) -> float:
        t2 = self.elapsedTime()
        t1 = t2 - S_PER_MONTH
        return self._onemktRevenueOverInterval(t1, t2)
    
    def onemktAnnualRevenueNow(self) -> float:
        t2 = self.elapsedTime()
        t1 = t2 - S_PER_YEAR
        return self._onemktRevenueOverInterval(t1, t2)
    
    def onemktAnnualRevenueOneYearAgo(self) -> float:
        t2 = self.elapsedTime() - S_PER_YEAR
        t1 = t2 - S_PER_YEAR
        return self._onemktRevenueOverInterval(t1, t2)
            
    def _onemktRevenueOverInterval(self, t1: int, t2:int) -> float:
        return self._revenueOverInterval(t1, t2, self.onemktRevenuePerSecond)

    def onemktRevenuePerSecond(self, tick) -> float:
        """Returns onemkt's revenue per second at a given tick"""
        return self._revenue_per_marketplace_per_s__per_tick[tick]

    #=======================================================================
    #revenue numbers: n marketplaces
    def allmktsMonthlyRevenueNow(self) -> float:
        t2 = self.elapsedTime()
        t1 = t2 - S_PER_MONTH
        return self._allmktsRevenueOverInterval(t1, t2)
    
    def allmktsAnnualRevenueNow(self) -> float:
        t2 = self.elapsedTime()
        t1 = t2 - S_PER_YEAR
        return self._allmktsRevenueOverInterval(t1, t2)
    
    def allmktsAnnualRevenueOneYearAgo(self) -> float:
        t2 = self.elapsedTime() - S_PER_YEAR
        t1 = t2 - S_PER_YEAR
        return self._allmktsRevenueOverInterval(t1, t2)

    def allmktsRevenuePerSecond(self, tick) -> float:
        """Returns allmkt's revenue per second at a given tick"""
        return self._revenue_per_marketplace_per_s__per_tick[tick] \
            * self._n_marketplaces__per_tick[tick]
            
    def _allmktsRevenueOverInterval(self, t1: int, t2:int) -> float:
        return self._revenueOverInterval(t1, t2, self.allmktsRevenuePerSecond)
    
    #=======================================================================
    #revenue numbers: ocean community
    def oceanMonthlyRevenueNow(self) -> float:
        t2 = self.elapsedTime()
        t1 = t2 - S_PER_MONTH
        return self._oceanRevenueOverInterval(t1, t2)
    
    def oceanAnnualRevenueNow(self) -> float:
        t2 = self.elapsedTime()
        t1 = t2 - S_PER_YEAR
        return self._oceanRevenueOverInterval(t1, t2)
    
    def oceanMonthlyRevenueOneMonthAgo(self) -> float:
        t2 = self.elapsedTime() - S_PER_MONTH
        t1 = t2 - S_PER_MONTH
        return self._oceanRevenueOverInterval(t1, t2)
    
    def oceanAnnualRevenueOneYearAgo(self) -> float:
        t2 = self.elapsedTime() - S_PER_YEAR
        t1 = t2 - S_PER_YEAR
        return self._oceanRevenueOverInterval(t1, t2)
            
    def _oceanRevenueOverInterval(self, t1: int, t2:int) -> float:
        return self._revenueOverInterval(t1, t2, self.oceanRevenuePerSecond)
    
    def oceanRevenuePerSecond(self, tick) -> float:
        """Returns ocean's revenue per second at a given tick"""
        return self._revenue_per_marketplace_per_s__per_tick[tick] \
            * self._n_marketplaces__per_tick[tick] \
            * self._marketplace_percent_toll_to_ocean__per_tick[tick]
    
    #=======================================================================
    def _revenueOverInterval(self, t1: int, t2:int, revenuePerSecondFunc) \
        -> float:
        """
        Helper function for _{onemkt, allmkts, ocean}revenueOverInterval().

        In time from t1 to t2 (both in # seconds since start), 
        how much $ was earned, using the revenuePerSecondFunc.
        """
        assert t2 > t1
        tick1: int = max(0, math.floor(t1 / self._time_step))
        tick2: int = min(self.tick(), math.floor(t2 / self._time_step) + 1) 
        rev = 0.0
        for tick_i in range(tick1, tick2):
            rev_this_s = revenuePerSecondFunc(tick_i)
            
            start_s = max(t1, tick_i * self._time_step)
            end_s = min(t2, (tick_i + 1) * self._time_step - 1)
            n_s = end_s - start_s + 1
            rev_this_tick = rev_this_s * n_s
            
            rev += rev_this_tick
        return rev
        
    #=======================================================================
    #revenue growth numbers: ocean community
    def oceanMonthlyRevenueGrowth(self) -> float:
        rev1 = self.oceanMonthlyRevenueOneMonthAgo()
        rev2 = self.oceanMonthlyRevenueNow()
        if rev1 == 0.0:
            return INF
        g = rev2 / rev1 - 1.0
        return g
    
    def oceanAnnualRevenueGrowth(self) -> float:
        rev1 = self.oceanAnnualRevenueOneYearAgo()
        rev2 = self.oceanAnnualRevenueNow()
        if rev1 == 0.0:
            return INF
        g = rev2 / rev1 - 1.0
        return g
        
    @enforce_types
    def valuationPS(self, p_s_ratio: float) -> float:
        """Use Price/Sales ratio to compute valuation."""
        annual_revenue = self.oceanAnnualRevenueNow()
        v = valuation.firmValuationPS(annual_revenue, p_s_ratio)
        return v

    #=======================================================================
    #OCEAN minted & burned per month, as a count (#) and as USD ($)
    def OCEANmintedPrevMonth(self) -> float:
        return self._OCEANchangePrevMonth(self._total_OCEAN_minted__per_tick)
           
    def OCEANburnedPrevMonth(self) -> float:
        return self._OCEANchangePrevMonth(self._total_OCEAN_burned__per_tick)
    
    def OCEANmintedInUSDPrevMonth(self) -> float:
        return self._OCEANchangePrevMonth(self._total_OCEAN_minted_USD__per_tick)
    
    def OCEANburnedInUSDPrevMonth(self) -> float:
        return self._OCEANchangePrevMonth(self._total_OCEAN_burned_USD__per_tick)

    def _OCEANchangePrevMonth(self, O_per_tick) -> float:
        ticks_total = len(O_per_tick)

        if ticks_total == 0:
            return 0.0
        
        ticks_1mo = self._ticksOneMonth()
        if ticks_total <= ticks_1mo:
            return O_per_tick[-1]
        
        return O_per_tick[-1] - O_per_tick[-(ticks_1mo+1)]

    def _ticksOneMonth(self) -> int:
        """Number of ticks in one month"""
        ticks: int = math.ceil(S_PER_MONTH / float(self._time_step))
        return ticks