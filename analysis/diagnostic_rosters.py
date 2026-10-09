"""Diagnostic outer join of nonempty, registered target keys only.

Rejected rows remain separately inventoried. This does not certify a complete
scientific roster, compute detection, or fulfil Gate I.
"""
import csv
import json
import unicodedata
from collections import Counter,defaultdict
from pathlib import Path
import pandas as pd
from common import CONFIG,EXPERIMENTS,GFILE,save_json,event


def main():
    norm=lambda s:unicodedata.normalize('NFKC',s).strip()
    rosters={}; issues=[]; normalization=[]; invalid=[]
    for kind,paths in [('g',[GFILE]),('experiment',[p for t,p in EXPERIMENTS])]:
        collected=defaultdict(list); tech=defaultdict(list)
        for path in paths:
            with path.open(newline='') as f:
                reader=csv.reader(f); headers=next(reader)
                pos=[i for i,h in enumerate(headers) if h in ['Plate Target ID','Plate_Target_ID']]
                fields=[(h.rstrip() if h else f'index_{i}')+(f'__{i}' if i in pos[1:] else '') for i,h in enumerate(headers)]
                for lineno,cells in enumerate(reader,2):
                    row=dict(zip(fields,cells)); name=row['unique_name' if kind=='g' else 'name']
                    rawtarget=cells[pos[0]]; nt=norm(rawtarget); nd=norm(name).casefold()
                    t=CONFIG['target_aliases'].get(nt.casefold())
                    normalized={'source':str(path.relative_to(Path('data/cache'))),'source_row':lineno,'raw_design':name,'normalized_design':norm(name),'design_key':nd,'raw_target':rawtarget,'normalized_target':nt,'canonical_target':t,'target_column_values':json.dumps([cells[i] for i in pos]),'status':'valid_key' if t and nd else 'blocked_key'}
                    normalization.append(normalized)
                    if not t or not nd:
                        invalid.append(normalized); continue
                    k=(t,nd)
                    m=CONFIG['settings'].get(row['subset_name' if kind=='g' else 'Subset_Name'],'UNKNOWN')
                    b=row['sample_id' if kind=='g' else 'Backbone_ID']
                    metadata={'target':t,'design':nd,'setting':m,'backbone_raw':b}
                    collected[k].append(metadata)
                    rep=norm(row['replicate']) if kind=='experiment' else ''
                    pkey=k+(rep,)
                    # Full scientific content used for duplicate checks only; no sequences exported.
                    fingerprint={field:value for field,value in row.items() if not field.startswith('index_') and field not in ['name','unique_name','Plate Target ID','Plate_Target_ID'] and not field.startswith(('Plate Target ID__','Plate_Target_ID__'))}
                    fingerprint.update(target=t,design=nd)
                    tech[pkey].append((fingerprint,lineno,str(path.relative_to(Path('data/cache')))))
        for k,values in tech.items():
            if len(values)>1:
                issues.append({'scope':kind,'key':list(k),'raw_rows':len(values),'identical':all(v[0]==values[0][0] for v in values),'positions':[{'file':v[2],'row':v[1]} for v in values]})
        roster={}
        for k,rows in collected.items():
            if any(r!=rows[0] for r in rows): issues.append({'scope':kind,'key':list(k),'reason':'metadata_conflict_across_repeats'})
            roster[k]=rows[0]
        rosters[kind]=roster
    left=set(rosters['experiment']);right=set(rosters['g'])
    joined=[]
    for k in sorted(left|right):
        joined.append({'target':k[0],'design':k[1],'join_status':'matched' if k in left&right else ('left_only' if k in left else 'right_only'),'experiment_setting':rosters['experiment'].get(k,{}).get('setting','NA'),'g_setting':rosters['g'].get(k,{}).get('setting','NA'),'experiment_backbone':rosters['experiment'].get(k,{}).get('backbone_raw','NA'),'g_backbone':rosters['g'].get(k,{}).get('backbone_raw','NA')})
    # An independently grouped pandas merge checks the diagnostic key operation.
    pleft=pd.DataFrame(rosters['experiment'].values()).drop_duplicates(['target','design'])
    pright=pd.DataFrame(rosters['g'].values()).drop_duplicates(['target','design'])
    pmerge=pleft.merge(pright,on=['target','design'],how='outer',indicator=True)
    from_frame={(r['target'],r['design']):str(r['_merge']) for r in pmerge.to_dict('records')}
    assert from_frame=={(r['target'],r['design']):('both' if r['join_status']=='matched' else r['join_status']) for r in joined}
    counts=[]
    for t in CONFIG['targets']:
        for m in ['C','WN','WD']:
            selected=[r for r in rosters['experiment'].values() if r['target']==t and r['setting']==m]
            selected_keys={(r['target'],r['design']) for r in selected}
            gkeys={k for k,r in rosters['g'].items() if r['target']==t and r['setting']==m}
            counts.append({'target':t,'setting':m,'valid_experiment_keys':len(selected),'valid_g_keys':len(gkeys),'valid_experiment_backbones':len({r['backbone_raw'] for r in selected}),'left_only':len(selected_keys-right),'right_only':len(gkeys-left),'status':'diagnostic_partial_unqualified'})
    for name,rows in [('diagnostic_outer_join',joined),('key_normalization',normalization)]:
        with Path('artifacts/'+name+'.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    result={'scope':'Valid registered keys only; rejected rows retained in invalid_target_keys.csv; not the full scientific roster','gate_I':'not_completed','diagnostic_join_crosscheck':'exact','join_counts':dict(Counter(r['join_status'] for r in joined)),'formal_cell_diagnostics':counts,'duplicate_keys':issues,'invalid_row_count':len(invalid)}
    save_json('artifacts/diagnostic_rosters.json',result)
    event('static_roster_diagnostics_completed',diagnostic_join_counts=result['join_counts'],invalid_rows=len(invalid),scientific_status='blocked')
    print(json.dumps({'diagnostic_join_counts':result['join_counts'],'duplicate_keys':issues},ensure_ascii=False))

if __name__=='__main__': main()
