# hermes-deepseek-cache

[中文](README.md) | **English**

A [Hermes](https://github.com/NousResearch/hermes-agent) plugin for DeepSeek API prefix-cache wire shaping: strip `reasoning_content` from non-tool-call assistant turns to improve cache hit rate, and accumulate cache token usage stats.

License: [MIT](LICENSE)

## Features

- Before each LLM request, strip `reasoning_content` / `reasoning` / `reasoning_details` from assistant turns **without** `tool_calls`
- Keep `reasoning_content` on turns that have `tool_calls` (required by the DeepSeek API)
- After each API response, accumulate `cache_read_tokens` / `input_tokens` into a local `stats.json`

## Install

```bash
# Copy or symlink into the Hermes plugins directory
cp -r hermes-deepseek-cache ~/.hermes/plugins/hermes-deepseek-cache
# For development:
# ln -s "$(pwd)" ~/.hermes/plugins/hermes-deepseek-cache
```

Add the plugin to `plugins.enabled` in `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - hermes-deepseek-cache
```

It takes effect automatically once enabled—no extra configuration.

## Limitations

- Only runs when `provider: deepseek`; all other providers (including DeepSeek model names via OpenRouter) are skipped
- Only strips reasoning fields on assistant turns **without** `tool_calls`; turns with `tool_calls` keep them
- When there is nothing to change, the middleware returns `None` to avoid unnecessary deepcopy and prefix churn
- Stats are written to `~/.hermes/plugins/hermes-deepseek-cache/stats.json`

## Coexistence with LCM

This plugin does not conflict with Hermes built-in LCM: it only removes fields such as `reasoning_content`, and does not modify `content` or `tool_calls` that LCM depends on. You can disable it at any time with no side effects.

## Tests

```bash
python -m pytest tests/
```

## Layout

```
hermes-deepseek-cache/
├── plugin.yaml      # Hermes plugin manifest
├── __init__.py      # Register middleware + hook
├── wire.py          # DeepSeek detection and reasoning strip
├── usage.py         # Cache token parsing and accumulation
├── tests/           # Unit tests
└── LICENSE
```

## Acknowledgments

The wire-shaping approach is inspired by [DeepSeek-Reasonix](https://github.com/esengine/DeepSeek-Reasonix) (Reasonix): suppress `reasoning_content` echo on non-tool-call assistant turns to keep DeepSeek's prefix cache stable. This repository is an independent Hermes plugin and has no code affiliation with Reasonix.
