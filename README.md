# SynthIDBio 条件分母复核 / Conditional-denominator audit

本仓库保存 R10lock-1 预注册定稿：复核公开、已入选的蛋白质序列水印设计，在冻结阈值下的检出计数与分母是否一致。作者已披露筛选条件；本复核已知论文结论，只覆盖公开验证记录。筛选前检出率与原校准总体假阳性率不由这些记录识别，功能比较仅作探索性描述。

This repository contains the R10lock-1 preregistration for an audit of detection counts and denominators in publicly released, selected protein sequence watermarking designs. The paper discloses the selection process, and its conclusions are already known. The audit cannot identify detection before selection or the false-positive rate in the original calibration population. Functional comparisons are exploratory.

**当前状态：本地文档定稿；未运行实验或科学分析，未 push，尚无公开预注册时间戳。**

**Current status: documents finalized locally; no experiments or scientific analyses run, no push performed, and no public preregistration timestamp established.**

| 文件 / File | 内容 / Contents |
|---|---|
| [PREREG.md](PREREG.md) | 冻结集合、阈值、判定、资格门、停止规则和报告模板 / Protocol and frozen report template |
| [feasibility.md](feasibility.md) | 来源、材料、解析约定及 120 分钟执行预算 / Sources, parsing rules and execution budget |
| [response2.md](response2.md) | 第二轮逐项处置 / Second-round review responses |
| [SHA256SUMS](SHA256SUMS) | 协议与可行性文档的原始字节哈希 / Byte hashes of the protocol and feasibility document |

审查输入与上一轮回复保留为本地对照材料，由 `.gitignore` 明确排除；本轮采纳情况完整记于 `response2.md`。本次锁定包不含分析代码、科学输入或结果。协议表中的上游 README 和 LICENSE 指官方数据仓库文件。

锁定流程：

1. 本地定稿后保存 `PREREG.md`、`feasibility.md` 的 SHA-256 至 `SHA256SUMS`，将四份文档与哈希清单一起提交。以完整提交 SHA 标识本地锁定内容；哈希清单不包含自身，提交 SHA 也不回填到该提交内，避免循环依赖。
2. 未来首次发布前，在仓库根目录运行下方只读核验命令，确认工作树干净且两份文件哈希匹配。记录待发布的完整锁定提交 SHA。当前任务到本地提交为止。
3. **以首次 push 到公开 GitHub 的锁定提交为预注册时间戳锚点。** 未来由发布者将上述提交首次 push 到当时已公开的 GitHub 仓库，并确认该提交及其文件可公开访问。记录公开仓库 URL、完整提交 SHA、首次公开 push 的 UTC 时间和可核验的平台事件或发布回执。本地作者日期、提交日期、文档日期或私有仓库中的提交不替代公开时间。
4. 将公开提交链接、时间及证据保存为后续独立登记记录，并核验公开提交中的文件仍匹配哈希清单。没有完成公开 push 或无法确认公开时间时，状态保持“公开时间戳未确认”。不得为了回填发布记录而 amend 或改写原锁定提交。
5. 公开锁定确认后方可开始未来正式执行；首次科学汇总前另行冻结分析代码、配置与精确依赖版本。执行按协议的资格门及时间上限进行。后续协议修改先用新提交说明原因并公开，再开展受影响分析，保留原提交及其公开记录。

```sh
git status --short
sha256sum -c SHA256SUMS
git rev-parse HEAD
```

Locking workflow (English):

1. Commit the finalized documents with `SHA256SUMS`, which records the byte hashes of `PREREG.md` and `feasibility.md`. Use the full commit SHA to identify the local snapshot. Do not embed the commit's own SHA in its contents.
2. Before future publication, use the read-only commands above to verify a clean working tree, matching hashes and the exact commit to publish. This task ends at the local commit.
3. **The locking commit's first push to a public GitHub repository anchors the preregistration timestamp.** The repository must already be public at that push. Retain the repository URL, full commit SHA, UTC time of the first public push, and verifiable platform-event evidence or a publication receipt. Local Git dates and private commits do not establish public publication time.
4. Verify public access and the committed file hashes, then retain the publication evidence in a subsequent registration record. Until publication and its timing are verified, the public timestamp remains unconfirmed. Preserve the original locking commit without amendment or history rewriting.
5. Begin formal execution only after public locking is confirmed; freeze analysis code, configuration and exact dependency versions before the first scientific aggregation. Publish any protocol amendment with its reason before the affected analysis, retaining the original public record.

论文与固定数据出处 / Paper and pinned data source: [论文 / Paper](https://www.nature.com/articles/s41586-026-10965-y)，[官方数据说明 / Official data documentation](https://github.com/google-deepmind/synthidbio/blob/b2d65a39e0bd3b0bca9e82696bf6f1c306d8d34e/README.md#publication-data)。源数据提交用于固定输入版本，与本仓库未来公开锁定的提交分别记录。 / Record the upstream data commit separately from this repository's public locking commit.
