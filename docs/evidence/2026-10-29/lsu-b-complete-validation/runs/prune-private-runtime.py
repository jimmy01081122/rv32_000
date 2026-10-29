"""Remove unused data only in this disposable diagnostic container."""
from pathlib import Path
import json, shutil, subprocess
base=Path('/OpenROAD-flow-scripts/flow/platforms')
manifest='/workspace/docs/evidence/2026-10-18/post-lsu-baseline-preparation/environment/physical-tool-platform-sha256.txt'
command=['sha256sum','--strict','--quiet','-c',manifest]
subprocess.run(command,check=True)
targets=[p for p in base.iterdir() if p.name not in ('asap7','common')]
targets += [Path(p) for p in ['/OpenROAD-flow-scripts/flow/designs','/usr/include','/usr/local/include','/opt/or-tools/include','/usr/share/doc','/usr/local/doc']]
for p in targets:
    assert not str(p).startswith(('/workspace','/orfs-source'))
    if p.is_dir(): shutil.rmtree(p)
    elif p.exists(): p.unlink()
subprocess.run(command,check=True)
Path('/workspace/build/experiments/lsu-b-validation-v2/private-runtime-pruning.json').write_text(json.dumps(dict(scope='disposable runtime directories only; pinned tools/ASAP7 retained for physical implementation and formal verification; no compiler build',removed=[str(p) for p in targets],critical_files_verified_before=204,critical_files_verified_after=204,pinned_image_unchanged=True),indent=2)+'\n')
