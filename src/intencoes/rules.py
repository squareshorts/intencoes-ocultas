"""Static rules of Intenções Ocultas and configurable assumptions (docs/rules_assumptions.md)."""
from dataclasses import dataclass
from enum import Enum


class Character(str, Enum):
    REGENTE = "Regente"
    COMERCIANTE = "Comerciante"
    SOMBRA = "Sombra"
    GUARDIAO = "Guardiao"
    EMBAIXADOR = "Embaixador"


class ActionType(str, Enum):
    INCOME = "Renda"
    FOREIGN_AID = "AjudaExterna"
    COUP = "GolpeDireto"
    TAX = "Regente:3moedas"
    STEAL = "Comerciante:roubo"
    ASSASSINATE = "Sombra:ataque"
    EXCHANGE = "Embaixador:troca"


# Character that must be claimed to take each action (None = general action).
CLAIM = {
    ActionType.INCOME: None,
    ActionType.FOREIGN_AID: None,
    ActionType.COUP: None,
    ActionType.TAX: Character.REGENTE,
    ActionType.STEAL: Character.COMERCIANTE,
    ActionType.ASSASSINATE: Character.SOMBRA,
    ActionType.EXCHANGE: Character.EMBAIXADOR,
}

# Characters that can block each action.
BLOCKERS = {
    ActionType.FOREIGN_AID: (Character.REGENTE,),
    ActionType.STEAL: (Character.GUARDIAO, Character.EMBAIXADOR),
    ActionType.ASSASSINATE: (Character.GUARDIAO,),
}

TARGETED = {ActionType.COUP, ActionType.STEAL, ActionType.ASSASSINATE}
INTERVENABLE = {ActionType.STEAL, ActionType.ASSASSINATE}


@dataclass(frozen=True)
class RuleConfig:
    n_players: int = 4
    copies_per_character: int = 3
    influences_per_player: int = 2
    starting_coins: int = 2
    treasury: int = 54  # 24 coins + 6 gold x 5 (A10); total coin value in the box
    coup_cost: int = 7
    assassinate_cost: int = 3
    tax_amount: int = 3
    steal_amount: int = 2
    foreign_aid_amount: int = 2
    forced_coup_threshold: int = 10  # A11
    intervention_enabled: bool = True  # A8
    intervention_reward: int = 1  # A9
    swap_on_proven_claim: bool = True  # A2
    assassin_refund_on_failed_challenge: bool = False  # A4
    max_turns: int = 400  # A1: draw beyond this

    def __post_init__(self):
        if not 3 <= self.n_players <= 5:
            raise ValueError("Intenções Ocultas is for 3-5 players")
        deck = self.copies_per_character * len(Character)
        if self.n_players * self.influences_per_player > deck:
            raise ValueError("not enough cards")
        if self.n_players * self.starting_coins > self.treasury:
            raise ValueError("treasury too small for starting coins")
