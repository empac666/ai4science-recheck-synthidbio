"""Reproduce the blocked state in an isolated relative directory."""
import json
import shutil
import subprocess
import sys
from datetime import datetime,timezone
from pathlib import Path


def main():
    destination=Path('reproduction')/datetime.now(timezone.utc).strftime('run-%Y%m%dT%H%M%S')
    destination.mkdir(parents=True,exist_ok=False)
    for directory in ['analysis','tests']:
        shutil.copytree(directory,destination/directory,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in ['PREREG.md','feasibility.md','SHA256SUMS','requirements.lock']:
        shutil.copy2(name,destination/name)
    (destination/'artifacts').mkdir();(destination/'figures').mkdir();(destination/'data/cache').mkdir(parents=True)
    shutil.copy2('artifacts/code_freeze.json',destination/'artifacts/code_freeze.json')
    # The historical timer is deliberately not copied; this is a separate run.
    subprocess.run([sys.executable,'analysis/acquire.py'],cwd=destination,check=True)
    expected=json.loads(Path('artifacts/software_versions.json').read_text())
    actual=json.loads((destination/'artifacts/software_versions.json').read_text())
    if actual!=expected: raise SystemExit('Software versions differ; install requirements.lock before reproducing.')
    result=subprocess.run([sys.executable,'analysis/run.py','core'],cwd=destination)
    if result.returncode!=1: raise SystemExit('Unexpected core status')
    failure=json.loads((destination/'artifacts/failure_core.json').read_text())
    if failure['reason']!='Unknown target': raise SystemExit('Unexpected failure reason')
    for script in ['diagnose_block.py','diagnostic_rosters.py','blocked_figure.py']:
        subprocess.run([sys.executable,'analysis/'+script],cwd=destination,check=True)
    print('Blocked state reproduced in '+str(destination))

if __name__=='__main__': main()
