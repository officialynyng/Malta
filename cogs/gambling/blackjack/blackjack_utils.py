import random

SUITS = ["♠️", "♥️", "♦️", "♣️"]
RANKS = {
    1: "A", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7",
    8: "8", 9: "9", 10: "10", 11: "J", 12: "Q", 13: "K"
}

def create_deck():
    return [(v, s) for v in range(1, 14) for s in SUITS]

def draw_card(deck):
    if len(deck) < 10:
        deck[:] = create_deck()
    return deck.pop(random.randint(0, len(deck) - 1))


def hand_value(hand):
    values = [min(card[0], 10) for card in hand]
    total = sum(values)
    aces = sum(1 for v, _ in hand if v == 1)
    while total <= 11 and aces:
        total += 10
        aces -= 1
    return total

def card_to_emoji(card):
    rank, suit = card
    return f"`{RANKS[rank]}{suit}`"

def format_hand(hand, reveal_all=True):
    if not reveal_all:
        return f"{card_to_emoji(hand[0])} ❓"
    return " ".join(card_to_emoji(card) for card in hand)
