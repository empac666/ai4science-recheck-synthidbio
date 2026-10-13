"""One frozen index draw, checked paired resampling; no partial intervals."""
import json
import math
import time
from pathlib import Path
import numpy as np
from common import CONFIG,TARGETS,SETTINGS,save_json,sha,event,elapsed,deadline


def cube(base, field, threshold, geometric=False):
    values=np.zeros((3,15,3),dtype=float)
    if geometric:
        for ti,t in enumerate(TARGETS):
            bones=sorted({r['backbone'] for r in base['details'] if r['target']==t})
            for bi,b in enumerate(bones):
                for mi,m in enumerate(SETTINGS):
                    ds=[d for d in base['designs'] if d['target']==t and d['backbone']==b and d['setting']==m]
                    # Keep exactly the primary quantifiable set.
                    hits=sum(int(math.exp(sum(math.log(float(v)) for v in d['positive_points_mol_L'])/len(d['positive_points_mol_L']))<=float(threshold)) for d in ds if d['quantifiable'])
                    values[ti,bi,mi]=hits if field=='a' else len(ds)
    else:
        for ti,t in enumerate(TARGETS):
            bones=sorted({r['backbone'] for r in base['details'] if r['target']==t})
            for bi,b in enumerate(bones):
                for mi,m in enumerate(SETTINGS):
                    r=next(r for r in base['details'] if (r['target'],r['backbone'],r['setting'],r['threshold_mol_L'])==(t,b,m,threshold))
                    values[ti,bi,mi]=r[field]
    return values


def paired_draws(delta, indices):
    return delta[np.arange(3)[None,:,None],indices].mean(axis=2).mean(axis=1)


def interval(draws):
    if draws.shape!=(10000,) or not np.isfinite(draws).all(): raise ValueError('Incomplete bootstrap')
    return {'iterations':10000,'standard_deviation':float(np.std(draws,ddof=1)),'percentile_interval':np.quantile(draws,[.025,.975],method='linear').tolist()}


def publish_bootstrap(rows,check_passed,minutes):
    if len(rows)!=4 or not check_passed or minutes>=75:
        return {'status':'not_completed','reason':'bootstrap_time_cutoff_or_failed_check','comparisons':[]}
    return {'status':'complete','comparisons':rows,'checks_passed':True}


def run_bootstrap(base):
    deadline('bootstrap')
    if not base['gate_B']: return {'status':'ineligible','comparisons':[],'reason':'Gate B failed'}
    if Path('artifacts/bootstrap_indices.npy').exists(): raise RuntimeError('Do not redraw or overwrite indices')
    rng=np.random.Generator(np.random.PCG64(2026100901))
    indices=rng.integers(0,15,size=(10000,3,15),endpoint=False,dtype=np.int64)
    np.save('artifacts/bootstrap_indices.npy',indices,allow_pickle=False)
    # A separate frequency representation checks every replicate in all comparisons.
    weights=np.zeros((10000,3,15),dtype=np.int64)
    for t in range(3):
        for j in range(15): weights[:,t,j]=(indices[:,t,:]==j).sum(axis=1)
    assert np.all(weights.sum(axis=2)==15)
    rows=[]
    for m in ['WN','WD']:
        mi=SETTINGS.index(m)
        for c in CONFIG['functional_thresholds']:
            deadline('bootstrap')
            a=cube(base,'a',c); n=cube(base,'n',c); rates=a/n
            delta=rates[:,:,mi]-rates[:,:,0]
            draws=paired_draws(delta,indices)
            check=(weights*delta[None,:,:]).sum(axis=(1,2))/45
            assert np.max(np.abs(draws-check))<=1e-12
            point=next(r['point_difference'] for r in base['comparisons'] if r['setting']==m and r['threshold_mol_L']==c)
            assert abs(delta.mean()-point)<=1e-12
            rows.append({'setting':m,'threshold_mol_L':c,**interval(draws)})
    result=publish_bootstrap(rows,True,elapsed())
    result.update(index_file='artifacts/bootstrap_indices.npy',index_sha256=sha('artifacts/bootstrap_indices.npy'),numpy_version=np.__version__,index_shape=list(indices.shape),index_bytes=indices.nbytes,seed=2026100901,standard_deviation_ddof=1,quantile_method='linear')
    save_json('artifacts/bootstrap.json',result)
    event('bootstrap_completed' if result['status']=='complete' else 'bootstrap_stopped',status=result['status'])
    return result


def secondary_window(minutes): return 75<=minutes<80

def run_sensitivities(base, bootstrap):
    if not secondary_window(elapsed()): raise RuntimeError('Secondary numeric work allowed only during minutes 75–80')
    if bootstrap['status']!='complete': raise RuntimeError('Bootstrap not completed')
    indices=np.load('artifacts/bootstrap_indices.npy',allow_pickle=False)
    assert sha('artifacts/bootstrap_indices.npy')==bootstrap['index_sha256']
    weight_rows=[]
    for m in ['WN','WD']:
        mi=SETTINGS.index(m)
        for c in CONFIG['functional_thresholds']:
            deadline('numeric')
            a=cube(base,'a',c); n=cube(base,'n',c)
            sample_a=a[np.arange(3)[None,:,None],indices].sum(axis=2)
            sample_n=n[np.arange(3)[None,:,None],indices].sum(axis=2)
            main=next(r['point_difference'] for r in base['comparisons'] if r['setting']==m and r['threshold_mol_L']==c)
            target_equal=(a[:,:,mi]/n[:,:,mi]-a[:,:,0]/n[:,:,0]).mean(axis=1)
            for ti,t in enumerate(TARGETS):
                point=float(a[ti,:,mi].sum()/n[ti,:,mi].sum()-a[ti,:,0].sum()/n[ti,:,0].sum())
                draws=sample_a[:,ti,mi]/sample_n[:,ti,mi]-sample_a[:,ti,0]/sample_n[:,ti,0]
                ref=float(target_equal[ti])
                weight_rows.append({'target':t,'setting':m,'threshold_mol_L':c,'micro_difference':point,'backbone_equal_reference':ref,'opposite_direction':point*ref<0,'magnitude_change_gt_0_05':abs(point-ref)>.05,**interval(draws)})
            point=float(a[:,:,mi].sum()/n[:,:,mi].sum()-a[:,:,0].sum()/n[:,:,0].sum())
            draws=sample_a[:,:,mi].sum(axis=1)/sample_n[:,:,mi].sum(axis=1)-sample_a[:,:,0].sum(axis=1)/sample_n[:,:,0].sum(axis=1)
            weight_rows.append({'target':'ALL','setting':m,'threshold_mol_L':c,'micro_difference':point,'backbone_equal_reference':main,'opposite_direction':point*main<0,'magnitude_change_gt_0_05':abs(point-main)>.05,**interval(draws)})
    deadline('numeric')
    save_json('artifacts/weight_sensitivity.json',{'status':'complete','index_sha256':bootstrap['index_sha256'],'comparisons':weight_rows})
    event('weight_sensitivity_completed')
    geom_rows=[]; design_changes=[]
    for m in ['WN','WD']:
        mi=SETTINGS.index(m)
        for c in CONFIG['functional_thresholds']:
            deadline('numeric')
            a=cube(base,'a',c,geometric=True); n=cube(base,'n',c)
            delta=a[:,:,mi]/n[:,:,mi]-a[:,:,0]/n[:,:,0]
            point=float(delta.mean())
            main=next(r['point_difference'] for r in base['comparisons'] if r['setting']==m and r['threshold_mol_L']==c)
            geom_rows.append({'setting':m,'threshold_mol_L':c,'geometric_difference':point,'arithmetic_difference':main,'change':point-main,'opposite_direction':point*main<0,'magnitude_change_gt_0_05':abs(point-main)>.05,**interval(paired_draws(delta,indices))})
    for d in base['designs']:
        if d['setting'] not in SETTINGS or not d['quantifiable']: continue
        geom=math.exp(sum(math.log(float(v)) for v in d['positive_points_mol_L'])/len(d['positive_points_mol_L']))
        changed={c:(geom<=float(c))!=(d['states'][c]=='hit') for c in CONFIG['functional_thresholds']}
        if any(changed.values()): design_changes.append({'target':d['target'],'design':d['design'],'setting':d['setting'],'arithmetic_mol_L':d['kd_mean_mol_L'],'geometric_mol_L':geom,'changed':changed})
    deadline('numeric')
    save_json('artifacts/repeat_sensitivity.json',{'status':'complete','index_sha256':bootstrap['index_sha256'],'quantifiable_set_unchanged':True,'comparisons':geom_rows,'changed_designs':design_changes})
    event('repeat_sensitivity_completed')
    return weight_rows,geom_rows
