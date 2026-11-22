"""Damage-only preview AFTER a simulated terminal state; never pays rewards.

Unlike the old settlement-only audit, this uses the engine's winner and HP.
Full match mutation remains with the reward/resource ledger, not this preview.
"""
from .settlement import ordinary_destiny_damage
from .effects import EffectEngine


def calculate_terminal_damage(compiled, result):
    if (result.get('terminated') is not True or result.get('truncated') is not False
            or type(result.get('winner')) is not int or result['winner'] not in (0,1)):
        return {'resolved':False,'reason':'no_terminal_winner','life_damage':None,'training_label_allowed':False}
    if any(p.get('direct_destiny_lost')!=0 for p in result['players']):
        return {'resolved':False,'reason':'in_combat_destiny_ledger_required','life_damage':None,'training_label_allowed':False}
    winner=result['winner'];loser=1-winner
    w,l=(compiled['effect_players'][i] for i in (winner,loser))
    if w.get('is_mirror') is not False or l.get('is_mirror') is not False:
        raise ValueError('Explicit live non-mirror participants required')
    hp=result['players'][winner]['hp']-result['players'][loser]['hp']
    base=ordinary_destiny_damage(compiled['battle']['players'][0]['round_number'],hp)
    damage=base;events=[];engine=EffectEngine.from_local()
    def change(effect,new):
        nonlocal damage
        events.append({'effect':effect,'before':damage,'after':new});damage=new
    if 2011 in w['season_choices']:change('season2011',max(1,damage-engine.kindness_reduction))
    tune=result['players'][loser].get('kindness_tune_stacks')
    if type(tune) is not int or tune<0:raise ValueError('Explicit terminal kindness-tune state required')
    if tune>0 and damage>0:change('buff210',max(1,damage-tune))
    # Current ranked season explicitly excludes talent resonance by user rule.
    if compiled['context'].get('resonance_selected')!=0:raise ValueError('Unknown ranked resonance rule')
    fates=set(l['fates']);counter=l.get('talent_counters');pending=[]
    if 27 in fates and damage>engine.dragon_scale_limit:change('talent27_cap',engine.dragon_scale_limit)
    if 45 in fates and damage>0 and damage%2==0:change('talent45',damage//2)
    def remaining(fate):
        if not isinstance(counter,dict):raise ValueError('Explicit before-battle talent counters required')
        v=counter.get(str(fate),0)
        if type(v) is not int:raise ValueError('Invalid talent counter')
        return v>0
    if 105 in fates and remaining(105) and damage>=engine.guard_threshold:
        change('talent105',0);pending.append({'kind':'consume_fate_counter','fate':105})
    if damage>=l['life']:
        eligible=sorted(f for f in fates&{7,65,83,154} if remaining(f))
        if len(eligible)>1:
            return {'resolved':False,'reason':'multiple_survival_effect_order_unknown','life_damage':None,'training_label_allowed':False}
        if eligible:
            f=eligible[0];change(f'talent{f}_survival',l['life']-1)
            pending.append({'kind':'survival_counter_and_reward','fate':f})
    return {'resolved':True,'winner':winner,'loser':loser,'hp_difference':hp,'base_damage':base,
            'life_damage':damage,'loser_destiny_before':l['life'],'loser_destiny_after':l['life']-damage,
            'events':events,'pending_match_effects':pending,'match_state_mutated':False,
            'full_match_transition_complete':False,'training_label_allowed':False}
