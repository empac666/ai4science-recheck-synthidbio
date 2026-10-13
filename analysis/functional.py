"""Frozen binding/KD rules and paired backbone descriptions."""
import csv
import json
import math
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from collections import Counter
from pathlib import Path
import numpy as np
from common import CONFIG, TARGETS, SETTINGS, save_json

MISSING={'','null','na','n/a','nan'}
UNITS={'M':Decimal(1),'mol/L':Decimal(1),'mM':Decimal('1e-3'),'uM':Decimal('1e-6'),'µM':Decimal('1e-6'),'μM':Decimal('1e-6'),'nM':Decimal('1e-9'),'pM':Decimal('1e-12')}
NUMBER=r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?'
PATTERN=re.compile(r'(?P<direction>>=|<=|≥|≤|>|<)?\s*(?P<number>'+NUMBER+r')\s*(?P<unit>[^\s]+)?')

def norm(s): return unicodedata.normalize('NFKC',str(s)).strip()

def binding(s):
    text=norm(s)
    if text.casefold() in MISSING: return 'missing'
    if text.upper() in ['TRUE','FALSE']: return text.upper()
    return 'conflict'

def header_unit(columns):
    candidates=[]
    for c in columns:
        if c=='kd': candidates.append((c,None))
        elif re.match(r'^kd\s*[\[(]',c):
            m=re.fullmatch(r'kd\s*(?:\(([^()]*)\)|\[([^\[\]]*)\])',c)
            if not m: raise ValueError('Unsupported KD header')
            u=norm(m.group(1) or m.group(2))
            if u not in UNITS: raise ValueError('Unknown KD header unit')
            candidates.append((c,u))
    if len(candidates)!=1: raise ValueError('Ambiguous KD columns')
    return candidates[0]

def parse_kd(raw, unit_header=None):
    s=norm(raw)
    source='header' if unit_header is not None else 'frozen_assumption'
    mult=UNITS.get(unit_header,Decimal(1))
    out={'raw':str(raw),'normalized':s,'unit_source':source,'multiplier':str(mult),'status':'conflict','direction':None,'value_mol_L':None,'reason':''}
    if unit_header is not None and unit_header not in UNITS:
        out['reason']='unknown_header_unit'; return out
    if s.casefold() in MISSING:
        out['status']='missing'; return out
    m=PATTERN.fullmatch(s)
    if not m: out['reason']='invalid_numeric_syntax'; return out
    cellunit=m.group('unit')
    if cellunit:
        out['unit_source']='cell'; out['unit']=cellunit
        if cellunit not in UNITS: out['reason']='unknown_cell_unit'; return out
        mult=UNITS[cellunit]; out['multiplier']=str(mult)
        if unit_header is not None and mult!=UNITS[unit_header]: out['reason']='unit_conflict'; return out
    try: value=Decimal(m.group('number'))*mult
    except InvalidOperation: out['reason']='invalid_number'; return out
    if not value.is_finite() or value<=0: out['reason']='nonpositive_or_nonfinite'; return out
    direction=m.group('direction')
    out.update(status='censored' if direction else 'point',direction=direction,value_mol_L=str(value))
    return out


def summarize_design(rows):
    bs=[r['binding_status'] for r in rows]; ks=[r['kd_parse'] for r in rows]
    enough=len({r['replicate'] for r in rows})>=2
    clear_yes=enough and all(b=='TRUE' for b in bs)
    clear_no=enough and all(b=='FALSE' for b in bs)
    mixed='TRUE' in bs and 'FALSE' in bs
    flag_conflict=any(b=='FALSE' and k['status'] in ['point','censored'] for b,k in zip(bs,ks))
    parse_conflict=any(k['status']=='conflict' for k in ks)
    binding_conflict='conflict' in bs
    conflict=flag_conflict or parse_conflict or binding_conflict
    quant=clear_yes and not conflict and all(k['status']=='point' for k in ks)
    values=[Decimal(k['value_mol_L']) for k in ks] if quant else []
    mean=sum(values)/len(values) if quant else None
    # Geometric summary is evaluated only during the permitted secondary window.
    nonquant=clear_yes and any(k['status'] in ['missing','censored'] for k in ks)
    known_no=clear_no and not conflict and all(k['status']=='missing' for k in ks)
    reasons=[]
    if not enough: reasons.append('fewer_than_two_replicates')
    if mixed: reasons.append('mixed_binding')
    if 'missing' in bs: reasons.append('missing_binding')
    if binding_conflict: reasons.append('invalid_binding')
    if parse_conflict: reasons.append('kd_parse_conflict')
    if flag_conflict: reasons.append('false_with_positive_kd')
    if nonquant: reasons.append('binding_nonquantifiable')
    states={threshold:('hit' if mean<=Decimal(threshold) else 'nonhit') if mean is not None else ('nonhit' if known_no else 'unknown') for threshold in CONFIG['functional_thresholds']}
    return {'n_replicates':len(rows),'clear_binding':clear_yes,'clear_nonbinding':clear_no,'mixed':mixed,'nonquantifiable':nonquant,'conflict':conflict,'known_nonbinding':known_no,'quantifiable':quant,'kd_mean_mol_L':str(mean) if mean is not None else None,'states':states,'reasons':reasons,'positive_points_mol_L':[str(v) for v in values]}


def state_counts(designs):
    return {k:sum(int(d[k]) for d in designs) for k in ['clear_binding','clear_nonbinding','mixed','nonquantifiable','conflict','quantifiable']}


def cell(designs, threshold):
    n=len(designs); counts=Counter(d['states'][threshold] for d in designs)
    a=counts['hit']; u=counts['unknown']; no=counts['nonhit']
    assert n==a+u+no
    rate=a/n if n else None; upper=(a+u)/n if n else None
    assert n==0 or 0<=rate<=upper<=1
    return {'n':n,'a':a,'u':u,'recorded_hit_rate':rate,'lower_bound':rate,'upper_bound':upper,'state_counts':state_counts(designs),'status':'ok' if n else 'not_estimable','reason':'' if n else 'missing_cell'}


def build(experiments):
    kdcol,unit=header_unit(experiments.columns)
    repeat_records=[]; design_records=[]; unit_issues=[]
    for (t,k),sub in experiments.groupby(['target','design'],sort=True):
        rows=[]
        for r in sub.to_dict('records'):
            parsed=parse_kd(r[kdcol],unit)
            rec={'target':t,'design':k,'setting':r['setting'],'backbone':int(r['backbone']) if r['backbone']==r['backbone'] else None,'replicate':r['replicate'],'binding_raw':r['binding'],'binding_status':binding(r['binding']),'kd_parse':parsed,'source_file':r['source_file'],'source_row':int(r['source_row'])}
            repeat_records.append(rec); rows.append(rec)
            if parsed['reason'] in ['unknown_cell_unit','unknown_header_unit','unit_conflict']: unit_issues.append(rec)
        d={'target':t,'design':k,'setting':rows[0]['setting'],'backbone':rows[0]['backbone'],**summarize_design(rows)}
        design_records.append(d)
    formal=[d for d in design_records if d['setting'] in SETTINGS]
    summary=[]; details=[]; missing=[]
    for t in TARGETS:
        bones=sorted({d['backbone'] for d in formal if d['target']==t})
        # Retain expected layout if a setting lacks a backbone.
        if len(bones)!=15: missing.append({'target':t,'reason':'backbone_count_not_15'})
        for b in bones:
            for m in SETTINGS:
                ds=[d for d in formal if d['target']==t and d['backbone']==b and d['setting']==m]
                for c in CONFIG['functional_thresholds']:
                    r={'target':t,'backbone':b,'setting':m,'threshold_mol_L':c,**cell(ds,c)}
                    details.append(r)
                    if not ds: missing.append({'target':t,'backbone':b,'setting':m})
        for m in SETTINGS:
            ds=[d for d in formal if d['target']==t and d['setting']==m]
            for c in CONFIG['functional_thresholds']:
                row={'target':t,'setting':m,'threshold_mol_L':c,**cell(ds,c)}
                group=[r for r in details if r['target']==t and r['setting']==m and r['threshold_mol_L']==c]
                assert all(row[f]==sum(r[f] for r in group) for f in ['n','a','u'])
                summary.append(row)
    gate=not unit_issues and not missing and len(details)==270
    comparisons=[]
    if gate:
        lookup={(r['target'],r['backbone'],r['setting'],r['threshold_mol_L']):r for r in details}
        for m in ['WN','WD']:
            for c in CONFIG['functional_thresholds']:
                diffs=[]; lo=[]; hi=[]
                for t in TARGETS:
                    bones=sorted({d['backbone'] for d in formal if d['target']==t})
                    for b in bones:
                        wm=lookup[t,b,m,c]; control=lookup[t,b,'C',c]
                        diffs.append(wm['recorded_hit_rate']-control['recorded_hit_rate'])
                        lo.append(wm['lower_bound']-control['upper_bound'])
                        hi.append(wm['upper_bound']-control['lower_bound'])
                point=float(np.mean(np.array(diffs).reshape(3,15),axis=1).mean())
                lower=float(np.mean(np.array(lo).reshape(3,15),axis=1).mean()); upper=float(np.mean(np.array(hi).reshape(3,15),axis=1).mean())
                assert lower-1e-12<=point<=upper+1e-12
                comparisons.append({'setting':m,'threshold_mol_L':c,'point_difference':point,'identification_bounds':[lower,upper],'direction_unidentified':lower<0<upper,'status':'ok'})
    finite=[]
    for t in TARGETS:
        for m in SETTINGS:
            ds=[d for d in formal if d['target']==t and d['setting']==m]
            vals=[float(d['kd_mean_mol_L']) for d in ds if d['quantifiable']]
            finite.append({'target':t,'setting':m,'n_quantifiable':len(vals),'n_total':len(ds),'min':min(vals) if vals else None,'quantiles_05_50_95':np.quantile(vals,[.05,.5,.95],method='linear').tolist() if vals else None,'max':max(vals) if vals else None})
    return {'gate_B':gate,'unit_issues':unit_issues,'missing_cells':missing,'summary':summary,'details':details,'comparisons':comparisons,'finite_kd':finite,'designs':design_records,'repeats':repeat_records,'controls':[d for d in design_records if d['setting'] not in SETTINGS],'unknown_designs':[d for d in formal if any(s=='unknown' for s in d['states'].values())]}


def export(result):
    save_json('artifacts/functional_base.json',result)
    fields=['target','backbone','setting','threshold_mol_L','n','a','u','recorded_hit_rate','lower_bound','upper_bound','state_counts','status','reason']
    with Path('functional_backbone_details.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for r in result['details']:
            row={k:('NA' if r[k] is None else r[k]) for k in fields}
            row['state_counts']=json.dumps(row['state_counts'],sort_keys=True,separators=(',',':'))
            w.writerow(row)
    fields=[k for k in fields if k!='backbone']
    with Path('artifacts/functional_summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for r in result['summary']:
            row={k:('NA' if r[k] is None else r[k]) for k in fields}; row['state_counts']=json.dumps(row['state_counts'],sort_keys=True,separators=(',',':')); w.writerow(row)
    save_json('artifacts/functional_unknowns.json',result['unknown_designs'])
    save_json('artifacts/controls.json',{'designs':result['controls'],'repeats':[r for r in result['repeats'] if r['setting'] not in SETTINGS]})
