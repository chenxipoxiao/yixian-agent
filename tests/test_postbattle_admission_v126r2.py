from tests.test_postbattle_admission_v126 import PostbattleAdmissionTests
import json,subprocess,shutil,unittest
from yixian import full_battle_v126r2 as engine

class ChaseSpaceFieldTests(unittest.TestCase):
    def test_fixed350_identity_does_not_gain_upgrade_or_cost_effect(self):
        engine.extension_contract()
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',
            str(engine.ROOT/'tests/postbattle_chase_v126r2_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertEqual(json.loads(p.stdout)['scenarios'],3)

if __name__=='__main__':unittest.main()
