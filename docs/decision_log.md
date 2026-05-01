# 决策记录

## 2026-04-30

1. 应用定位为本地事实底座，不是 NotebookLM 复制品。
2. v0.1 主流程确定为：文件导入 → chunk/evidence → 候选事实 → 人工逐条确认 → confirmed FC → 只读 Vault 导出。
3. 扫描 PDF / 图片 OCR 纳入 v0.1。
4. OCR 必须本地运行。
5. OCR 结果必须保留页面图片快照和 bbox。
6. v0.1 必须提供 OCR 基础高亮审核界面。
7. v0.1 采用本地 Web 应用形态。
8. 原始文件复制到 evidence archive。
9. 归档文件默认不允许物理删除。
10. 新版 source 创建新 source version，不覆盖旧版本。
11. 人工确认时允许修改候选事实文本。
12. confirmed FC 不允许原地覆盖，只允许创建新版本。
13. 冲突事实不自动裁决。
14. source 权威等级先内置默认规则，后续允许项目级配置。
15. 事实分类 schema 采用通用分类 + 勒泰重整专项标签。
16. v0.1 先做 Fact Gateway mock，不正式接入完整 subagent。
17. LLM 只处理 chunk，敏感信息默认脱敏。

