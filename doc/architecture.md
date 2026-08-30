# BiYou 本地知识库问答系统 —— 架构设计文档

本文档详细说明 BiYou 本地 Agentic RAG 问答系统的**服务端总体分层架构**与**基于 LangGraph 的 Agentic RAG 双层图状态机架构**。

---

## 1. 服务端总体 DDD 分层架构图

服务端严格遵循 **DDD（领域驱动设计）** 原则，将核心业务规则与外部数据库、模型厂商、Web 框架彻底解耦，依赖方向自外向内单向依赖：

```mermaid
flowchart TB
    subgraph Presentation_Layer ["1. 表现层 (Presentation Layer - API & SSE)"]
        API_KB["知识库路由<br/>(/api/v1/knowledge-bases)"]
        API_Doc["文档路由<br/>(/api/v1/documents)"]
        API_Chat["会话流式路由 (SSE)<br/>(/api/v1/conversations/.../stream)"]
        API_Settings["设置路由<br/>(/api/v1/settings)"]
        API_Diag["诊断探针路由<br/>(/api/v1/diagnostics)"]
    end

    subgraph Application_Layer ["2. 应用服务层 (Application Layer - Use Cases)"]
        Chat_Svc["ChatService<br/>(LangGraph 编排/流式驱动/事务持久化)"]
        Doc_Svc["DocumentService<br/>(两阶段切分/异步向量化管道)"]
        KB_Svc["KnowledgeBaseService<br/>(知识库生命周期/跨模块统计聚合)"]
        Ret_Svc["RetrievalService<br/>(子块初筛搜索/父块大上下文回取)"]
        Mem_Svc["MemoryService<br/>(显式长期记忆提取/去重更新)"]
        Set_Svc["SettingsService<br/>(模型热加载/运行期参数持久化)"]
        Diag_Svc["DiagnosticsService<br/>(链路探针/反馈审计统计)"]
    end

    subgraph Domain_Layer ["3. 核心领域层 (Domain Layer - Pure Business & Ports)"]
        subgraph Chat_Domain ["Chat 领域"]
            Chat_State["领域状态机<br/>(ConversationState / AgentSubGraphState)"]
            Chat_Nodes["领域节点与路由<br/>(summarize, rewrite, orchestrator, aggregate)"]
            Chat_Tools["检索领域工具<br/>(create_retrieval_tools)"]
            Chat_Port["端口协议<br/>(ConversationRepository / LlmProvider)"]
        end
        subgraph Doc_Domain ["Documents 领域"]
            Doc_Models["文档实体与分块<br/>(Document / TextChunk / ChunkKind)"]
            Doc_Port["端口协议<br/>(DocumentRepository / DocumentStorage)"]
        end
        subgraph Ret_Domain ["Retrieval 领域"]
            Ret_Models["检索模型与命中<br/>(ChildChunkItem / ParentChunkDetail)"]
            Ret_Port["端口协议<br/>(VectorStore / EmbeddingProvider)"]
        end
        subgraph KB_Domain ["KnowledgeBase 领域"]
            KB_Models["知识库实体<br/>(KnowledgeBase / Metrics)"]
            KB_Port["端口协议<br/>(KnowledgeBaseRepository)"]
        end
        subgraph Mem_Domain ["Memory 领域"]
            Mem_Models["记忆实体与提取纯函数<br/>(Memory / extract_explicit_memory)"]
            Mem_Port["端口协议<br/>(MemoryRepository)"]
        end
    end

    subgraph Infrastructure_Layer ["4. 基础设施层 (Infrastructure Layer - Adapters & Storage)"]
        Repo_SQLite["SQLite Repositories<br/>(SqliteConversationRepo / SqliteDocRepo / SqliteKBRepo)"]
        Store_LanceDB["LanceDB Vector Store<br/>(本地高性能嵌入式向量索引)"]
        Storage_Disk["Local Document Storage<br/>(本地磁盘文件存储)"]
        Migration_Tool["Migration Tools<br/>(数据库与向量迁移工具)"]
    end

    subgraph Providers_Layer ["5. 外部能力适配层 (Providers Layer)"]
        LLM_Adapter["LangChain ChatModel Provider<br/>(SiliconFlow / DeepSeek / Ollama / OpenAI)"]
        Embed_Adapter["FastEmbed Provider<br/>(BAAI/bge-small-zh-v1.5)"]
        Chunker_Adapter["ParentChildTextChunker<br/>(Markdown 标题树感知 + 小块合并切分)"]
    end

    Presentation_Layer --> Application_Layer
    Application_Layer --> Domain_Layer
    Application_Layer --> Providers_Layer
    Infrastructure_Layer -.->|实现端口协议| Domain_Layer
    Providers_Layer -.->|实现能力协议| Domain_Layer
```

---

## 2. LLM Chat 的 Agentic RAG 双层图状态机架构图

BiYou 借鉴并融合了 `agentic-rag-for-dummies` 的核心思想，使用 **LangGraph SDK** 构筑了具备**意图拆解重写、两阶段多步工具调用研究循环、动态上下文压缩、超预算降级兜底及最终多路归纳**的双层状态机。

```mermaid
flowchart TD
    %% 主图流转
    subgraph Main_Graph ["主图：ConversationState (会话主生命周期)"]
        Start([用户提问进入]) --> Node_Summ["1. summarize_history<br/>(滑动窗口超限历史自动摘要)"]
        Node_Summ --> Node_Rewrite["2. rewrite_query<br/>(大模型结构化输出 QueryAnalysis)"]
        
        Node_Rewrite --> Cond_Clear{"问题表意是否清晰？<br/>(is_clear)"}
        
        %% 澄清分支
        Cond_Clear -- "否 (is_clear=False)" --> Node_Clarify["3. request_clarification<br/>(生成澄清追问并触发 Checkpoint 中断)"]
        Node_Clarify --> End_Clarify([挂起等待用户澄清])

        %% Map-Reduce 扇出
        Cond_Clear -- "是 (is_clear=True)" --> Send_Agent["4. Send('agent', ...)<br/>(Map-Reduce 并发扇出 1~3 个检索子问题)"]
    end

    %% 子图流转
    subgraph Agent_SubGraph ["研究子图：AgentSubGraphState (多步工具研究循环)"]
        Send_Agent --> Sub_Orch["5. orchestrator (Agent 编排节点)<br/>(首轮强制触发初筛，依据证据决策下一步)"]
        
        Sub_Orch --> Cond_Orch{"编排器输出决策"}
        
        %% 工具调用分支
        Cond_Orch -- "调用工具 (tool_calls)" --> Sub_Tools["6. 两阶段检索工具执行"]
        
        subgraph Tool_Execution ["两阶段检索工具 (create_retrieval_tools)"]
            Tool_Search["search_child_chunks<br/>(第一阶段：向量相似度初筛，返回子块与 Parent ID)"]
            Tool_Parent["retrieve_parent_chunks<br/>(第二阶段：根据 Parent ID 获取完整父块大段落)"]
        end
        
        Sub_Tools --> Tool_Search
        Sub_Tools --> Tool_Parent
        
        Tool_Search --> Sub_Record["记录已检索 query 与 parent_id<br/>(retrieval_keys 集合，防止重复调用)"]
        Tool_Parent --> Sub_Record
        Sub_Record --> Cond_Budget{"Token 是否增长过快？<br/>(估算 > 3000 Token)"}
        
        Cond_Budget -- "是" --> Sub_Compress["7. compress_context<br/>(动态提炼当前研究事实，压缩上下文)"]
        Cond_Budget -- "否" --> Sub_Orch
        Sub_Compress --> Sub_Orch
        
        %% 降级兜底分支
        Cond_Orch -- "超出预算/轮次超限 (iteration>=5)" --> Sub_Fallback["8. fallback_response<br/>(根据已有检索证据强制总结，防止死循环)"]
        
        %% 完成子问题回答
        Cond_Orch -- "证据充分/无工具调用" --> Sub_Collect["9. collect_answer<br/>(输出当前子问题的独立回答与来源)"]
        Sub_Fallback --> Sub_Collect
    end

    %% 主图汇总
    subgraph Main_Aggregate ["主图：结果归纳与事件推送"]
        Sub_Collect --> Node_Agg["10. aggregate_answers<br/>(综合所有子问题的回答与引用，输出最终答案)"]
        Node_Agg --> SSE_Push["11. SSE 流式分发<br/>(event: delta / meta / done / error)"]
        SSE_Push --> Commit_Turn["12. ChatService 事务提交<br/>(持久化 ChatMessage 与 Citation)"]
        Commit_Turn --> End_Done([完成本轮对话])
    end
```

---

## 3. 关键架构设计与运行机制详解

### 3.1 两阶段切分与按需检索（Two-Stage Parent-Child Retrieval）
- **切分阶段 (`ParentChildTextChunker`)**：
  1. 使用 `MarkdownHeaderTextSplitter` 提取天然章节树；
  2. 自动合并过小父块（`_merge_small_parents`，将碎片合并并更新标题路径 `章节1 -> 章节2`）；
  3. 递归切分子块（`RecursiveCharacterTextSplitter`，500 字符，50 字符重叠），子块携带 `parent_id`。
- **检索阶段 (`create_retrieval_tools`)**：
  1. **第一阶段初筛 (`search_child_chunks`)**：基于 LanceDB 向量计算，快速检索出语义最匹配的细粒度 Child 片段，返回概要、相似度与 `parent_id`；
  2. **第二阶段大上下文获取 (`retrieve_parent_chunks`)**：Agent 根据初筛线索，按需调取完整的 Parent 章节段落，彻底消除断章取义。

### 3.2 自适应查询分析与 Map-Reduce 扇出（Query Analysis & Map-Reduce）
- 在 `rewrite_query` 节点中，利用大模型的结构化输出能力（`with_structured_output(QueryAnalysis)`）：
  - **模糊代词识别**：若提问严重缺失主语或指代不明（如“那个怎么用”），标记 `is_clear=False` 并给出澄清反问，触发 LangGraph 的 Checkpoint 中断，等待用户补充说明；
  - **复杂问题拆解**：若问题清晰，自动将其重写并分解为 1~3 个相互独立的子问题，通过 LangGraph 的 `Send("agent", ...)` 并发分发给子图 Agent 进行独立研究。

### 3.3 工具循环治理与动态压缩（Loop Safety & Context Compression）
- **防死循环与去重**：子图维护 `retrieval_keys: Annotated[set[str], set_union]` 状态，记录已执行过的检索词和已获取的父块 ID，禁止重复调取。
- **动态上下文压缩 (`compress_context`)**：当检索证据累计导致 Token 估算超出阈值时，自动触发压缩节点，提取事实、过滤工具冗余，将上下文提炼至 300~600 字结构化摘要后继续研究。
- **硬限制降级 (`fallback_response`)**：当迭代轮次达 5 次或工具调用达 8 次时，平滑降级至兜底归纳节点，避免大模型陷入死循环。

### 3.4 最终归纳与平滑流式推送（Aggregation & SSE Streaming）
- 所有子问题的研究结果汇总至 `aggregate_answers`，提炼连贯答案并严格按格式附加 `来源：\n- 文件名.ext`。
- `ChatService` 监听 LangGraph 产生的实时更新，通过标准 Server-Sent Events（SSE）将打字机文本（`delta`）、思考状态、引用来源（`Citation`）即时推送到前端界面。

---

## 4. 技术栈总览

| 分层 | 核心技术选型 | 作用与优势 |
| :--- | :--- | :--- |
| **状态机与编排** | `LangGraph` + `LangChain Core` | 双层图状态机、Map-Reduce 扇出、Checkpoint 挂起中断与循环治理 |
| **后端框架** | Python 3.12 + `FastAPI` + `Uvicorn` | 异步高性能、原生支持异步流式 SSE 与 OpenAPI 规范 |
| **包管理** | `uv` | 高性能、确定性构建的 Python 依赖管理工具 |
| **关系型持久化** | `SQLite 3` (`aiosqlite`) | 单机零部署、轻量可靠的事务性关系数据存储 |
| **向量数据库** | `LanceDB` | 嵌入式高性能向量数据库，支持 Columnar 格式与毫秒级向量初筛 |
| **Embedding 引擎**| `FastEmbed` (`bge-small-zh-v1.5`) | 本地 CPU 高效运行，无需外部网络依赖 |
| **文档智能切分** | `MarkdownHeaderTextSplitter` + `RecursiveSplitter` | Markdown 标题感知 + 自适应小块合并 + 两阶段父子映射 |
| **前端应用** | React 18 + TypeScript + Vanilla CSS | 模块化设计、极速响应、无缝深色模式与流式打字机高亮渲染 |
