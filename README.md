# SynthIDBio 条件分母复核 / Conditional-denominator audit

本次 R10run 已按锁定规则执行，**M 未检验：Gate G 阻断**。六份必需输入的原始字节哈希全部匹配，但原始靶标标签与冻结连接规则不兼容，且存在空靶标键。没有把这些记录自动改名或补键，也没有输出可用子集的检测率。这不构成发现漏检或否定论文论断的证据。

R10run reached a **blocked, not-tested M verdict**. All six required input hashes match. An unregistered target label and empty experimental target keys prevent the complete roster join under the frozen rules. No detection rate or functional comparison was computed; this is not evidence of missed detections or an incorrect paper claim. The authors disclosed selection.

公开锁定提交：[8be7d0518127bd62b7f967ca75afb425763ab59a](https://github.com/empac666/ai4science-recheck-synthidbio/commit/8be7d0518127bd62b7f967ca75afb425763ab59a)。平台首次主分支创建时间为 `2026-10-09 03:04:51 UTC`，证据及公开文件字节核验见 [登记记录](artifacts/public_lock.json)。锁定协议与可行性文档均保持原字节。

| 文件 / File | 内容 / Contents |
|---|---|
| [REPORT.md](REPORT.md) | 按协议 §8.2 填写的阻断报告 / Frozen-template blocked report |
| [results.json](results.json) | 资格门、未执行项目与缺项状态 / Gates and explicit unavailable results |
| [图 1 / Figure 1](figures/figure1.png) | 筛选分母、连接阻断与未检验状态 / Selection funnel and blocked audit |
| [PREREG.md](PREREG.md)、[feasibility.md](feasibility.md)、[SHA256SUMS](SHA256SUMS) | 不变的锁定方案 / Unmodified locked protocol |
| [DEVIATIONS.md](DEVIATIONS.md) | 表头解释、数据阻断、提前停止 / Implementation interpretation and stopping record |
| [输入清单 / Input manifest](artifacts/input_manifest.json) | 六份原始输入的 URL、大小、哈希、获取时间 |
| [失败清单 / Invalid keys](artifacts/invalid_target_keys.csv) | 272 个阻断原始行，包含两个空键重复 |
| [诊断外连接 / Diagnostic join](artifacts/diagnostic_outer_join.csv) | 仅有效键的定位清单，不能替代完整名册 |
| [原值规整 / Normalization trace](artifacts/key_normalization.csv) | 保留键原值、规整值及原始行号，不含蛋白序列 |
| [代码冻结 / Code freeze](artifacts/code_freeze.json) | 首次实际执行前的代码、配置与依赖哈希 |
| [来源 / Sources](SOURCES.md) | 数据归属、许可与处理变化 |
| [英文草稿](x_post.md)、[中文草稿](x_post_cn.md) | 未发布的传播草稿 / Unpublished drafts |

复现条件：Python 精确版本见 [软件记录](artifacts/software_versions.json)，依赖固定于 [requirements.lock](requirements.lock)。下列命令在仓库根目录执行；复跑结果进入忽略的独立目录，保留本次原始计时与产物。

```sh
python3 -m pip install -r requirements.lock
sha256sum -c SHA256SUMS
python3 -m unittest discover -s tests -v
python3 tools/reproduce_block.py
```

The reproduction command fetches and verifies the same six pinned inputs, starts a new timer in an isolated relative directory, confirms both parser rejections and regenerates the diagnostic join and status-only Figure 1. It does not repair keys or resume scientific aggregation.

代码已实现精确检测比较、两条独立路径、功能解析、固定索引重采样及时间窗保护；实际输入在主名册资格检查处停止，后续科学分支未执行，不能声称已通过真实数据验证。18 行功能表在报告中逐项标“不可估计”；因资格未通过，不生成 270 行明细 CSV。重采样、两个次级敏感性和可选图 2 均未执行。

原始 CSV、上游许可材料与大索引缓存均不入库；不下载参考 PDF，不分发蛋白序列、原图或论文全文。所有结果只在本地 `run/v1` 分支提交，本次未 push。既有第二轮文档处置见 [response2.md](response2.md)。
