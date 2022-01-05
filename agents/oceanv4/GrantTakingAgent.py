from enforce_typing import enforce_types

from engine import AgentBase


@enforce_types
class GrantTakingAgent(AgentBase.AgentBaseNoEvm):
    def __init__(self, name: str, USD: float, OCEAN: float):
        super().__init__(name, USD, OCEAN)
        self._spent_at_tick = 0.0  # USD and OCEAN (in USD) spent

    def takeStep(self, state):
        self._spent_at_tick = self.USD() + self.OCEAN() * state.OCEANprice()

        # spend it all, as soon as agent has it
        self._transferUSD(None, self.USD())
        self._transferOCEAN(None, self.OCEAN())

    def spentAtTick(self) -> float:
        return self._spent_at_tick
