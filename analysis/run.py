"""Sequential stages; each validates the pre-analysis code freeze."""
import argparse
import json
import sys
import time
from pathlib import Path
from common import CONFIG,save_json,sha,event,deadline,elapsed,archive_json


def verify_freeze():
    frozen=json.loads(Path('artifacts/code_freeze.json').read_text())
    for name,expected in frozen['sha256'].items():
        if sha(name)!=expected: raise RuntimeError('Execution code changed after freeze: '+name)
    manifest=json.loads(Path('artifacts/input_manifest.json').read_text())
    assert len(manifest['inputs'])==6
    for row in manifest['inputs']:
        if sha(row['cache'])!=row['expected_sha256']: raise RuntimeError('Input hash changed')


def main(stage):
    verify_freeze()
    if stage=='core':
        deadline('acceptance')
        import path_a,path_b
        start=time.monotonic()
        a,experiments,roster=path_a.run()
        b=path_b.run()
        save_json('artifacts/path_a.json',a)
        archive_json('artifacts/path_a.json')
        save_json('artifacts/path_b.json',b)
        identical=a['canonical']==b
        save_json('artifacts/independent_check.json',{'gate_I':identical,'exact_match':identical,'fields_checked':['formal_keys','roster_counts','N/K/L','equal_threshold','sensitivity_classification_changes','per_design_boolean_decisions'],'rate_absolute_tolerance':1e-12,'actually_exact':identical})
        if not identical: raise RuntimeError('Independent paths disagree')
        deadline('acceptance')
        event('implementation_and_roster_accepted',gate_G=a['audit']['gate_G'],gate_I=identical)
        if not a['audit']['gate_G']: raise RuntimeError('Gate G failed')
        save_json('artifacts/roster_audit.json',a['audit'])
        archive_json('artifacts/roster_audit.json')
        core={'gate_V':True,'gate_G':True,'gate_I':True,'M_pass':all(r['N']==267 and r['L']==0 for r in a['detection'] if r['target']=='ALL'),'detection':a['detection'],'sensitivity':a['sensitivity'],'C_triggers':a['C_triggers'],'boundary_sensitive':any(r['zero_misses_changed'] for r in a['sensitivity'])}
        save_json('artifacts/core.json',core)
        from plots import figure1
        figure1(core)
        deadline('core')
        event('core_completed',M_pass=core['M_pass'],computation_seconds=time.monotonic()-start)
    elif stage=='base':
        deadline('numeric')
        if not Path('figures/figure1.png').exists(): raise RuntimeError('Core figure absent')
        import path_a,functional
        # Fresh rerun is a deterministic input for the function stage; no changes to M.
        _,experiments,_=path_a.run()
        result=functional.build(experiments)
        functional.export(result)
        archive_json('artifacts/functional_base.json')
        archive_json('artifacts/controls.json')
        deadline('numeric')
        event('functional_base_saved',gate_B=result['gate_B'],summary_rows=len(result['summary']),detail_rows=len(result['details']))
    elif stage=='bootstrap':
        from resampling import run_bootstrap
        base=json.loads(Path('artifacts/functional_base.json').read_text())
        result=run_bootstrap(base)
        if result['status']!='complete': save_json('artifacts/bootstrap.json',result)
    elif stage=='secondary':
        from resampling import run_sensitivities
        run_sensitivities(json.loads(Path('artifacts/functional_base.json').read_text()),json.loads(Path('artifacts/bootstrap.json').read_text()))
    elif stage=='figure2':
        from plots import figure2
        figure2(json.loads(Path('artifacts/functional_base.json').read_text()),json.loads(Path('artifacts/bootstrap.json').read_text()))
    else: raise ValueError('Unknown stage')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('stage',choices=['core','base','bootstrap','secondary','figure2']); args=parser.parse_args()
    try: main(args.stage)
    except Exception as exc:
        # Retain existing outputs and a concise error without environment identifiers.
        event('stage_failed',stage=args.stage,error_type=type(exc).__name__,reason=str(exc))
        save_json('artifacts/failure_'+args.stage+'.json',{'stage':args.stage,'error_type':type(exc).__name__,'reason':str(exc),'elapsed_minutes':elapsed()})
        raise SystemExit(1)
