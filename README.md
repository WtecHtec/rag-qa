# BiYou

[演示视频](https://www.bilibili.com/video/BV1u1un6vEhi/?share_source=copy_web&vd_source=b38d30b9afa4cdb7d6538c4c2978a4c8)

[可参考 rag-web-ui](https://github.com/rag-web-ui/rag-web-ui)

[RAG 教程](https://github.com/GiovanniPasq/agentic-rag-for-dummies)

[文件转md](https://github.com/firecrawl/anydoc)

本地优先的个人知识库问答系统。项目采用前后端分离结构：


- `frontend/`：React、TypeScript、Vite
- `backend/`：FastAPI
- `prototype/`：已确认的 Apple 风格交互原型，仅作为视觉和交互参考

## 目录结构

```text
BiYouQA/
├── frontend/
│   └── src/
│       ├── app/                 # 路由和应用装配
│       ├── components/          # 跨功能 UI 组件
│       ├── features/            # 按产品功能拆分的页面与逻辑
│       └── shared/              # API、配置、样式等共享能力
├── backend/
│   ├── app/
│   │   ├── api/                 # HTTP API 入口
│   │   ├── core/                # 配置、日志等基础能力
│   │   ├── middleware/          # Trace ID 等中间件
│   │   ├── modules/             # 知识库、文档、问答业务模块
│   │   └── providers/           # 可替换的模型、检索、解析实现
│   └── tests/
└── prototype/
```

## 本地启动

### 后端

```bash
cd backend
uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8001
```

健康检查：`http://127.0.0.1:8000/api/v1/health`

也可以在仓库根目录一键启动前后端：

```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env，填写 BIYOU_LLM_API_KEY
./scripts/dev.sh
```

默认前端端口为 `4173`、后端端口为 `8001`。需要改端口时可设置
`BIYOU_FRONTEND_PORT` 和 `BIYOU_BACKEND_PORT`。按 `Ctrl+C` 会同时停止两个服务。

知识库 API：

```text
POST   /api/v1/knowledge-bases
GET    /api/v1/knowledge-bases
GET    /api/v1/knowledge-bases/{knowledge_base_id}
PATCH  /api/v1/knowledge-bases/{knowledge_base_id}
DELETE /api/v1/knowledge-bases/{knowledge_base_id}
```

文档与文本块 API：

```text
POST   /api/v1/knowledge-bases/{knowledge_base_id}/documents?filename=文档.md
GET    /api/v1/knowledge-bases/{knowledge_base_id}/documents
DELETE /api/v1/knowledge-bases/{knowledge_base_id}/documents/{document_id}
POST   /api/v1/knowledge-bases/{knowledge_base_id}/documents/{document_id}/reprocess
GET    /api/v1/knowledge-bases/{knowledge_base_id}/documents/{document_id}/chunks
GET    /api/v1/knowledge-bases/{knowledge_base_id}/documents/{document_id}/chunks/{chunk_id}
PATCH  /api/v1/knowledge-bases/{knowledge_base_id}/documents/{document_id}/chunks/{chunk_id}
DELETE /api/v1/knowledge-bases/{knowledge_base_id}/documents/{document_id}/chunks/{chunk_id}
POST   /api/v1/knowledge-bases/{knowledge_base_id}/search
```

上传接口直接使用原始请求体，文件名放在 `filename` 查询参数中；这种协议可以在前后端流式传输，不需要为大文件额外构造一份 multipart/FormData 副本。当前支持 UTF-8 编码的 `.txt`、`.md`，默认单文件上限为 100 MB。可通过 `BIYOU_DOCUMENT_STORAGE_PATH` 和 `BIYOU_MAX_DOCUMENT_SIZE_BYTES` 调整本地存储目录与大小限制。

默认 Parent / Child 策略：

- Markdown 相邻短章节会先聚合为不超过约 3000 字符的 Parent，标题仍保留在正文中。
- 每个 Parent 至少生成一个 Child；Child 约 500 字符，相邻 Child 默认重叠 50 字符。
- Child 使用 `parent_id` 关联 Parent。后续 Embedding 只处理 Child；检索命中后按 `parent_id` 聚合、去重并回取 Parent 作为 LLM 上下文。
- Child 同时保存相对于 Parent 的 `start_offset` / `end_offset`。引用面板按真实区间标记命中证据，不再用 `indexOf` 猜测重复文本的位置。
- 如果整篇文档本身短于 Child 阈值，单个 Child 与 Parent 内容相同是保证可向量化的必要兜底。

当前默认使用 FastEmbed 加载 `BAAI/bge-small-zh-v1.5` 中文语义模型（512 维、约 90 MB），并把 Child 向量永久保存到本地 LanceDB。模型首次使用时下载到 `data/models`，之后可完全离线推理；LanceDB 数据默认保存在 `data/vectors`。缓存和向量库路径可分别通过 `BIYOU_EMBEDDING_CACHE_PATH`、`BIYOU_VECTOR_DATABASE_PATH` 修改。

索引按 64 个 Child 分批生成，并通过 Child ID 幂等写入 LanceDB；查询使用 LanceDB 原生 cosine 搜索，再按 `parent_id` 聚合回取 Parent。少量向量直接精确搜索，达到 5000 条后自动建立 cosine HNSW-SQ 索引；阈值可通过 `BIYOU_VECTOR_INDEX_THRESHOLD` 调整。

启动时会将旧版 SQLite `child_vectors` 表中模型和维度均匹配的向量一次性迁移到 LanceDB，迁移完成标记保存在 SQLite 的 `app_migrations` 表中。旧特征哈希向量等不兼容数据不会混入语义向量库，对应文档会显示“需要重新处理”，用户重试后将使用当前模型重新生成。删除文档时，关联的 LanceDB Child 向量也会同步删除。

搜索请求示例：

```json
{
  "query": "如何处理大文件上传？",
  "top_k": 5
}
```

响应按 Parent 聚合：`content` 是交给 LLM 的完整父块，`matched_children` 是实际命中的 Child 证据与分数。

会话问答默认通过 LangChain 的 OpenAI-compatible Provider 调用 SiliconFlow
`Pro/zai-org/GLM-4.7`，API Key 只从后端环境变量读取：

```bash
cd backend
cp .env.example .env
# 编辑 .env，填写 BIYOU_LLM_API_KEY
uv run uvicorn app.main:app --reload --port 8000
```

会话 API：

```text
POST   /api/v1/conversations
GET    /api/v1/conversations
DELETE /api/v1/conversations/{conversation_id}
GET    /api/v1/conversations/{conversation_id}/messages
POST   /api/v1/conversations/{conversation_id}/messages/stream
POST   /api/v1/conversations/{conversation_id}/messages/{message_id}/regenerate
PUT    /api/v1/conversations/{conversation_id}/messages/{message_id}/feedback
```

会话不绑定单个知识库，也不要求用户手动选择是否启用 RAG。发送前采用分层意图路由：寒暄、明确记忆命令和短追问先通过高置信规则处理，其余请求交给独立的 LLM 意图分类器，识别普通会话、知识检索、缺少上下文、记忆召回和记忆写入候选。知识型问题优先在全部知识库的 LanceDB Child 向量中检索，再按 `parent_id` 聚合并将完整 Parent 交给 LLM；知识库没有命中时自动回退到通用 LLM。分类器低置信、超时、配置错误或输出格式异常时，会自动回退到原有的 RAG-first 策略，不阻断问答。

检索结果只是候选来源，只有回答正文实际出现对应的 `[n]` 标记后，该文档才会作为引用展示和持久化。

消息接口默认返回最新 30 条并保持正序，可通过 `limit`、`offset` 从最新消息向前分页；前端滚动到会话顶部时会加载更早的消息。回答正文通过 SSE 增量返回，`meta` 提供服务端用户消息与助手消息身份，`done` 直接驱动当前轮次增量并入历史并保留旧消息对象引用；正常完成不再刷新最新消息页，只有中断、协议异常或断线恢复时才调用列表接口校准。会话、消息、实际引用快照和反馈永久保存到 SQLite。日志仅记录稳定事件名、内部 ID、状态码与上游 trace ID，不记录 API Key 和文档正文。

长期记忆与聊天历史、知识库文档分层保存。只有“记住……”或“……，记住这个”这类明确指令会写入 SQLite `memories` 表；相同修改主题会覆盖旧值，并在后续会话的 Prompt 预算内召回。LLM 判断为记忆写入候选、但缺少明确授权时，只会要求用户确认，不会静默修改长期记忆。记忆也不会写入文档 LanceDB 或冒充知识库引用。

当前 `BIYOU_LLM_PROVIDER=openai_compatible`，可以通过 `BIYOU_LLM_BASE_URL`、
`BIYOU_LLM_API_KEY` 和 `BIYOU_LLM_MODEL` 切换兼容 OpenAI Chat Completions 的厂商。
业务层只依赖项目自己的 `LlmProvider` 接口；其他协议厂商后续通过
`LlmProviderFactory` 注册新的 LangChain Builder，不需要修改会话和 RAG 业务。
意图分类默认复用回答模型，但使用温度 0、256 token 和 8 秒超时的独立实例；可通过
`BIYOU_INTENT_MODEL` 指定更轻量的模型，或使用 `BIYOU_INTENT_CLASSIFIER_ENABLED=false`
关闭模型分类并完全回退到规则路由。

后端检查：

```bash
cd backend
uv run ruff check app tests
uv run pytest -q
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://127.0.0.1:4173`，开发服务器会把 `/api` 请求代理到后端的 `8001` 端口。启动脚本会在端口被占用时直接报错，避免 Vite 静默切换端口后误打开其他本地项目。
