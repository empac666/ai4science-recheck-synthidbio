"""Path A: fresh positional CSV import, pandas filtering and groupby."""
import csv
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path
import numpy as np
import pandas as pd
from common import CONFIG, TARGETS, SETTINGS, EXPERIMENTS, GFILE


def norm(value): return unicodedata.normalize('NFKC',str(value)).strip()
def target(value):
    k=norm(value).casefold()
    if k not in CONFIG['target_aliases']: raise ValueError('Unknown target')
    return CONFIG['target_aliases'][k]
def key(value):
    k=norm(value).casefold()
    if not k: raise ValueError('Empty design key')
    return k

def backbone(value, formal):
    v=norm(value)
    if not v and not formal: return None
    m=re.fullmatch(r'Backbone (\d+)',v)
    if not m: raise ValueError('Invalid backbone')
    return int(m[1])

def read_table(path, kind):
    with Path(path).open(newline='') as f: headers=next(csv.reader(f))
    positions=[i for i,h in enumerate(headers) if h in ('Plate Target ID','Plate_Target_ID')]
    if not positions: raise ValueError('Missing target column')
    df=pd.read_csv(path,header=0,names=[f'p{i}' for i in range(len(headers))],dtype=str,keep_default_na=False)
    for j in positions[1:]:
        if not df[f'p{positions[0]}'].map(norm).equals(df[f'p{j}'].map(norm)): raise ValueError('Conflicting duplicate target headers')
    # Empty index columns are retained only as source positions.
    selected={f'p{i}':h.rstrip() for i,h in enumerate(headers) if h and (i not in positions or i==positions[0])}
    df=df[list(selected)].rename(columns=selected)
    df=df.rename(columns={headers[positions[0]].rstrip():'raw_target'})
    df['source_row']=np.arange(2,len(df)+2)
    df['source_file']=str(path.resolve().relative_to(Path('data/cache').resolve()))
    namecol='unique_name' if kind=='g' else 'name'
    catcol='subset_name' if kind=='g' else 'Subset_Name'
    df['target']=df['raw_target'].map(target)
    df['design']=df[namecol].map(key)
    if not df[catcol].isin(CONFIG['settings']).all(): raise ValueError('Unknown or missing setting')
    df['setting']=df[catcol].map(CONFIG['settings'])
    bonecol='sample_id' if kind=='g' else 'Backbone_ID'
    df['backbone']=[backbone(v,s in SETTINGS) for v,s in zip(df[bonecol],df['setting'])]
    normmap=df[['source_file','source_row','raw_target','target',namecol,'design']].rename(columns={namecol:'raw_design'}).to_dict('records')
    # Every original target column is recorded, including the redundant header.
    with Path(path).open(newline='') as f:
        rows=list(csv.reader(f))[1:]
    for out, row in zip(normmap,rows):
        out['target_columns']=[{'position':j,'raw':row[j],'normalized':norm(row[j])} for j in positions]
        out['normalized_design']=norm(out['raw_design'])
    pkey=['target','design']
    if kind=='e':
        df['replicate']=df['replicate'].map(norm)
        if (df['replicate']=='').any(): raise ValueError('Empty replicate key')
        pkey+=['replicate']
    # Compare all scientific fields, including sequence internally, never export it.
    excluded={'source_row','source_file',namecol,'raw_target'}
    compare=[c for c in df if c not in excluded]
    dup=[]; collisions=[]
    for groupkey,group in df.groupby(pkey,sort=True,dropna=False):
        if group[namecol].nunique()>1 or group['raw_target'].nunique()>1:
            collisions.append({'key':list(groupkey),'raw_names':sorted(group[namecol].unique().tolist()),'rows':group['source_row'].tolist()})
        if len(group)>1:
            if len(group[compare].drop_duplicates())!=1: raise ValueError('Conflicting primary-key duplicates')
            dup.append({'key':list(groupkey),'raw_rows':len(group),'source_rows':group['source_row'].tolist()})
    df=df.drop_duplicates(pkey).copy()
    return df, {'file':str(path.resolve().relative_to(Path('data/cache').resolve())),'raw_rows':len(rows),'retained_rows':len(df),'duplicates':dup,'collisions':collisions,'normalization':normmap}


def decimal_score(v):
    try: d=Decimal(v)
    except InvalidOperation: raise ValueError('Non-numeric detection score')
    if not d.is_finite() or not Decimal(0)<=d<=Decimal(1): raise ValueError('Invalid detection score')
    return d


def run():
    g,ga=read_table(GFILE,'g')
    experiments=[]; audits=[ga]
    for expected,path in EXPERIMENTS:
        e,ea=read_table(path,'e')
        if not (e['target']==expected).all(): raise ValueError('File target mismatch')
        experiments.append(e); audits.append(ea)
    e=pd.concat(experiments,ignore_index=True)
    # Metadata invariant across technical repeats; design denominator is deduplicated.
    invariants=e.groupby(['target','design'])[['setting','backbone']].nunique(dropna=False)
    if (invariants>1).any().any(): raise ValueError('Replicate metadata conflict')
    roster=e[['target','design','setting','backbone']].drop_duplicates(['target','design'])
    joined=roster.merge(g,on=['target','design'],how='outer',indicator=True,suffixes=('_experiment','_g'),validate='one_to_one')
    joinlists={s:joined.loc[joined['_merge']==s,['target','design']].values.tolist() for s in ['left_only','right_only','both']}
    matched=joined[joined['_merge']=='both']
    if not (matched['setting_experiment']==matched['setting_g']).all(): raise ValueError('Setting mismatch across rosters')
    formal=matched['setting_g'].isin(SETTINGS)
    if not (matched.loc[formal,'backbone_experiment']==matched.loc[formal,'backbone_g']).all(): raise ValueError('Backbone mismatch across rosters')
    formal_g=g[g['setting'].isin(SETTINGS)].copy()
    formal_e=roster[roster['setting'].isin(SETTINGS)].copy()
    keys_g=set(map(tuple,formal_g[['target','design']].values.tolist()))
    keys_e=set(map(tuple,formal_e[['target','design']].values.tolist()))
    roster_counts=[]
    for (t,m),sub in formal_e.groupby(['target','setting'],sort=True):
        roster_counts.append({'target':t,'setting':m,'N':len(sub),'backbones':int(sub['backbone'].nunique())})
    failures=[]
    if keys_g!=keys_e: failures.append('Formal roster sets differ')
    for m,count in CONFIG['expected_counts'].items():
        if int((formal_e['setting']==m).sum())!=count: failures.append('Reference count mismatch: '+m)
    for t in TARGETS:
        sets=[set(formal_e.loc[(formal_e['target']==t)&(formal_e['setting']==m),'backbone']) for m in SETTINGS]
        if any(len(s)!=15 for s in sets) or not sets[0]==sets[1]==sets[2]: failures.append('Backbone layout mismatch: '+t)
    for col in CONFIG['score_columns'].values(): formal_g[col]=formal_g[col].map(decimal_score)
    decisions=[]; detection=[]; sensitivity=[]; triggers=[]
    for t in TARGETS:
        for m in ['WN','WD']:
            sub=formal_g[(formal_g['target']==t)&(formal_g['setting']==m)].copy()
            tau=Decimal(CONFIG['thresholds'][m]); scores=sub[CONFIG['score_columns'][m]]
            sub['main']=scores.map(lambda x:x>=tau)
            sub['equal']=scores.map(lambda x:x==tau)
            specs={'strict':lambda x:x>tau,'minus_0.0005':lambda x:x>=tau-Decimal('0.0005'),'plus_0.0005':lambda x:x>=tau+Decimal('0.0005')}
            for name,fn in specs.items(): sub[name]=scores.map(fn)
            n=len(sub); k=int(sub['main'].sum())
            margins=[float(x-tau) for x in scores]
            row={'target':t,'setting':m,'N':n,'K':k,'L':n-k,'equal':int(sub['equal'].sum()),'rate':k/n if n else None}
            detection.append({**row,'margin_min':min(margins) if n else None,'margin_quantiles':np.quantile(margins,[.05,.5,.95],method='linear').tolist() if n else None})
            for name in specs:
                ks=int(sub[name].sum())
                sensitivity.append({'target':t,'setting':m,'variant':name,'N':n,'K':ks,'L':n-ks,'changed':int((sub[name]!=sub['main']).sum()),'zero_misses_changed':(ks==n)!=(k==n)})
            for r in sub.to_dict('records'):
                decisions.append({'target':t,'design':r['design'],'setting':m,'main':bool(r['main']),'equal':bool(r['equal']),**{name:bool(r[name]) for name in specs}})
        cs=formal_g[(formal_g['target']==t)&(formal_g['setting']=='C')]
        for detector in ['WN','WD']:
            k=int(cs[CONFIG['score_columns'][detector]].map(lambda v:v>=Decimal(CONFIG['thresholds'][detector])).sum())
            triggers.append({'target':t,'detector':detector,'K':k,'N':len(cs)})
    for m in ['WN','WD']:
        cells=[r for r in detection if r['setting']==m]
        n=sum(r['N'] for r in cells); k=sum(r['K'] for r in cells)
        scores=formal_g.loc[formal_g['setting']==m,CONFIG['score_columns'][m]]
        margins=[float(v-Decimal(CONFIG['thresholds'][m])) for v in scores]
        detection.append({'target':'ALL','setting':m,'N':n,'K':k,'L':n-k,'equal':sum(r['equal'] for r in cells),'rate':k/n if n else None,'margin_min':min(margins) if n else None,'margin_quantiles':np.quantile(margins,[.05,.5,.95],method='linear').tolist() if n else None})
    canonical={'formal_keys':sorted([list(k) for k in keys_e]),'roster_counts':sorted(roster_counts,key=lambda r:(r['target'],r['setting'])),'detection':[{k:v for k,v in r.items() if not k.startswith('margin')} for r in detection],'sensitivity':sensitivity,'decisions':sorted(decisions,key=lambda r:(r['target'],r['design']))}
    audit={'tables':audits,'join':joinlists,'roster_counts':roster_counts,'gate_G':not failures,'failures':failures,'g_design_count':len(g),'experiment_design_count':len(roster),'experiment_repeat_rows':len(e)}
    return {'canonical':canonical,'audit':audit,'detection':detection,'sensitivity':sensitivity,'C_triggers':triggers},e,roster
