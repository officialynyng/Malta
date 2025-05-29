import random

SUITS = ["♠️", "♥️", "♦️", "♣️"]
RANKS = {
    1: "A", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7",
    8: "8", 9: "9", 10: "10", 11: "J", 12: "Q", 13: "K"
}

def create_shoe(decks=6):
    single_deck = [(v, s) for v in range(1, 14) for s in SUITS]
    shoe = single_deck * decks
    random.shuffle(shoe)
    return shoe

# To be assigned once in BlackjackGameView.shared_shoe = create_shoe()
def draw_from_shoe(shoe, reshuffle_callback=None):
    if len(shoe) < 15:
        if reshuffle_callback:
            reshuffle_callback()
    return shoe.pop()

def draw_card():
    from cogs.gambling.blackjack.blackjack import BlackjackGameView
    if len(BlackjackGameView.shared_shoe) < 15:
        BlackjackGameView.shared_shoe = create_shoe()
    return BlackjackGameView.shared_shoe.pop()


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
