"""Render a status-only Figure 1; never invent scientific counts."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


def main():
    fig,ax=plt.subplots(figsize=(15,7))
    ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    fig.text(.045,.95,'Protein watermark detection: the denominator audit is blocked',fontsize=19,weight='bold')
    fig.text(.045,.902,'Public in-vitro records; authors disclosed selection. No detection rates were recomputed.',fontsize=12)
    boxes=[(.02,.38,.20,.38,'1. Generated candidates','Count unknown\n\nBefore-selection detection:\nnot identifiable\n\nRetention / selection cost:\nnot identifiable'),(.27,.38,.21,.38,'2. Disclosed selection','Structural quality\n+ g-value threshold\n+ ranking\n\nPreviously binding\nbackbones selected'),(.53,.38,.20,.38,'3. Public selected records','Complete design roster:\nNOT VERIFIED\n\nTarget keys fail\nlocked joining rules\n\nGate G: blocked'),(.78,.38,.20,.38,'4. Detection audit','WN: K/N not evaluated\nFixed threshold: 0.545\n\nWD: K/N not evaluated\nFixed threshold: 0.722\n\nM: NOT TESTED')]
    for x,y,w,h,title,body in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.010',facecolor='#f2f5f5' if x<.5 else '#fff0e5',edgecolor='#4c6870' if x<.5 else '#b46432',linewidth=1.4))
        ax.text(x+w/2,y+h-.04,title,ha='center',va='top',fontsize=11,weight='bold')
        ax.text(x+w/2,y+h-.105,body,ha='center',va='top',fontsize=10.5,linespacing=1.3)
    for left,right in [(.226,.266),(.486,.526),(.736,.776)]:
        ax.annotate('',(right,.57),(left,.57),arrowprops={'arrowstyle':'->','lw':1.7,'color':'#4c6870'})
    ax.text(.025,.285,'Why blocked: 270 raw g-value rows use an unregistered target label;\n2 experimental repeat rows have an empty target key. No aliases or keys were inferred.',fontsize=12,color='#96481e')
    ax.text(.025,.17,'The intended estimand is detection conditional on watermarking AND selection.\nFailure to qualify these records is not evidence of missed detections or a false paper claim.',fontsize=11)
    fig.text(.045,.075,'Source: Google DeepMind / SynthIDBio; CC BY 4.0. Original diagnostic figure; no scientific rates calculated.',fontsize=8)
    fig.text(.045,.049,'doi:10.1038/s41586-026-10965-y | upstream commit b2d65a39e0bd3b0bca9e82696bf6f1c306d8d34e',fontsize=7)
    fig.text(.045,.024,'See SOURCES.md for data and licence links. Counts above refer to invalid raw rows, not scientific denominators.',fontsize=8)
    for suffix in ['png','svg']:
        fig.savefig('figures/figure1.'+suffix,dpi=180,bbox_inches='tight',metadata={'Creator':'Independent conditional-denominator audit'})
    plt.close(fig)

if __name__=='__main__': main()
