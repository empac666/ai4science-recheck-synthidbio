"""Fetch only six frozen inputs; validate raw bytes before any analysis."""
import hashlib
import importlib.metadata
import json
import platform
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PIN = 'b2d65a39e0bd3b0bca9e82696bf6f1c306d8d34e'
INPUTS = [
 ('synthidbio_sequence/data/all_g_values.csv',64488,'8421e8368cefbd27beb8d136b125f3c8a137f836ff57ab8adabd43364be93757'),
 ('synthidbio_sequence/data/VEGF-A/vegfa_data.csv',114207,'321cc01da075c5f0b535a82f0d031b1bfaec1b88337f1541bc5ddd1be4103fe2'),
 ('synthidbio_sequence/data/PD_L1/pdl1_data.csv',108131,'c8089b83259ac344805e724d4593884f4c67e9c617a55a2d2209d1838c4e0d2b'),
 ('synthidbio_sequence/data/SC2RBD/sc2rbd_data.csv',110848,'e132509696cb528eb3e5bdf00d3e92b45d05df21b2ef736000fa4d67bae2e03f'),
 ('README.md',24147,'861ed6bd339c7215f66d7c53dcb875566a12c39ba1648e80e29388b016a71da9'),
 ('LICENSE',11358,'cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30'),
]

def now(): return datetime.now(timezone.utc).isoformat()

def main():
    clock = Path('artifacts/run_clock.json')
    if clock.exists():
        start = json.loads(clock.read_text())['start_epoch']
    else:
        start = time.time()
        clock.write_text(json.dumps({'start_epoch':start,'start_utc':now(),'hard_limit_minutes':120},indent=2)+'\n')
    manifest = {'upstream_commit': PIN, 'inputs':[], 'pdf':{'status':'not_downloaded_reference_only','sha256':'6b9cadfdbc70e54eb711fc670139a1f7f61c4a79cafd965b6e0c2ba651887b04','threshold_source':'Supplementary Table S2 and Figures S24/S25'}}
    for name,size,expected in INPUTS:
        path = Path('data/cache') / name
        url = f'https://raw.githubusercontent.com/google-deepmind/synthidbio/{PIN}/{name}'
        attempts = []
        for attempt in range(3):
            if time.time()-start > 15*60: raise RuntimeError('Acquisition deadline exceeded')
            try:
                if path.exists(): b=path.read_bytes(); source='verified_cache'
                else:
                    with urllib.request.urlopen(url,timeout=30) as r: b=r.read()
                    source='network'
                actual=hashlib.sha256(b).hexdigest()
                if len(b)!=size or actual!=expected: raise ValueError('Frozen input mismatch: '+name)
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(b)
                attempts.append({'attempt':attempt+1,'status':'pass'})
                manifest['inputs'].append({'file':name,'cache':str(path),'url':url,'bytes':len(b),'sha256':actual,'expected_sha256':expected,'verified':True,'obtained_at_utc':now(),'source':source,'attempts':attempts})
                print(name, 'verified',len(b),flush=True)
                break
            except ValueError: raise
            except Exception as e:
                attempts.append({'attempt':attempt+1,'status':'failed','error_type':type(e).__name__})
                if attempt==2: raise
    manifest['completed_utc']=now()
    manifest['elapsed_minutes']=(time.time()-start)/60
    Path('artifacts/input_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    versions={'python':platform.python_version()}
    for name in ['numpy','pandas','matplotlib','Pillow']:
        try: versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: versions[name]='missing'
    Path('artifacts/software_versions.json').write_text(json.dumps(versions,indent=2)+'\n')
    print(versions)

if __name__=='__main__': main()
