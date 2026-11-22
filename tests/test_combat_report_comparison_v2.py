from copy import deepcopy
import json,unittest
from pathlib import Path
from yixian.combat_report_comparison_v2 import v79_contract_only_change
from yixian.full_battle_v79r2 import PROOF_SHA

class MigrationComparisonTests(unittest.TestCase):
    def pair(self):
        # Fully synthetic old/new cases, with explicit195 representation only.
        old={'record_id':'fixture','all_four_match':True,'compiled':{
          'effect_players':[{'fates':[195]},{'fates':[]}],
          'battle':{'players':[{'spirit_hexagram_evolves_stacks':1},{}]},
          'declared_components':[{'raw_cards':[0,0],'compiled_fates':{'player_fields':{'spirit_hexagram_evolves_stacks':1},'coverage':[{'raw_id':195}]}},{'raw_cards':[0,0],'compiled_fates':{'player_fields':{},'coverage':[]}}]},
          'simulation':{'initial':[{'spirit_hexagram_evolves_stacks':1},{}],'winner':0,'hp_delta':11,'turns':5,'used_randomness':False,'trace':[{'hp':11}]},'settlement':{'life_damage':3}}
        new=deepcopy(old);c=new['compiled'];c['battle']['players'][0].pop('spirit_hexagram_evolves_stacks');new['simulation']['initial'][0].pop('spirit_hexagram_evolves_stacks')
        cf=c['declared_components'][0]['compiled_fates'];cf['player_fields']={};cf['coverage']=[]
        c['battle']['hexagram_fates']={'players':[{'fate_ids':[195],'starting_raw_cards':[0,0]},{'fate_ids':[],'starting_raw_cards':[0,0]}]}
        c['hexagram_fates_v79_context']={'evidence_sha256':PROOF_SHA,'ownership_from_start':True,'original_board_required':True,'training_label_allowed':False}
        new['simulation']['hexagram_fates_v79']={'evidence_sha256':PROOF_SHA,'events':[],'players':[{'player_index':0,'fate_ids':[195],'qualifying_start_count':0,'explain_active':False,'pending439':False},{'player_index':1,'fate_ids':[],'qualifying_start_count':0,'explain_active':False,'pending439':False}],'recorded_action_log':False,'training_label_allowed':False}
        return old,new
    def test_exact_migration_only(self):
        old,new=self.pair();self.assertTrue(v79_contract_only_change(old,new));self.assertFalse(v79_contract_only_change(old,old))
    def test_terminal_trace_and_settlement_cannot_be_hidden(self):
        for field,value in [('winner',1),('hp_delta',12),('turns',6),('used_randomness',True),('trace',[{'hp':12}])]:
            old,new=self.pair();new['simulation'][field]=value;self.assertFalse(v79_contract_only_change(old,new))
        old,new=self.pair();new['settlement']['life_damage']=4;self.assertFalse(v79_contract_only_change(old,new))
    def test_start_ownership_and_other_fields_must_match(self):
        old,new=self.pair();new['compiled']['battle']['players'][1]['qi']=9;self.assertFalse(v79_contract_only_change(old,new))
        old,new=self.pair();new['compiled']['battle']['hexagram_fates']['players'][0]['starting_raw_cards']=[0];self.assertFalse(v79_contract_only_change(old,new))
    def test_metadata_must_be_bound_and_cannot_enable_training(self):
        for field,value in [('evidence_sha256','bad'),('training_label_allowed',True),('recorded_action_log',True),('extra',1)]:
            old,new=self.pair();new['simulation']['hexagram_fates_v79'][field]=value;self.assertFalse(v79_contract_only_change(old,new))
    def test_195_lifecycle_rejects_unpaired_end_and_duplicate_gain(self):
        event={'fate_id':195,'phase':'positive_qi_add439','player_index':0,'active_player_index':1,'amount':1}
        old,new=self.pair();meta=new['simulation']['hexagram_fates_v79'];meta['events']=[event];meta['players'][0]['pending439']=True;self.assertTrue(v79_contract_only_change(old,new))
        meta['events'].append(deepcopy(event));self.assertFalse(v79_contract_only_change(old,new))
    def test_original_contract_and_expected_fields_not_discarded(self):
        old,new=self.pair();new['expected']={'winner':0};self.assertFalse(v79_contract_only_change(old,new))

if __name__=='__main__':unittest.main()
