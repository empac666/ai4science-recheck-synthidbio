"""Frozen constants and output utilities; no shared cleaning between paths."""
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

CONFIG=json.loads(Path('analysis/config.json').read_text())
TARGETS=CONFIG['targets']
SETTINGS=['C','WN','WD']
CACHE=Path('data/cache/synthidbio_sequence/data')
EXPERIMENTS=[('VEGF-A',CACHE/'VEGF-A/vegfa_data.csv'),('PD-L1',CACHE/'PD_L1/pdl1_data.csv'),('SC2RBD',CACHE/'SC2RBD/sc2rbd_data.csv')]
GFILE=CACHE/'all_g_values.csv'

def save_json(path, data):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def elapsed(): return (time.time()-json.loads(Path('artifacts/run_clock.json').read_text())['start_epoch'])/60

def event(name, **kwargs):
    row={'event':name,'utc':datetime.now(timezone.utc).isoformat(),'elapsed_minutes':elapsed(),**kwargs}
    with Path('artifacts/timeline.jsonl').open('a') as f: f.write(json.dumps(row,ensure_ascii=False)+'\n')
    print(json.dumps(row,ensure_ascii=False),flush=True)

def deadline(name):
    if elapsed()>=CONFIG['deadlines_minutes'][name]: raise RuntimeError('Deadline reached: '+name)

def archive_json(path):
    import gzip
    original=Path(path)
    target=Path(str(path)+'.gz')
    target.write_bytes(gzip.compress(original.read_bytes(),mtime=0))
    return {'path':str(target),'sha256':sha(target),'uncompressed_sha256':sha(original)}
