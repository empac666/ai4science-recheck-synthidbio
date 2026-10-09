"""Static failure audit only: no scores, detection rates or function aggregation."""
import csv
import json
import unicodedata
from collections import Counter
from pathlib import Path
import pandas as pd
from common import CONFIG,EXPERIMENTS,GFILE,save_json,sha,event,elapsed


def inspect_csv(path,experiment):
    with path.open(newline='') as f:
        reader=csv.reader(f); header=next(reader); rows=list(reader)
    positions=[i for i,h in enumerate(header) if h in ['Plate Target ID','Plate_Target_ID']]
    name_position=header.index('name' if experiment else 'unique_name')
    setting_position=header.index('Subset_Name' if experiment else 'subset_name')
    normalized=lambda s:unicodedata.normalize('NFKC',s).strip()
    issues=[]; rawlabels=Counter()
    for lineno,row in enumerate(rows,2):
        raw=row[positions[0]]; value=normalized(raw); rawlabels[raw]+=1
        reason='empty_target_key' if not value else ('target_not_in_frozen_alias_dictionary' if value.casefold() not in CONFIG['target_aliases'] else None)
        if len({normalized(row[i]) for i in positions})!=1: reason='duplicate_target_header_conflict'
        if reason:
            issues.append({'file':str(path.relative_to(Path('data/cache'))),'source_row':lineno,'raw_target':raw,'normalized_target':value,'raw_design':row[name_position],'raw_setting':row[setting_position],'reason':reason})
    # Independent pandas read corroborates raw target frequencies, not scientific outcomes.
    df=pd.read_csv(path,header=0,names=[str(i) for i in range(len(header))],dtype=str,keep_default_na=False)
    raw_counts={str(k):int(v) for k,v in df.groupby(str(positions[0]),dropna=False).size().items()}
    assert dict(rawlabels)==raw_counts
    return {'file':str(path.relative_to(Path('data/cache'))),'raw_rows':len(rows),'target_columns':[{'position':i,'header':header[i]} for i in positions],'raw_target_counts':dict(sorted(rawlabels.items())),'target_frequency_crosscheck':'exact','issues':issues,'duplicate_target_columns_agree':all(len({normalized(row[i]) for i in positions})==1 for row in rows)}


def main():
    import path_b
    try:
        path_b.run()
        b={'status':'unexpected_success'}
    except ValueError as exc:
        b={'status':'blocked','error_type':type(exc).__name__,'reason':str(exc)}
    records=[inspect_csv(GFILE,False)]+[inspect_csv(p,True) for t,p in EXPERIMENTS]
    issues=[x for r in records for x in r['issues']]
    result={'purpose':'static_source_and_key_failure_audit_only','scientific_aggregation_performed':False,'path_a_failure':json.loads(Path('artifacts/failure_core.json').read_text()),'path_b_attempt':b,'files':records,'issue_count_by_reason':dict(Counter(x['reason'] for x in issues)),'gate_I':'not_completed','gate_I_note':'Both independent parsers reject the original inputs. Agreement on rejection does not satisfy the preregistered scientific Gate I.','code_sha256':sha('analysis/diagnose_block.py')}
    save_json('artifacts/blocking_audit.json',result)
    fields=['file','source_row','raw_target','normalized_target','raw_design','raw_setting','reason']
    with Path('artifacts/invalid_target_keys.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(issues)
    event('static_blocking_audit_completed',issues=result['issue_count_by_reason'],path_b_status=b['status'],no_scientific_summary=True)
    print(json.dumps({k:result[k] for k in ['issue_count_by_reason','path_b_attempt','gate_I']},ensure_ascii=False))

if __name__=='__main__': main()
