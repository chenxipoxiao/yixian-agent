"""Prospective baseline fix; does not change the frozen v185 candidate protocol.

CardConfig.anima is signed: positive gains qi and negative spends it. chargeQi
is a different card field and cannot substitute for that ordinary qi gain.
Any use of this revised ordering needs new candidate/panel rewards.
"""


def numeric_priority(card, catalogue, pressure, style):
    c = catalogue[card]
    anima = float(c.get('anima', 0))
    qi_gain = max(0., anima)
    cost = max(0., -anima)
    defense = float(c.get('def', 0))
    attack = float(c.get('attack', 0)) * max(1., float(c.get('attackCount', 0)))
    weights = ((4., 1.6, 1.), (3., .7, 1.8), (5., 2.5, .5))[style]
    return -(weights[0]*qi_gain - 2.*cost + weights[1]*pressure*defense + weights[2]*attack), card
