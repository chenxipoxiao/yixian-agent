#!/usr/bin/env bash
# One bounded GPU pilot, persistent across SSH disconnections.
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
export PATH="$HOME/.local/bin:$PATH"
session=longyao-pretrain
if tmux has-session -t "$session" 2>/dev/null; then
  printf 'Training session already exists: %s\n' "$session" >&2
  exit 1
fi
test -f runs/pretraining-data/longyao-v1/manifest.json
.venv/bin/python -c 'import torch; assert torch.cuda.is_available(), "CUDA unavailable"'
run_id="$(date -u +%Y%m%dT%H%M%SZ)-longyao-v1"
base="$project_root/runs/pretraining"
out="$base/$run_id"
log="$base/$run_id.log"
launcher="$base/$run_id.launch.sh"
mkdir -p "$base"
test ! -e "$out"
test ! -e "$log"
test ! -e "$launcher"
{
  printf '#!/usr/bin/env bash\nset -euo pipefail\ncd %q\n' "$project_root"
  printf 'export PATH="$HOME/.local/bin:$PATH"\n'
  printf 'exec %q -u %q --data %q --out %q --config %q --device cuda >%q 2>&1\n' \
    "$project_root/.venv/bin/python" "$project_root/tools/train_longyao_pretrain.py" \
    "$project_root/runs/pretraining-data/longyao-v1" "$out" \
    "$project_root/configs/longyao_pretrain.json" "$log"
} > "$launcher"
tmux new-session -d -s "$session" bash "$launcher"
.venv/bin/python - "$base/latest.json" "$out" "$log" "$session" <<'PY'
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
path, run_dir, log, session = sys.argv[1:]
pointer = {'launched_at_utc':datetime.now(timezone.utc).isoformat(),
           'run_dir':run_dir, 'log':log, 'tmux_session':session,
           'scope':'longyao_shuffled_recorded_board_reconstruction',
           'full_match_training':False}
Path(path).write_text(json.dumps(pointer, indent=2)+'\n', encoding='utf-8')
print(json.dumps(pointer))
PY
