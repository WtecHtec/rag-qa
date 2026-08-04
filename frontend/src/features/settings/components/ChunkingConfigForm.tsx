/**
 * Parent-Child Chunk 切片策略配置表单组件。
 */

import type { ChunkingConfig } from "../types/settings";

interface ChunkingConfigFormProps {
  config: ChunkingConfig;
  onChange: (field: keyof ChunkingConfig, value: unknown) => void;
}

export function ChunkingConfigForm({ config, onChange }: ChunkingConfigFormProps) {
  return (
    <div className="settings-form-card">
      <div className="settings-form-head">
        <h3>Document Chunk 文档切片策略配置</h3>
        <p>配置 Parent-Child 切片参数（Parent Chunk 提供上下文，Child Chunk 负责高精向量检索）</p>
      </div>

      <div className="settings-grid">
        {/* Strategy Selector */}
        <div className="settings-field is-full">
          <label>切片策略 (Chunk Strategy)</label>
          <select
            value={config.strategy}
            onChange={(e) => onChange("strategy", e.target.value)}
          >
            <option value="parent_child">Parent / Child Chunk 双层结构 (推荐)</option>
            <option value="recursive">Recursive Character Chunking 递归切片</option>
            <option value="semantic">Semantic Chunking 语义切片 (预留)</option>
          </select>
        </div>

        {/* Parent Chunk Size */}
        <div className="settings-field">
          <label>Parent Chunk 上下文块大小 (字符数)</label>
          <input
            type="number"
            value={config.parent_chunk_size}
            onChange={(e) => onChange("parent_chunk_size", parseInt(e.target.value, 10))}
            style={{ fontFamily: "monospace" }}
          />
        </div>

        {/* Child Chunk Size */}
        <div className="settings-field">
          <label>Child Chunk 向量匹配块大小 (字符数)</label>
          <input
            type="number"
            value={config.child_chunk_size}
            onChange={(e) => onChange("child_chunk_size", parseInt(e.target.value, 10))}
            style={{ fontFamily: "monospace" }}
          />
        </div>

        {/* Overlap Size */}
        <div className="settings-field">
          <label>切片重叠区间 (Overlap Size)</label>
          <input
            type="number"
            value={config.overlap_size}
            onChange={(e) => onChange("overlap_size", parseInt(e.target.value, 10))}
            style={{ fontFamily: "monospace" }}
          />
        </div>
      </div>
    </div>
  );
}
