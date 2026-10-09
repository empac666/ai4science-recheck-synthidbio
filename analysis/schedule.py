"""Honor the locked absolute secondary windows; waits never exceed 30 seconds."""
import json
import time
from pathlib import Path
from common import elapsed,event,save_json
from run import main


def wait_until(minute):
    while elapsed()<minute:
        remaining=(minute-elapsed())*60
        time.sleep(min(30,max(.05,remaining)))
        print(json.dumps({'status':'waiting_for_preregistered_window','elapsed_minutes':round(elapsed(),3),'next_minute':minute}),flush=True)


def main_schedule():
    wait_until(40)
    if not Path('artifacts/independent_check.json').exists():
        event('checkpoint_40',status='failed'); return
    event('checkpoint_40',status='passed_previously')
    wait_until(60)
    if not all(Path(p).exists() for p in ['artifacts/core.json','artifacts/independent_check.json','figures/figure1.png']):
        event('checkpoint_60',status='secondary_cancelled'); return
    event('checkpoint_60',status='core_previously_ready')
    wait_until(75)
    if not Path('artifacts/bootstrap.json').exists() or json.loads(Path('artifacts/bootstrap.json').read_text())['status']!='complete':
        event('checkpoint_75',status='cutoff_secondary_cancelled'); return
    event('checkpoint_75',status='all_bootstrap_replicates_previously_checked')
    try: main('secondary')
    except Exception as exc:
        event('secondary_stopped',error_type=type(exc).__name__,reason=str(exc)); return
    wait_until(80)
    event('checkpoint_80',status='numeric_analysis_closed')
    try: main('figure2')
    except Exception as exc: event('figure2_omitted',error_type=type(exc).__name__,reason=str(exc))
    event('scheduled_work_finished')

if __name__=='__main__': main_schedule()
