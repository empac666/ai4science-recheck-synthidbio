"""Independent standard-library audit: rereads raw CSV, sets and Counter only."""
import csv
import re
import unicodedata
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from common import CONFIG, TARGETS, SETTINGS, EXPERIMENTS, GFILE


def clean(s): return unicodedata.normalize('NFKC',s).strip()

def read_raw(path, experiment):
    with path.open(newline='') as f:
        reader=csv.reader(f)
        header=next(reader)
        indices=[i for i,x in enumerate(header) if x in ['Plate Target ID','Plate_Target_ID']]
        if not indices: raise ValueError('Target header absent')
        for row in reader:
            if len(row)!=len(header): raise ValueError('Ragged CSV')
            if len({clean(row[i]) for i in indices})!=1: raise ValueError('Target header conflict')
    names=[]
    for i,h in enumerate(header):
        if i in indices: names.append('target_raw' if i==indices[0] else f'target_extra_{i}')
        elif not h: names.append(f'index_only_{i}')
        else: names.append(h.rstrip())
    unique={}; fingerprints={}; duplicates=[]
    with path.open(newline='') as f:
        reader=csv.DictReader(f,fieldnames=names); next(reader)
        for position,row in enumerate(reader,2):
            target_key=clean(row['target_raw']).casefold()
            if target_key not in CONFIG['target_aliases']: raise ValueError('Unrecognized target')
            t=CONFIG['target_aliases'][target_key]
            name_field='name' if experiment else 'unique_name'
            k=clean(row[name_field]).casefold()
            if not k: raise ValueError('Blank name')
            label=row['Subset_Name' if experiment else 'subset_name']
            if label not in CONFIG['settings']: raise ValueError('Unrecognized category')
            m=CONFIG['settings'][label]
            rawbone=clean(row['Backbone_ID' if experiment else 'sample_id'])
            if not rawbone and m not in SETTINGS: b=None
            else:
                match=re.fullmatch('Backbone ([0-9]+)',rawbone)
                if match is None: raise ValueError('Invalid backbone field')
                b=int(match.group(1))
            primary=(t,k)
            if experiment:
                rep=clean(row['replicate'])
                if not rep: raise ValueError('Blank replicate')
                primary+=(rep,)
            fp={field:value for field,value in row.items() if not field.startswith(('index_only_','target_extra_')) and field not in [name_field,'target_raw']}
            if experiment: fp['replicate']=rep
            fp.update(target=t,design=k)
            if primary in unique:
                if fp!=fingerprints[primary]: raise ValueError('Nonidentical duplicate key')
                duplicates.append({'key':list(primary),'source_row':position})
                continue
            fingerprints[primary]=fp
            unique[primary]={'target':t,'design':k,'setting':m,'backbone':b,'raw':row}
    return unique,duplicates


def number(s):
    try: x=Decimal(s)
    except InvalidOperation: raise ValueError('Bad score syntax')
    if not x.is_finite() or x<0 or x>1: raise ValueError('Score outside [0,1]')
    return x


def run():
    gs,gd=read_raw(GFILE,False)
    eroster={}; repeat_keys=set()
    for expected,path in EXPERIMENTS:
        reps,duplicates=read_raw(path,True)
        for p,r in reps.items():
            if r['target']!=expected: raise ValueError('Wrong target file')
            if p in repeat_keys: raise ValueError('Repeat key duplicated across files')
            repeat_keys.add(p)
            k=p[:2]
            meta=(r['setting'],r['backbone'])
            if k in eroster and eroster[k]!=meta: raise ValueError('Metadata changes across repeats')
            eroster[k]=meta
    gkeys={k for k,r in gs.items() if r['setting'] in SETTINGS}
    ekeys={k for k,meta in eroster.items() if meta[0] in SETTINGS}
    if gkeys!=ekeys: raise ValueError('Formal outer join mismatch')
    for k in gkeys:
        if eroster[k]!=(gs[k]['setting'],gs[k]['backbone']): raise ValueError('Roster metadata mismatch')
    counts=Counter(); bones=defaultdict(set)
    for (t,k),(m,b) in eroster.items():
        if m in SETTINGS: counts[(t,m)]+=1; bones[(t,m)].add(b)
    roster_counts=[{'target':t,'setting':m,'N':n,'backbones':len(bones[(t,m)])} for (t,m),n in sorted(counts.items())]
    results=Counter(); decision=[]
    for (t,k) in sorted(gkeys):
        r=gs[(t,k)]; m=r['setting']
        # C's two fields are validated independently too.
        for col in CONFIG['score_columns'].values(): number(r['raw'][col])
        if m not in ['WN','WD']: continue
        x=number(r['raw'][CONFIG['score_columns'][m]]); tau=Decimal(CONFIG['thresholds'][m])
        flags={'main':x>=tau,'equal':x==tau,'strict':x>tau,'minus_0.0005':x>=tau-Decimal('0.0005'),'plus_0.0005':x>=tau+Decimal('0.0005')}
        results[(t,m,'N')]+=1
        for flag,value in flags.items(): results[(t,m,flag)]+=int(value)
        for flag in ['strict','minus_0.0005','plus_0.0005']: results[(t,m,flag+'_changed')]+=int(flags[flag]!=flags['main'])
        decision.append({'target':t,'design':k,'setting':m,**flags})
    detection=[]; sensitivity=[]
    for t in TARGETS:
        for m in ['WN','WD']:
            n=results[(t,m,'N')]; k=results[(t,m,'main')]
            detection.append({'target':t,'setting':m,'N':n,'K':k,'L':n-k,'equal':results[(t,m,'equal')],'rate':k/n if n else None})
            for variant in ['strict','minus_0.0005','plus_0.0005']:
                kk=results[(t,m,variant)]
                sensitivity.append({'target':t,'setting':m,'variant':variant,'N':n,'K':kk,'L':n-kk,'changed':results[(t,m,variant+'_changed')],'zero_misses_changed':(kk==n)!=(k==n)})
    for m in ['WN','WD']:
        n=sum(results[(t,m,'N')] for t in TARGETS); k=sum(results[(t,m,'main')] for t in TARGETS)
        detection.append({'target':'ALL','setting':m,'N':n,'K':k,'L':n-k,'equal':sum(results[(t,m,'equal')] for t in TARGETS),'rate':k/n if n else None})
    return {'formal_keys':sorted([list(k) for k in ekeys]),'roster_counts':roster_counts,'detection':detection,'sensitivity':sensitivity,'decisions':decision}
