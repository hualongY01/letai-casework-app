# 勒泰本地事实底座应用 · 产品规格 v0.1

## 一、产品定义

本应用是本地运行的 source-grounded factbase，用于把原始材料转化为可追溯、可校验、可被后续 subagent 调用的事实资产。

应用不定位为普通聊天工具、简单 RAG 问答系统或 NotebookLM 复制品。其核心职责是控制事实入口，防止未经来源验证的信息进入后续工作流。

## 二、核心用户

- 龙飞本人
- Codex / LLM 执行环境
- 后续 subagent 工作流

v0.1 不面向外部律师、财务顾问、招商团队或债权人直接使用。

## 三、输入

### 原始材料

- PDF，包括文本 PDF 和扫描 PDF
- 图片：PNG、JPG、JPEG、TIFF
- DOCX
- XLSX
- TXT / Markdown

### 元数据

- 项目名称
- 材料来源
- 提交人
- 接收日期
- 材料类型
- 保密级别
- 所属业务线

### 人工操作

- 确认候选事实
- 修改候选事实后确认
- 驳回候选事实
- 标记 OCR 错误
- 生成 FR
- 处理冲突事实

## 四、输出

### 数据库输出

- Source
- DocumentChunk
- EvidenceSpan
- OCRPage / OCRBlock
- FactCandidate
- ConfirmedFact
- FactCard
- FactRequest
- ConflictRecord
- AuditLog

### 文件输出

- 只读 Vault Markdown
- 入库报告
- OCR 审核记录
- 冲突事实报告
- Fact Gateway context pack

## 五、主流程

```text
文件导入
→ 复制到 evidence archive
→ 计算 hash
→ 解析文本或本地 OCR
→ 生成 chunk / evidence
→ LLM 提取 FactCandidate
→ 引用和字段校验
→ 人工逐条确认
→ confirmed FC
→ 只读 Vault 导出
→ Fact Gateway mock
```

## 六、已确认规则

1. SQLite 是唯一事实权威。
2. Vault Markdown 只读，不允许人工直接编辑。
3. 原始文件导入后复制到 evidence archive。
4. 归档文件默认不允许物理删除，只允许逻辑状态变更。
5. 新版 source 创建新 version，不覆盖旧版本。
6. 扫描 PDF / 图片必须本地 OCR。
7. OCR 结果必须保留页面图片快照和 bbox。
8. v0.1 必须提供 OCR 基础高亮审核界面。
9. 候选事实必须逐条人工确认后才能成为 confirmed FC。
10. 人工确认时允许修改候选事实文本，但必须保留修改记录。
11. confirmed FC 不允许原地覆盖，只能创建新版本。
12. 冲突事实不自动裁决，由人工选择处理方式。
13. source 权威等级默认内置，后续允许项目级配置。
14. v0.1 采用通用事实分类 + 勒泰重整专项标签。
15. v0.1 先做 Fact Gateway mock，不正式接入完整 subagent。
16. LLM 只处理 chunk，不上传全量文件。
17. 敏感信息默认本地脱敏后再发送给 LLM。
18. OCR 图像默认不上传云端多模态模型。

## 七、v0.1 验收

用 3 到 5 份真实但可控材料回测，至少包括：

- 1 份扫描 PDF
- 1 份可提取文本 PDF 或 DOCX
- 1 份 Excel
- 1 份已有 FC 可对照的材料
- 可选：1 份存在事实冲突或新版/旧版关系的材料

验收链路：

```text
导入 → OCR/解析 → chunk/evidence → candidate → 人工确认 → FC → Vault 导出 → Fact Gateway mock
```

