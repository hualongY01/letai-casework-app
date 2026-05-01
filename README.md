# Letai Casework App

本项目是勒泰本地事实底座应用的代码仓库。

目标不是复制 NotebookLM，而是实现一个本地运行的 source-grounded factbase：

```text
文件导入
→ chunk / evidence
→ 候选事实
→ 人工逐条确认
→ confirmed FC
→ 只读 Vault 导出
→ Fact Gateway mock
```

## 定位

- SQLite 是唯一事实权威。
- Vault Markdown 是只读投影，不允许人工直接编辑。
- 原始文件导入后复制到 evidence archive，并计算 hash。
- confirmed FC 不允许原地覆盖，只允许创建新版本。
- 下游 subagent 在 v0.1 不正式接入，只通过 Fact Gateway mock 验证事实包。

## v0.1 范围

支持：

- PDF，包括文本 PDF 和扫描 PDF
- PNG / JPG / JPEG / TIFF
- DOCX
- XLSX
- TXT / Markdown
- 本地 OCR
- OCR 页面图片快照和 bbox 高亮审核
- LLM 自动生成 FactCandidate，但只处理 chunk，不处理全量文件
- LLM 调用前本地脱敏身份证号、手机号、银行账号、住址
- LLM 调用日志记录 source、chunk、prompt_version、model、输出
- 候选事实逐条人工确认
- confirmed FC 只读 Vault 导出

暂不做：

- 多用户权限
- 云端部署
- NotebookLM 上传
- Gmail 自动读取
- 完整 subagent 工作流
- 自动正式报告

## 仓库边界

本仓库只保存应用代码、schema、文档和脱敏样例。

不得提交：

- 真实案卷原文
- Office / PDF / 压缩包原件
- `.env`
- API Key / token
- 未脱敏事实卡全量
- 未脱敏邮件正文

## 目录

```text
backend/      Python + FastAPI 后端
frontend/     React + TypeScript 本地审核界面
schemas/      JSON schema
docs/         产品、架构、决策文档
```

## 下一步

1. 实现 confirmed FC 版本更新流程。
2. 用真实但可控材料回测导入、解析、渲染、OCR、候选事实确认流程。
3. 补充导入/审核页面，不再依赖 API 手工调用。
4. 后续视 Node/Vite 兼容性决定是否恢复 React/Vite 构建链路。

## LLM 自动候选事实

未配置 API Key 时，系统仍可完成导入、解析、OCR、索引、人工查看和人工创建候选事实，但不能自动提取候选事实。

配置示例：

```bash
LETAI_LLM_PROVIDER=openai
LETAI_LLM_API_KEY=...
LETAI_LLM_MODEL=...
```

接口：

```text
POST /api/chunks/{chunk_uid}/extract-candidates
GET  /api/llm-call-logs
```

约束：

- LLM 只接收单个 chunk 的脱敏文本。
- 不上传原始文件，不上传 OCR 图像。
- LLM 只能生成 `FactCandidate`，不能生成 confirmed FC。
- 每次调用写入 `LLMCallLog`。

## 后端本地命令

```bash
cd /Users/controller/Documents/Codex/letai-casework-app/backend
python3 -m venv .venv
.venv/bin/python -m pip install .
PYTHONPATH=src .venv/bin/python -c "from letai_factbase.db.session import init_db; init_db()"
PYTHONPATH=src .venv/bin/python -m pytest
PYTHONPATH=src .venv/bin/uvicorn letai_factbase.main:app --reload
```

前端当前有两种入口：

- `frontend/src/`：React + TypeScript 源码，已通过 `tsc` 类型检查。
- `frontend/static/index.html`：无构建依赖的 OCR 审核页，可用本地静态服务器直接访问，当前作为 v0.1 可运行 UI。

```bash
cd /Users/controller/Documents/Codex/letai-casework-app/frontend/static
python3 -m http.server 5173 --bind 127.0.0.1
```

服务启动后访问：

```text
http://127.0.0.1:5173/
```
