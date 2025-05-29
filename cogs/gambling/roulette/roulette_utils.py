import random

ROULETTE_NUMBERS = list(range(0, 37))
ROULETTE_COLORS = {
    0: "green",
    **dict.fromkeys([1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36], "red"),
    **dict.fromkeys([2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35], "black")
}

def spin_roulette():
    result = random.choice(ROULETTE_NUMBERS)
    return result, ROULETTE_COLORS[result]

def payout(bet_type, choice, result):
    number, color = result
    if bet_type == "Red" and color == "red":
        return 2
    elif bet_type == "Black" and color == "black":
        return 2
    elif bet_type == "Number" and int(choice) == number:
        return 36
    return 0
