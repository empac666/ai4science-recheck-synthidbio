"""Original, single-panel audit figures from frozen aggregates."""
import json
import textwrap
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from common import CONFIG,TARGETS,deadline,elapsed,event

SOURCE='Source: Google DeepMind / SynthIDBio; CC BY 4.0. Independent aggregation; technical repeats merged.'
LINK='doi:10.1038/s41586-026-10965-y | data commit b2d65a39e0bd3b0bca9e82696bf6f1c306d8d34e'

def save(fig,name):
    for suffix in ['png','svg']:
        fig.savefig(f'figures/{name}.{suffix}',dpi=180,bbox_inches='tight',metadata={'Creator':'Independent conditional-denominator audit'})
    plt.close(fig)

def figure1(core):
    totals={r['setting']:r for r in core['detection'] if r['target']=='ALL'}
    cells={m:[r for r in core['detection'] if r['target']!='ALL' and r['setting']==m] for m in ['WN','WD']}
    fig,ax=plt.subplots(figsize=(15,7.2)); ax.set(xlim=(0,1),ylim=(0,1)); ax.axis('off')
    fig.text(.05,.95,'Protein watermark detection: which denominator?',fontsize=20,weight='bold')
    fig.text(.05,.905,'Public, selected three-target records. The paper discloses the selection conditions.',fontsize=12)
    boxes=[(.02,.38,.20,.39,'Generated candidates','Count unobserved\n\nBefore-selection detection:\nnot identifiable\n\nRetention and selection cost:\nnot identifiable'),(.27,.38,.21,.39,'Disclosed selection','Structural quality\n+ g-value threshold\n+ ranking\n\nPreviously binding\nbackbones selected'),(.53,.38,.20,.39,'Public selected designs','C: 222\nWN: 267\nWD: 267\n\n3 targets × 15 backbones\nTechnical repeats merged'),(.78,.38,.20,.39,'Detected at fixed thresholds',f"WN: {totals['WN']['K']}/{totals['WN']['N']}\ng ≥ 0.545\n\nWD: {totals['WD']['K']}/{totals['WD']['N']}\ng ≥ 0.722")]
    for x,y,w,h,title,body in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.012',facecolor='#edf4f7',edgecolor='#315c6d',linewidth=1.5))
        ax.text(x+w/2,y+h-.045,title,ha='center',va='top',fontsize=10.5,weight='bold',wrap=True)
        ax.text(x+w/2,y+h-.11,body,ha='center',va='top',fontsize=11,linespacing=1.35)
    for left,right in [(0.225,.265),(.485,.525),(.735,.775)]: ax.annotate('',(right,.575),(left,.575),arrowprops={'arrowstyle':'->','lw':1.8,'color':'#315c6d'})
    for i,m in enumerate(['WN','WD']):
        text=m+': '+ '   |   '.join(f"{r['target']} {r['K']}/{r['N']}" for r in cells[m])
        ax.text(.03,.29-i*.065,text,fontsize=12)
    ax.text(.03,.115,'The observed proportion is conditional on watermarking AND selection.\nIt does not estimate detection before selection or the calibration-population false-positive rate.',fontsize=11,color='#8b3b20')
    fig.text(.05,.065,SOURCE,fontsize=8)
    fig.text(.05,.039,LINK,fontsize=7)
    fig.text(.05,.015,'Data and licence links: see SOURCES.md. No detector scores or wet experiments were regenerated.',fontsize=7)
    save(fig,'figure1')
    event('figure1_completed')

def figure2(base,boot):
    if not 80<=elapsed()<90: raise RuntimeError('Figure 2 window is minutes 80–90')
    if not all(Path(p).exists() for p in ['artifacts/weight_sensitivity.json','artifacts/repeat_sensitivity.json','figures/figure1.png']): raise RuntimeError('Figure 2 prerequisites absent')
    fig,ax=plt.subplots(figsize=(11,6))
    labels=[]
    for i,r in enumerate(base['comparisons']):
        b=next(x for x in boot['comparisons'] if (x['setting'],x['threshold_mol_L'])==(r['setting'],r['threshold_mol_L']))
        lo,hi=r['identification_bounds']; p=r['point_difference']; ci=b['percentile_interval']
        ax.plot([lo,hi],[i+.1,i+.1],color='#c16b26',lw=6,alpha=.65,label='Unknown-KD identification bounds' if i==0 else None)
        ax.plot(ci,[i-.1,i-.1],color='#315c6d',lw=2,label='Exploratory 95% bootstrap percentile interval' if i==0 else None)
        ax.scatter([p],[i],s=45,color='#173846',zorder=5,label='Backbone-equal recorded-hit difference' if i==0 else None)
        labels.append(f"{r['setting']} − C; KD ≤ {r['threshold_mol_L']} mol/L")
    ax.axvline(0,color='gray',lw=1,ls='--'); ax.set_yticks(range(4),labels); ax.invert_yaxis()
    ax.set_xlabel('Recorded quantitative-hit proportion difference (watermarked minus C)')
    ax.set_title('Selected-backbone functional descriptions',loc='left',weight='bold',pad=20)
    ax.legend(loc='upper center',bbox_to_anchor=(.5,-.2),fontsize=8,frameon=False)
    fig.subplots_adjust(left=.29,bottom=.34,top=.82)
    fig.text(.03,.89,'Authors disclose selection. Unlabelled KD values assume mol/L; temperature differs for WN and C.',fontsize=9)
    fig.text(.03,.095,'Identification bounds are not confidence intervals. Bootstrap assumes exchangeable selected backbones;\npointwise intervals do not establish equivalence, causality or population performance.',fontsize=9)
    fig.text(.03,.045,SOURCE,fontsize=7)
    fig.text(.03,.019,LINK+' | See SOURCES.md for links.',fontsize=6)
    deadline('figure2'); save(fig,'figure2'); event('figure2_completed')
