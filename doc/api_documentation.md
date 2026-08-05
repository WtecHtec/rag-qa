# BiYou 本地知识库问答系统 —— API 接口文档

版本：`v1.0.0`  
基础路径：`/api/v1`  
传输协议：HTTP / HTTPS / SSE (Server-Sent Events)  
数据格式：JSON (UTF-8)

---

## 1. 通用约定与错误响应格式

### 1.1 请求头规范
所有 API 请求建议携带以下 Header：
- `Accept`: `application/json` (SSE 接口为 `text/event-stream`)
- `X-Trace-ID`: *(可选)* 客户端自定义 Trace ID，若不传由后端 `TraceIdMiddleware` 自动生成。

### 1.2 统一错误包结构 (Error Envelope)
发生 4xx / 5xx 错误时，接口返回统一结构的 JSON：
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "指定的知识库不存在或已被删除",
    "trace_id": "tr_9a8b7c6d5e"
  }
}
```

---

## 2. 知识库与文档管理 API (`/knowledge-bases`)

### 2.1 获取知识库列表
- **HTTP 方法**：`GET`
- **路径**：`/api/v1/knowledge-bases`
- **查询参数**：
  - `limit` *(int, 可选, 默认 20)*：每页数量
  - `offset` *(int, 可选, 默认 0)*：偏移量
- **成功响应 (`200 OK`)**：
```json
{
  "items": [
    {
      "id": "kb_123456",
      "name": "产品架构文档",
      "description": "产品需求与系统设计资料",
      "document_count": 8,
      "chunk_count": 136,
      "created_at": "2026-08-04T10:00:00Z",
      "updated_at": "2026-08-04T10:18:00Z"
    }
  ],
  "total": 1
}
```

### 2.2 创建新知识库
- **HTTP 方法**：`POST`
- **路径**：`/api/v1/knowledge-bases`
- **请求体**：
```json
{
  "name": "开发文档",
  "description": "API 约定与后端用例规范"
}
```
- **成功响应 (`201 Created`)**：返回创建的知识库对象。

### 2.3 获取知识库下文档列表
- **HTTP 方法**：`GET`
- **路径**：`/api/v1/knowledge-bases/{kb_id}/documents`
- **成功响应 (`200 OK`)**：
```json
{
  "items": [
    {
      "id": "doc_889900",
      "knowledge_base_id": "kb_123456",
      "filename": "系统架构设计.md",
      "file_size_bytes": 2516582,
      "status": "ready",
      "parent_chunk_count": 24,
      "child_chunk_count": 96,
      "error_message": null,
      "created_at": "2026-08-04T10:42:00Z",
      "updated_at": "2026-08-04T10:42:05Z"
    }
  ],
  "total": 1
}
```

### 2.4 上传导入文档
- **HTTP 方法**：`POST`
- **路径**：`/api/v1/knowledge-bases/{kb_id}/documents`
- **请求类型**：`multipart/form-data`
- **Form 参数**：
  - `file`: 待导入文件二进制流 (支持 `.md`, `.txt`, `.pdf`)
- **成功响应 (`202 Accepted`)**：
```json
{
  "id": "doc_889900",
  "filename": "系统架构设计.md",
  "status": "processing",
  "message": "文档已接收，正在进行文本切片与向量化生成"
}
```

### 2.5 删除文档
- **HTTP 方法**：`DELETE`
- **路径**：`/api/v1/documents/{doc_id}`
- **成功响应 (`204 No Content`)**

---

## 3. 智能问答与流式对话 API (`/conversations`)

### 3.1 获取历史会话列表
- **HTTP 方法**：`GET`
- **路径**：`/api/v1/conversations`
- **查询参数**：
  - `limit` *(int, 可选, 默认 20)*
- **成功响应 (`200 OK`)**：
```json
{
  "items": [
    {
      "id": "conv_998877",
      "title": "为什么选择 Parent / Child Chunk？",
      "created_at": "2026-08-04T10:00:00Z",
      "updated_at": "2026-08-04T10:18:00Z"
    }
  ]
}
```

### 3.2 发起流式问答 (SSE)
- **HTTP 方法**：`POST`
- **路径**：`/api/v1/conversations/{id}/messages/stream`
- **请求体**：
```json
{
  "content": "系统默认选择 Parent / Child Chunk 的主要原因是什么？",
  "knowledge_base_id": "kb_123456"
}
```
- **响应格式**：`text/event-stream`
- **流事件序列**：
  1. `event: metadata` —— 返回消息 ID、改写后的检索 Query 与使用的模型。
  2. `event: delta` —— 增量文本 Token。
  3. `event: citation` —— 召回引用的文档片段出处。
  4. `event: done` —— 生成完毕通知。

### 3.3 重新生成回答 (SSE)
- **HTTP 方法**：`POST`
- **路径**：`/api/v1/conversations/{id}/messages/{message_id}/regenerate`
- **响应格式**：`text/event-stream`
- **功能说明**：重新触发目标助理消息的 RAG 检索与大模型回答生成，并自动将重新生成行为写入审计日志表。

### 3.4 提交回答评价反馈 (点赞/点踩)
- **HTTP 方法**：`POST`
- **路径**：`/api/v1/conversations/{id}/messages/{message_id}/feedback`
- **请求体**：
```json
{
  "rating": "like", 
  "reason": null
}
```
*注：`rating` 可选 `"like"` 或 `"dislike"`。点踩时可附带 `reason` 描述字符串。*
- **成功响应 (`200 OK`)**：
```json
{
  "status": "success",
  "message": "反馈已成功记录"
}
```

---

## 4. 系统诊断与运维 API (`/diagnostics`)

### 4.1 获取系统健康探针
- **HTTP 方法**：`GET`
- **路径**：`/api/v1/diagnostics/health`
- **成功响应 (`200 OK`)**：
```json
{
  "status": "healthy",
  "trace_id": "tr_11223344",
  "components": {
    "database": { "status": "ok", "latency_ms": 2.1 },
    "vector_store": { "status": "ok", "latency_ms": 5.4 },
    "llm_provider": { "status": "ok", "latency_ms": 120.0 }
  }
}
```

### 4.2 获取数据概览指标
- **HTTP 方法**：`GET`
- **路径**：`/api/v1/diagnostics/metrics`
- **成功响应 (`200 OK`)**：
```json
{
  "knowledge_base_count": 3,
  "document_count": 24,
  "vector_count": 136,
  "conversation_count": 12,
  "message_count": 48,
  "storage_size_bytes": 15485760
}
```

### 4.3 查询点赞/点踩与重新生成审计统计
- **HTTP 方法**：`GET`
- **路径**：`/api/v1/diagnostics/feedback-stats`
- **成功响应 (`200 OK`)**：
```json
{
  "total_likes": 32,
  "total_dislikes": 3,
  "like_ratio": 0.914,
  "total_regenerations": 5,
  "dislike_reasons": {
    "回答不准确": 2,
    "答非所问": 1
  }
}
```

### 4.4 查询系统控制台审计日志
- **HTTP 方法**：`GET`
- **路径**：`/api/v1/diagnostics/logs`
- **查询参数**：
  - `level` *(string, 可选)*：`INFO` / `WARNING` / `ERROR`
  - `limit` *(int, 可选, 默认 50)*
- **成功响应 (`200 OK`)**：
```json
{
  "items": [
    {
      "timestamp": "2026-08-04T10:21:08Z",
      "level": "INFO",
      "event": "llm.first_token_received",
      "message": "首 Token 响应成功",
      "trace_id": "tr_8F2A91",
      "extra": { "ttft_ms": 320.5 }
    }
  ]
}
```

---

## 5. 系统配置 API (`/settings`)

### 5.1 获取脱敏系统配置
- **HTTP 方法**：`GET`
- **路径**：`/api/v1/settings`
- **成功响应 (`200 OK`)**：
```json
{
  "llm": {
    "provider": "openai_compatible",
    "base_url": "https://api.siliconflow.cn/v1",
    "model": "deepseek-ai/DeepSeek-V3",
    "api_key_masked": "sk-****abcd"
  },
  "rag": {
    "top_k": 4,
    "similarity_threshold": 0.6
  }
}
```

### 5.2 热更新系统配置
- **HTTP 方法**：`PUT`
- **路径**：`/api/v1/settings`
- **请求体**：
```json
{
  "llm": {
    "provider": "openai_compatible",
    "base_url": "https://api.siliconflow.cn/v1",
    "model": "deepseek-ai/DeepSeek-V3",
    "api_key": "sk-new-secret-key"
  }
}
```
- **成功响应 (`200 OK`)**：返回热加载后的最新配置对象。

### 5.3 测试 LLM 连通性
- **HTTP 方法**：`POST`
- **路径**：`/api/v1/settings/test-llm`
- **请求体**：指定 Provider、Base URL、Model 和 API Key。
- **成功响应 (`200 OK`)**：
```json
{
  "success": true,
  "message": "模型服务连通成功，响应延时 280ms"
}
```
