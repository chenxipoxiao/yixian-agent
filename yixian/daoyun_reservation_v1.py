"""Ordinary Dao Yun reservation for an explicitly supplied, chronological player timeline."""
from dataclasses import dataclass, replace
from typing import Mapping


@dataclass(frozen=True)
class DaoYunReservation:
    menu: int = 0
    offered: tuple[int, ...] = ()
    selected: int | None = None
    required_realm: int | None = None
    claimed: bool = False

    def open_menu(self, menu: int, offered: tuple[int, ...]):
        """A new trigger replaces any still-unfulfilled selection."""
        if type(menu) is not int or menu < 1 or menu < self.menu:
            raise ValueError("Invalid or stale menu")
        if not offered or any(type(card) is not int for card in offered):
            raise ValueError("Missing card options")
        offered = tuple(offered)
        if menu == self.menu:
            if self.offered != offered:
                raise ValueError("Changed options require explicit refresh handling")
            return self
        return DaoYunReservation(menu=menu, offered=offered)

    def select(self, card: int, realms: Mapping[int, int]):
        if type(card) is not int or card not in self.offered:
            raise ValueError("Card outside offered options")
        if card == 27 or realms.get(card) not in (4, 5):
            raise ValueError("Selection outside ordinary realm-gated cards")
        if self.selected is not None:
            if card != self.selected:
                raise ValueError("Menu already resolved")
            return self
        return replace(self, selected=card, required_realm=realms[card])

    def advance(self, realm: int, hand: tuple[int, ...]):
        """Apply state and hand together at a caller-provided ordinary reward boundary."""
        if type(realm) is not int or realm not in range(1, 6):
            raise ValueError("Unknown realm")
        if self.claimed or self.required_realm is None or realm < self.required_realm:
            return self, hand
        return replace(self, claimed=True), (*hand, self.selected)
