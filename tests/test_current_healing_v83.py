import json,shutil,subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class HealingV83Tests(unittest.TestCase):
    def test_boundaries(self):
        for name in ('current_spirit_outburst_v83_probe.mjs','current_yan_qi_v83_probe.mjs','current_healing_v83_probe.mjs'):
            with self.subTest(probe=name):
                p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(ROOT/'tests'/name)],cwd=ROOT,capture_output=True,text=True,encoding='utf8',timeout=90)
                self.assertEqual(p.returncode,0,p.stdout+p.stderr)
                result=json.loads(p.stdout);self.assertTrue(result['passed']);self.assertGreater(result['scenarios'],0)
                print(name,result,flush=True)
