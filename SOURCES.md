# 数据来源与处理

- 论文：*Function-preserving watermarking of AI-generated proteins*，DOI [10.1038/s41586-026-10965-y](https://www.nature.com/articles/s41586-026-10965-y)。本次引用既有阈值与设计说明，不分发论文全文、补充 PDF 或原图。
- 原始数据：Google DeepMind / SynthIDBio 项目，[固定提交的数据说明](https://github.com/google-deepmind/synthidbio/blob/b2d65a39e0bd3b0bca9e82696bf6f1c306d8d34e/README.md#publication-data)，完整提交 `b2d65a39e0bd3b0bca9e82696bf6f1c306d8d34e`。
- 数据许可：[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)，依据上游 [许可说明](https://github.com/google-deepmind/synthidbio/blob/b2d65a39e0bd3b0bca9e82696bf6f1c306d8d34e/README.md#licensing--disclaimer) 与 Publication Data 两段合读。数据目录拼写遗漏沿用协议记录，不扩展到其他材料。软件许可为 Apache-2.0，与数据许可分开。
- 处理变化：本仓独立编写表格解析与计数程序，规整连接键、合并技术重复、按冻结阈值比较，汇总功能记录并自制图表；保留原值到规范键的追踪表。未重新计算检测分数、生成蛋白序列或进行实验。归属通过来源链接追溯，不暗示上游项目背书。
- 限定：作者已披露筛选条件；图 1 和图 2 只对应公开入选记录。两种主阈值来自补充表 S2 与图 S24/S25；图 S2 文字中的阈值差异按协议披露，未用于选择结果。没有重新下载参考附件。
- 原始输入 URL、日期、长度与原始字节 SHA-256 见 [输入清单](artifacts/input_manifest.json)。原始序列只存在于被忽略的缓存中，不进入交付提交。
