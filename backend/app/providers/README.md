# Provider boundaries

后续实现统一接口，并把具体厂商或算法放在对应目录中：

- `llm/`：语言模型
- `embedding/`：Embedding 模型
- `vector_store/`：向量存储
- `parsers/`：文档解析器
- `chunking/`：切片策略
- `retrieval/`：召回、融合和 Rerank

业务模块只依赖 Provider 接口，不直接依赖具体实现。

