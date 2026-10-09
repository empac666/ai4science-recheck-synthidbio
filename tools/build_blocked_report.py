"""Fill the frozen report template using only saved audit and status records."""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,'analysis')
from common import CONFIG,save_json,sha,elapsed,event


def table_row(values): return '| '+' | '.join(str(v).replace('\n','；') for v in values)+' |'

def build():
    template=Path('artifacts/report_template.md').read_text()
    inputs=json.loads(Path('artifacts/input_manifest.json').read_text())
    freeze=json.loads(Path('artifacts/code_freeze.json').read_text())
    blocking=json.loads(Path('artifacts/blocking_audit.json').read_text())
    roster=json.loads(Path('artifacts/diagnostic_rosters.json').read_text())
    targets=CONFIG['targets']; settings=['C','WN','WD']; thresholds=CONFIG['functional_thresholds']
    reason='Gate G 阻断：未登记靶标别名及空靶标键；未计算科学指标'
    unavailable='NA（未检验）'
    detection=[{'target':t,'setting':m,'N':None,'K':None,'L':None,'equal_threshold':None,'margin_min':None,'margin_quantiles_05_50_95':None,'status':'not_tested','reason':reason} for t in targets+['ALL'] for m in ['WN','WD']]
    sensitivity=[{'target':t,'setting':m,'variant':v,'N':None,'K':None,'classification_changes':None,'zero_misses_changed':None,'status':'not_executed','reason':reason} for t in targets for m in ['WN','WD'] for v in ['strict','minus_0.0005','plus_0.0005']]
    functional=[{'target':t,'setting':m,'threshold_mol_L':c,'n':None,'a':None,'u':None,'recorded_hit_rate':None,'identification_bounds':None,'state_counts':None,'status':'not_estimable','reason':'Gate B 未取得资格：完整名册与骨架配对被 Gate G 阻断'} for t in targets for m in settings for c in thresholds]
    comparisons=[{'setting':m,'threshold_mol_L':c,'point_difference':None,'identification_bounds':None,'bootstrap_standard_deviation':None,'bootstrap_interval':None,'status':'not_estimable','reason':'完整骨架配对未确认；未启动功能计算'} for m in ['WN','WD'] for c in thresholds]
    gates={'V':{'status':'pass','reason':'六份必需原始输入的长度及 SHA-256 全部匹配；PDF 为参考附件，未重复下载'},'G':{'status':'fail','reason':'270 行 g-value 使用未登记的 SARS-CoV-2；实验表同一 WN 设计的两条重复靶标为空，禁止补键'},'I':{'status':'not_completed','reason':'两条独立原始 CSV 解析路径均拒绝继续，未核验完整键集合、N/K/L 或敏感性；共同拒绝不构成 Gate I 通过'},'B':{'status':'ineligible','reason':'完整名册与 45 骨架配对未确认；实际逐重复单位与功能汇总未执行'},'T':{'status':'pass','reason':'资格阻断后提前收尾；未启动重采样或次级项目，未到任何时间熔断节点，未延长预算'}}
    summary='核心审计未完成；扩展分析未执行；整项复核部分完成（输入与失败审计完成）'
    conclusion='公开记录尚不足以完成原集合的数字复核：冻结的靶标别名与空键规则阻断完整连接，M 未检验，不能判定通过；这不是发现漏检，也不据此否定论文的“100%”论断。筛选前检出率与原校准总体假阳性率仍不可由本集合识别。'
    result={'schema_version':'R10run-1','revision_analysis':False,'repository':'https://github.com/empac666/ai4science-recheck-synthidbio','lock_commit':CONFIG['lock_commit'],'upstream_commit':CONFIG['upstream_commit'],'status':{'core':'not_completed','extension':'not_executed','overall':'partial_completion_blocked'},'M':{'status':'not_tested','passed':None,'qualification_passed':False,'reason':reason,'claim_refuted':False},'conclusion_zh':conclusion,'gates':gates,'inputs':inputs,'code_freeze':freeze,'blocking_diagnostics':{'invalid_target_rows':270,'empty_target_repeat_rows':2,'empty_target_design_raw_name':'PDW_1080','diagnostic_join_counts':roster['join_counts'],'diagnostic_scope':roster['scope'],'source':'artifacts/blocking_audit.json'},'detection':detection,'detection_sensitivity':sensitivity,'C_trigger_proportions':{'status':'not_executed','values':None,'reason':reason},'controls':{'status':'not_executed','binding_values':None,'reason':'仅登记原始类别，未进行结合汇总或核对论文对照结果'},'functional_summary':functional,'functional_comparisons':comparisons,'functional_details':{'path':None,'expected_complete_layout_rows':270,'actual_rows':None,'status':'not_generated','reason':'Gate B 未通过；不以 270 行伪造零计数或可估计性'},'bootstrap':{'status':'not_executed','reason':'资格阻断，基础点估计未生成；未到第 75 分钟','iterations_completed':0,'intervals':None,'index_sha256':None,'seed_configured':2026100901,'rng_consumed':False},'weight_sensitivity':{'status':'not_executed','reason':'资格阻断，重采样未执行'},'repeat_summary_sensitivity':{'status':'not_executed','reason':'资格阻断，重采样未执行'},'figures':{'figure1':{'path':'figures/figure1.png','status':'blocked_state_diagnostic','scientific_funnel_counts_available':False},'figure2':{'path':None,'status':'not_executed','reason':'前置资格、重采样及次级敏感性未完成'}},'time':{'start':json.loads(Path('artifacts/run_clock.json').read_text()),'report_completed_utc':datetime.now(timezone.utc).isoformat(),'report_elapsed_minutes':elapsed(),'checkpoints':{str(n):{'status':'not_applicable','reason':'已因资格阻断提前结束，未到达节点'} for n in [40,60,75,80,90]},'hard_limit_minutes':120},'limitations':['Selected public records only; no pre-selection detection or calibration FPR estimate','No functional equivalence, causal or wet-experiment reproduction claim','Unlabelled KD values would assume mol/L, conditional on protocol assumption; actual functional parsing not run','Scientific computation branches after roster parsing were not validated on these real inputs'],'artifact_links':{'invalid_keys':'artifacts/invalid_target_keys.csv','diagnostic_join':'artifacts/diagnostic_outer_join.csv','normalization':'artifacts/key_normalization.csv','deviations':'DEVIATIONS.md'}}
    # Preserve the locked Markdown framework, replacing only its placeholders/rows.
    out=template
    out=out.replace('核心审计状态：{{状态}}；扩展分析状态：{{状态}}；整项复核状态：{{状态}}。','核心审计状态：未完成（G 阻断）；扩展分析状态：未执行；整项复核状态：部分完成（输入与失败审计完成）。')
    out=out.replace('{{严格按协议 §7 填写}}',conclusion)
    out=out.replace('公开锁定提交链接、完整 SHA、首次公开 push 的 UTC 时间及证据：{{记录}}。','公开锁定提交链接、完整 SHA、首次公开 push 的 UTC 时间及证据：[锁定提交 8be7d0518127bd62b7f967ca75afb425763ab59a](https://github.com/empac666/ai4science-recheck-synthidbio/commit/8be7d0518127bd62b7f967ca75afb425763ab59a)，时间 `2026-10-09 03:04:51 UTC`；[平台活动接口](https://api.github.com/repos/empac666/ai4science-recheck-synthidbio/activity) 中活动 ID `45918352073` 为主分支从空引用创建至该根提交。仓库当前公开、用户确认此前已公开，匿名获取的锁定文件字节一致；[保存的证据](artifacts/public_lock.json) 不以 Git 日期替代发布时间。')
    manifest_text=f"协议 SHA-256 `{freeze['protocol_sha256']}`；可行性 SHA-256 `{freeze['feasibility_sha256']}`；正式获取前复制的模板 SHA-256 `{freeze['template_sha256']}`。代码与配置于 `{freeze['frozen_at_utc']}`（第 {freeze['elapsed_minutes']:.3f} 分钟）冻结，首次真实输入执行前已提交 `57dfa66`；[逐文件代码哈希](artifacts/code_freeze.json)。软件：Python 3.13.5、NumPy 2.5.3、pandas 3.0.6、Matplotlib 3.11.2、Pillow 12.3.0；[精确依赖](requirements.lock)。固定随机配置为 PCG64(2026100901)、10000×3×15、int64、线性分位插值，本次未初始化或消费该生成器、未生成索引文件。获取日期 2026-10-09 UTC；[原始输入 URL 与逐项获取时间](artifacts/input_manifest.json)。7 项合成样例验收通过，覆盖拒绝重复表头冲突/键碰撞、跨靶标同名与技术重复分母、两检测阈值与三个敏感设置、KD 单位/缺失/六种删失符号、功能状态/识别界、配对抽样与熔断；[验收记录](artifacts/acceptance.json)。这不代表被阻断的真实数据科学分支已运行"
    out=out.replace('协议/可行性文档/模板/代码哈希、软件版本、随机数配置及获取日期：{{清单}}。','协议/可行性文档/模板/代码哈希、软件版本、随机数配置及获取日期：'+manifest_text+'。')
    out=out.replace('| {{文件}} | {{哈希}} | {{状态}} |','\n'.join(table_row([r['file'],f"`{r['sha256']}`",f"通过；{r['bytes']:,} 字节"]) for r in inputs['inputs']))
    out=out.replace('参考附件状态与静态阈值出处：{{记录}}。','参考附件状态与静态阈值出处：按协议跳过参考 PDF 重取；存档哈希 `6b9cadfdbc70e54eb711fc670139a1f7f61c4a79cafd965b6e0c2ba651887b04`。沿用补充表 S2 与图 S24/S25 的 WN=0.545、WD=0.722；图 S2 文字将失真设置与 0.649 并列的来源差异仍保留，不改选阈值。补充表 S3 不替换 S2。本次没有执行阈值比较。')
    names={'V':'通过','G':'不通过','I':'未完成','B':'无资格','T':'通过（提前停止）'}
    out=out.replace('| {{检查}} | {{状态}} | {{记录}} |','\n'.join(table_row([g,names[g],v['reason']]) for g,v in gates.items()))
    rows=[]
    for r in roster['formal_cell_diagnostics']:
        rows.append(table_row([f"{r['target']} × {r['setting']}",f"{r['valid_experiment_keys']} 个有效实验键；完整数未核验",f"{r['valid_experiment_backbones']}（仅有效键）",f"{r['left_only']} / {r['right_only']}（仅有效键诊断）",'有效键中无重复；全名册被阻断']))
    out=out.replace('| {{单元}} | {{数值或状态}} | {{数值或状态}} | {{清单}} | {{清单}} |','\n'.join(rows)+'\n\n上述名册行仅定位问题，不能作为完整科学分母。原始 g-value 表 810 行，其中 `SARS-CoV-2` 270 行均不在冻结别名字典；实验表 `PDW_1080` 的两条 WN 重复（CSV 第 543、544 行，含表头）靶标为空。完整保留 [272 行阻断清单](artifacts/invalid_target_keys.csv)、[原值规整表](artifacts/key_normalization.csv) 和 [诊断外连接](artifacts/diagnostic_outer_join.csv)。仅有效键外连接（含对照）为匹配 539、仅实验侧 270、仅 g-value 侧 1；被拒行未删去或补键，另表列示。两种方法对这个诊断连接操作一致，不能替代 Gate I 的完整科学核对。[原失败记录](artifacts/failure_core.json)、[静态核验](artifacts/blocking_audit.json) 与 [名册诊断](artifacts/diagnostic_rosters.json) 均保留。')
    out=out.replace('| {{单元}} | {{值}} | {{值}} | {{值}} | {{值}} | {{值}} | {{状态}} |','\n'.join(table_row([r['target']+' × '+r['setting'],unavailable,unavailable,unavailable,unavailable,unavailable,'未检验：G 阻断']) for r in detection))
    variants={'strict':'g > τ','minus_0.0005':'g ≥ τ−0.0005','plus_0.0005':'g ≥ τ+0.0005'}
    out=out.replace('| {{设置}} | {{值}} | {{值}} | {{状态}} |','\n'.join(table_row([r['target']+' × '+r['setting']+'；'+variants[r['variant']],unavailable,'NA（未执行）','未执行，不能判断是否敏感']) for r in sensitivity))
    out=out.replace('入选非水印组触发数/分母（两个分数分别列出）、阴性与亲本对照状态：{{记录}}。','入选非水印组触发数/分母（两个分数分别列出）、阴性与亲本对照状态：C 的 WN 分数阈值触发数/分母为 NA（未执行），WD 分数阈值触发数/分母为 NA（未执行）。阴性与亲本对照仅登记原始类别，没有做结合汇总，不宣称与论文“未检出结合”一致。C 的这些比例即使可算也不等于校准总体 FPR。')
    out=out.replace('图 1：{{筛选分母与检出漏斗链接；注明作者已披露筛选条件}}。','图 1：[筛选分母与检出漏斗的阻断状态图](figures/figure1.png)（[SVG](figures/figure1.svg)）。作者已披露筛选条件；图中保留生成候选、筛选、公开入选、按阈值检出四阶段，完整分母未核验，WN/WD 的 K/N 均标未执行。它是失败审计图，不是已完成的科学检出漏斗。\n\n![图 1：作者已披露筛选条件；名册连接阻断，M 未检验](figures/figure1.png)')
    unittext='VEGF-A/vegfa_data.csv、PD_L1/pdl1_data.csv、SC2RBD/sc2rbd_data.csv 三文件的无单位 `kd` 均预定按 mol/L、乘数 1 解释；这只是冻结假定，不能按数值猜单位。白名单显式单位换算及缺失/删失分派已用合成样例验收，实际记录因资格阻断未进入功能解析；逐重复单位来源、换算与冲突清单未生成，不能称单位资格通过。所有本可报告的功能数值均以单位假定正确为条件'
    out=out.replace('单位假定及显式换算记录：{{逐文件记录}}。','单位假定及显式换算记录：'+unittext+'。')
    out=out.replace('| {{单元}} | {{值或状态}} | {{值或状态}} | {{值或状态}} | {{值或状态}} | {{界或状态}} | {{清单}} |','\n'.join(table_row([r['target']+' × '+r['setting']+' × '+r['threshold_mol_L'],'NA（未核验）','NA（未核验）','NA（未核验）','不可估计','不可估计','未执行；完整名册/配对被阻断']) for r in functional))
    out=out.replace('{{functional_backbone_details.csv 的相对链接、行数、SHA-256；未生成则填状态与原因}}','未生成 `functional_backbone_details.csv`：Gate B 未通过，完整名册与骨架配对未确认；实际行数与 SHA-256 均不适用，不用 270 行空壳或零计数冒充完成')
    out=out.replace('有限 KD 子集的描述及分母：{{数值或状态}}。','有限 KD 子集的描述及分母：未执行；可定量子集的分母及分布均未核验。')
    out=out.replace('| {{比较}} | {{值或状态}} | {{界或状态}} | {{值或未完成}} | {{记录}} |','\n'.join(table_row([r['setting']+'−C × '+r['threshold_mol_L'],'不可估计','不可估计','未执行；无区间','Gate B 无资格，未启动计算']) for r in comparisons))
    out=out.replace('| {{项目}} | {{结果或未执行}} | {{记录}} |','\n'.join(table_row([name,'未执行',why]) for name,why in [('功能权重敏感性','资格阻断，重采样未执行，不比较微平均与骨架权重'),('重复汇总敏感性','资格阻断，未计算算术或几何均值结果'),('图 2','前置资格、重采样与两个次级敏感性未完成，按优先级取消')]))
    timing=f"正式计时从 `{result['time']['start']['start_utc']}` 开始；首次真实输入尝试在第 8.140 分钟拒绝未知靶标。第 40/60/75/80/90 分钟节点均不适用（已因资格阻断提前结束）；没有启动重采样，不存在部分迭代区间。报告生成于 `{result['time']['report_completed_utc']}`，累计 {result['time']['report_elapsed_minutes']:.3f} 分钟；实际收尾时刻见 [时间记录](artifacts/run_completion.json)，总墙钟严格小于 120 分钟。[执行事件](artifacts/timeline.jsonl)、[失败清单](artifacts/invalid_target_keys.csv)、[偏离与提前停止](DEVIATIONS.md)；未修订原协议或科学参数，未补做后续数值分析"
    out=out.replace('{{逐项记录；提前结束后未到达节点填不适用}}',timing)
    out=out.replace('数据来源、固定提交、许可链接及处理变化：{{记录}}。','数据来源、固定提交、许可链接及处理变化：Google DeepMind / SynthIDBio 项目，[固定版数据说明](https://github.com/google-deepmind/synthidbio/blob/b2d65a39e0bd3b0bca9e82696bf6f1c306d8d34e/README.md#publication-data)，上游提交 `b2d65a39e0bd3b0bca9e82696bf6f1c306d8d34e`；数据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。独立解析、键规整、失败定位和自制图，不分发原始序列、PDF 或论文原图；完整归属与处理变化见 [SOURCES.md](SOURCES.md)。本轮未重新计算分数或复现湿实验，协议与可行性文档保持冻结字节；所有传播稿只是草稿，未发送或发布。')
    assert '{{' not in out and '}}' not in out
    Path('REPORT.md').write_text(out.replace('。。','。'))
    save_json('results.json',result)
    print('Frozen-template report filled; detection rows 8, sensitivity rows 18, functional rows 18, comparisons 4; all unavailable states explicit.')

if __name__=='__main__': build()
