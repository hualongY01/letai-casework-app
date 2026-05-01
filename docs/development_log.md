# 开发日志

## 2026-04-30

### 已完成

- 创建后端 Python 虚拟环境：`backend/.venv`。
- 安装核心后端依赖：FastAPI、SQLModel、Pydantic、PyMuPDF、Pillow 等。
- 安装测试依赖：pytest、httpx。
- 修正 SQLite 初始化逻辑：`init_db()` 建表前导入模型元数据。
- 实现 `POST /api/sources/import`：
  - 接收上传文件。
  - 复制文件到 `storage/evidence_archive/{source_uid}/original/`。
  - 计算 SHA-256 hash。
  - 写入 `Source` 记录。
- 实现 `GET /api/sources`。
- 完成本地 smoke test：
  - 上传 TXT 样例。
  - API 返回 200。
  - SQLite 可查询 source 记录。
  - evidence archive 可看到归档文件。
- 新增自动化测试：
  - `tests/test_contracts.py`
  - `tests/test_source_import.py`
- 实现 TXT/Markdown parser：
  - 新增 `POST /api/sources/{source_uid}/parse`。
  - 新增 `GET /api/chunks`。
  - 新增 `GET /api/evidence`。
  - 已归档文本可生成 `DocumentChunk` 和 `EvidenceSpan`。
- 新增 `tests/test_text_parse.py`。
- 实现可提取文本 PDF parser：
  - 使用 PyMuPDF 按页提取文本。
  - `DocumentChunk` 保留 `page_start/page_end`。
  - `EvidenceSpan.locator_json` 保留页码和 parser 标记。
- 实现 DOCX parser：
  - 提取段落。
  - 提取表格行。
- 实现 XLSX parser：
  - 使用 `openpyxl` 读取 workbook。
  - 逐 sheet/row 生成 chunk。
  - 保留 `sheet_name`、`row_start`、`row_end`。
- 实现页面渲染：
  - 新增 `POST /api/sources/{source_uid}/render-pages`。
  - 新增 `GET /api/ocr-pages`。
  - PDF 渲染为 `storage/evidence_archive/{source_uid}/pages/page-XXXX.png`。
  - 图片文件规范化为 `page-0001.png`。
  - 写入 `OCRPage`，保留 `page_image_path`、`page_image_hash`、`ocr_engine=pending`。
- 安装本地 OCR 引擎：
  - Homebrew `tesseract`
  - Homebrew `tesseract-lang`
  - Python `pytesseract`
- 实现本地 OCR adapter：
  - 新增 `POST /api/ocr-pages/{ocr_page_uid}/run-ocr`。
  - 新增 `GET /api/ocr-blocks`。
  - OCR 结果写入 `OCRBlock`。
  - 每个 OCR block 同步生成 `EvidenceSpan`。
  - `EvidenceSpan.locator_json` 保留 `bbox`、`ocr_engine`、`ocr_confidence`、页码。
- 实现候选事实创建接口：
  - 新增 `POST /api/candidates`。
  - 从已入库 evidence 创建 `FactCandidate`。
  - 校验 evidence 与 source 是否匹配。
- 既有 `POST /api/candidates/confirm` 已完成最小人工确认闭环：
  - `FactCandidate` 可确认成 `FactCard`。
  - 允许修改候选事实文本。
  - 保留 `edited_from_candidate` 与 `edit_reason`。
- 新增测试：
  - `tests/test_pdf_parse.py`
  - `tests/test_docx_parse.py`
  - `tests/test_xlsx_parse.py`
  - `tests/test_page_render.py`
  - `tests/test_ocr_run.py`
  - `tests/test_candidate_flow.py`

### 校验结果

```text
10 passed in 0.84s
```

### 未完成

- 尚未实现 chunk/evidence/page render/OCR 去重和重跑策略。
- 尚未实现 LLM FactCandidate 自动生成。
- 尚未实现 confirmed FC 版本更新流程。
- 尚未接入真实案卷材料。

## 2026-05-01 · 幂等与 force 重跑

### 已完成

- `POST /api/sources/{source_uid}/parse` 增加幂等控制：
  - 默认重复调用时返回已有 `DocumentChunk`，不重复生成 chunk/evidence。
  - 支持 `force=true`。
  - 若旧 evidence 已被 `FactCandidate` 或 `FactCard` 引用，`force=true` 返回 409。
- `POST /api/sources/{source_uid}/render-pages` 增加幂等控制：
  - 默认重复调用时返回已有 `OCRPage`，不重复渲染页面。
  - 支持 `force=true`。
  - 若旧 OCR evidence 已被候选事实或 FC 引用，拒绝重跑。
- `POST /api/ocr-pages/{ocr_page_uid}/run-ocr` 增加幂等控制：
  - 默认重复调用时返回已有 `OCRBlock`，不重复生成 OCR block/evidence。
  - 支持 `force=true`。
  - 若旧 OCR evidence 已被候选事实或 FC 引用，拒绝重跑。
- 新增测试：
  - `tests/test_idempotency.py`
  - 覆盖 parse、render-pages、run-ocr 默认幂等。
  - 覆盖 parse force 重建。
  - 覆盖 evidence 已有候选事实依赖时 force 拒绝。

### 校验结果

```text
backend: 15 passed
frontend: tsc --noEmit passed
```

### 未完成

- 尚未实现 LLM FactCandidate 自动生成。
- 尚未实现 confirmed FC 版本更新流程。
- 尚未接入真实案卷材料。

## 2026-05-01 · LLM 自动候选事实提取

### 已完成

- 新增本地敏感信息脱敏层：
  - 身份证号 → `[REDACTED_ID_NUMBER]`
  - 手机号 → `[REDACTED_PHONE]`
  - 12-30 位银行账号/长数字账号 → `[REDACTED_BANK_ACCOUNT]`
  - `住址/家庭住址/联系地址/通讯地址` 标签后的地址 → `[REDACTED_ADDRESS]`
- 新增 `LLMCallLog` 表：
  - 记录 `source_uid`
  - 记录 `chunk_uid`
  - 记录 `prompt_version`
  - 记录 `model`
  - 记录脱敏后的输入文本
  - 记录 LLM 输出 JSON
  - 记录调用状态与错误信息
- 新增 LLM 候选事实提取服务：
  - 只处理单个 `DocumentChunk`。
  - 不上传全量文件。
  - 不上传 OCR 图像。
  - prompt 版本为 `fact_candidate_extraction_v0.1`。
  - 输出只能创建 `FactCandidate`，不能创建 confirmed FC。
  - 同一 evidence、同一 proposed_fact_text、同一 model、同一 prompt_version 的候选事实会跳过重复创建。
- 新增 API：
  - `POST /api/chunks/{chunk_uid}/extract-candidates`
  - `GET /api/llm-call-logs`
- 未配置 `LETAI_LLM_API_KEY` 或 `LETAI_LLM_MODEL` 时，自动提取接口返回 409；导入、解析、OCR、人工审核仍可使用。
- 静态前端 `frontend/static/index.html` 新增：
  - chunk 列表
  - “LLM 提取候选事实”按钮
  - 候选事实列表
  - LLM 调用日志摘要
- 新增测试：
  - `tests/test_llm_extraction.py`
  - 覆盖敏感信息脱敏。
  - 覆盖 LLM 候选事实创建、调用日志、重复候选跳过。
  - 覆盖未配置 API Key 时自动提取接口返回 409。

### 校验结果

```text
backend: 18 passed
frontend: tsc --noEmit passed
```

### 未完成

- 尚未实现 confirmed FC 版本更新流程。
- 尚未接入真实案卷材料。
- 静态前端仍缺文件导入与 parse/render 控制面板。

## 2026-05-01 · OCR 审核 UI（较早阶段记录）

### 已完成

- 后端新增页面图片读取接口：
  - `GET /api/ocr-pages/{ocr_page_uid}/image`
  - 返回 OCR page PNG，供前端高亮审核使用。
- 后端启用本地开发 CORS：
  - `http://localhost:5173`
  - `http://127.0.0.1:5173`
- 前端 React/TypeScript 源码接入真实 API：
  - `/api/ocr-pages`
  - `/api/ocr-blocks`
  - `/api/evidence`
  - `/api/ocr-pages/{ocr_page_uid}/image`
  - `/api/ocr-pages/{ocr_page_uid}/run-ocr`
  - `/api/candidates`
- 前端实现真实 OCR 页面图像 + bbox overlay + block 列表 + 创建候选事实按钮。
- 新增 `frontend/static/index.html`：
  - 无构建依赖。
  - 直接调用 FastAPI。
  - 当前作为 v0.1 可运行 OCR 审核界面。
- 前端 `npm run build` 调整为 TypeScript 类型检查。

### 校验结果

```text
backend: 10 passed
frontend: tsc --noEmit passed
```

### 说明

- Vite build 在当前 Node 25 环境下会挂起，已暂时移出 v0.1 运行链路。
- v0.1 当前用 `frontend/static/index.html` 作为可运行前端。

### 未完成

- 尚未实现 confirmed FC 版本更新流程。
- 尚未接入真实案卷材料。
