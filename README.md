# hermes-deepseek-cache

[Hermes](https://github.com/NousResearch/hermes-agent) 插件：针对 DeepSeek API 做前缀缓存（prefix cache）线形成形——剥离非工具调用 assistant 消息中的 `reasoning_content`，提升缓存命中率，并统计缓存 token 用量。

License: [MIT](LICENSE)

## 功能

- 在 LLM 请求发出前，对 **无 `tool_calls`** 的 assistant 轮剥离 `reasoning_content` / `reasoning` / `reasoning_details`
- 带 `tool_calls` 的轮保留 `reasoning_content`（DeepSeek API 要求）
- 在 API 响应后累加 `cache_read_tokens` / `input_tokens` 等到本地 `stats.json`

## 安装

```bash
# 复制或 symlink 到 Hermes 插件目录
cp -r hermes-deepseek-cache ~/.hermes/plugins/hermes-deepseek-cache
# 开发时推荐：
# ln -s "$(pwd)" ~/.hermes/plugins/hermes-deepseek-cache
```

在 `~/.hermes/config.yaml` 的 `plugins.enabled` 中加入：

```yaml
plugins:
  enabled:
    - hermes-deepseek-cache
```

激活后自动生效，无需额外配置。

## 限制

- 仅当 `provider: deepseek` 时介入；其他 provider（含 OpenRouter 上的 DeepSeek 模型名）一律跳过
- 仅剥离**无 `tool_calls`** 的 assistant 轮上的 reasoning 字段；带 `tool_calls` 的轮保留
- 无改动时 middleware 返回 `None`，避免无谓 deepcopy 与前缀扰动
- 统计写入 `~/.hermes/plugins/hermes-deepseek-cache/stats.json`

## 与 LCM 共存

本插件与 Hermes 内置 LCM 无冲突：只删除 `reasoning_content` 等字段，不修改 LCM 依赖的 `content` 和 `tool_calls`。可随时停用，无副作用。

## 测试

```bash
python -m pytest tests/
```

## 项目结构

```
hermes-deepseek-cache/
├── plugin.yaml      # Hermes 插件清单
├── __init__.py      # 注册 middleware + hook
├── wire.py          # DeepSeek 检测与 reasoning 剥离
├── usage.py         # 缓存 token 解析与累计
├── tests/           # 单元测试
└── LICENSE
```

## 致谢

线形成形思路参考了 [DeepSeek-Reasonix](https://github.com/esengine/DeepSeek-Reasonix)（Reasonix）：对非工具调用的 assistant 轮抑制 `reasoning_content` 回显，以稳定 DeepSeek 前缀缓存。本仓库是面向 Hermes 的独立插件实现，与 Reasonix 无代码从属关系。
