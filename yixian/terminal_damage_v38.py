"""Gross terminal damage with civet gain requests kept separate from net life.

The client display helper does not prove authoritative gain capping or survival
ordering. For these cases we can compare a life-independent gross damage, but
must not publish an invented authoritative before/after destiny balance.
"""
from .terminal_damage import calculate_terminal_damage as previous

def calculate_terminal_damage(compiled,result):
    receipt=result.get('civet_v38')
    if receipt is None:return previous(compiled,result)
    gains=receipt.get('requested_destiny_gains')
    if (not isinstance(gains,list) or len(gains)!=2
            or any(type(v) is not int or v<0 for v in gains)):
        raise ValueError('Explicit civet gain requests required')
    if not any(gains):return previous(compiled,result)
    winner=result.get('winner')
    if type(winner) is int and winner in (0,1):
        loser=1-winner
        if gains[loser] and set(compiled['effect_players'][loser]['fates'])&{7,65,83,154}:
            return {'resolved':False,'reason':'civet_survival_gain_order_unresolved','life_damage':None,
                    'requested_destiny_gains':list(gains),'training_label_allowed':False}
    answer=previous(compiled,result)
    if answer.get('resolved'):
        answer.pop('loser_destiny_before',None)
        answer.pop('loser_destiny_after',None)
        answer.update(damage_scope='gross_terminal_loss_not_net_destiny_change',
                      requested_destiny_gains=list(gains),authoritative_destiny_gain_resolved=False,
                      authoritative_post_battle_destiny=None)
    return answer
