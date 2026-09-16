# dragiter suggested settings

**Version:** derived from source (2026.9.13) plus vendor figures retrieved 15 September 2026  
**Language:** British English  
**Audience:** power users and the maintainer  
**Scope:** First-cut window figures for the four shipped example providers. A cookbook. Not a tutorial, not a how-to, not a second manual and not a flag list.  
**Sources:** `examples/01_md_sample/config-*.toml`, `docs/manual.md`, `docs/reference.md`, `docs/info.txt`, and vendor pages listed in each table

When this page disagrees with the Manual or the Technical Reference, name the file and the version and treat this page as uncertain. Vendor columns age quickly; the shipped TOML comments are already behind some vendor pages.

British English is used throughout.

---

## How to extend this page

Add a new `##` chapter for a **shipped** example config only. Do not invent a provider that has no `config-*.toml` in the 2026.9.13 tree. Do not rename an existing heading: MkDocs permalinks follow the heading text.

Each provider chapter uses this order:

1. Identity (`base_url`, `model_name`, path of the shipped file)
2. TOML fragment copied from that file
3. Table: tree row, recommended row, other names that appear in the tree or on the vendor page
4. Typical pitfall
5. Pointer to Manual versus Reference
6. What the reporter should send

Do not introduce admonition syntax, tabbed fences or other Material extras — `mkdocs.yml` currently enables only `search` and `privacy`.

To publish on the site, copy this file next to `manual.md` / `reference.md` (CI already copies `docs/*.md` into `web/`) and add one nav entry in `mkdocs.yml`:

```yaml
nav:
  - Home: index.md
  - Manual: manual.md
  - Reference: reference.md
  - FAQ: faq.md
  - Glossary: glossary.md
  - Starting values: suggested-settings.md
```

---

## 1. What this page is

A starting-values cookbook. It tells you which three numbers to type first. Procedures live in the Manual. Exact keys, ranges and board cells live in the Technical Reference.

The estimator runs only when **all three** are set:

- `chars_per_token` — characters divided by this figure, then truncated to an integer
- `max_context_tokens` — working total (input **plus** reserved output)
- `max_output_tokens` — reserved for the reply **and** sent to the API as `max_tokens`

Otherwise the board shows `window n/a` and `peak / limit --`.

Recommended working total \(W\) is **not** the vendor marketing maximum. The Manual’s cloud starting point is 128 000. Local models start smaller until the loaded window is known.

Recommended output reservation:

\[
O = \operatorname{clamp}(0.08\,W,\; 4096,\; \min(O_{\mathrm{vendor}}, 16384))
\]

On an unmeasured Ollama tag use \(W = 8192\), \(O = 2048\). Input allowed is always \(W - O\). Do not set \(O\) near \(W\).

`chars_per_token` is an estimate, not a vendor tokenizer. Prefer a slightly low figure (more estimated tokens, earlier refusal). The shipped comments use 3.8; the test Ollama config uses 4.0. This page uses 3.6 locally and 3.8 on the cloud providers.

Check any change with simulation. The board cells that matter are `window`, `peak / limit`, `tokens`, `pack` and `over`.

```bash
dragiter -s -v -c config-ollama.toml -p prompt.toml -r resource.toml
```

See Manual, How to keep requests inside the model’s context window. See Reference §2 and §9.

---

## 2. Ollama

Shipped file: `examples/01_md_sample/config-ollama.toml`.  
OpenAI-compatible base: `http://localhost:11434/v1`.  
Example model: `qwen3:8b`.  
`tcp_keep_alive` is live in this file; the window lines are comments.

```toml
api_key = "Ollama"
base_url = "http://localhost:11434/v1"
model_name = "qwen3:8b"
tcp_keep_alive = true
# chars_per_token = 3.8
# max_context_tokens = 32000
# max_output_tokens = 4000
```

| model_name | chars_per_token | max_context_tokens | max_output_tokens | Source |
|---|---:|---:|---:|---|
| `qwen3:8b` | 3.8 | 32000 | 4000 | comment in `config-ollama.toml` (2026.9.13) |
| `qwen3:8b` recommended until `num_ctx` is measured | 3.6 | 8192 | 2048 | cookbook, 15 September 2026 |
| `qwen3:8b` after `num_ctx ≥ 32768` | 3.6 | 32768 | 4096 | cookbook, 15 September 2026 |
| `llama3` | — | — | — | named in Manual and `docs/info.txt`; Ollama library lists an 8k architecture window |
| `gemma3:27b` | — | — | — | not in the tree; Ollama library lists a 128k architecture window |

Ollama publishes two different numbers. The library “context window” is the architecture limit. The loaded window is `num_ctx` (Modelfile, `OLLAMA_CONTEXT_LENGTH`, or a hardware default — often 2048 or 4096). The OpenAI-compatible `/v1` API neither returns nor sets `num_ctx`. Read it with native `POST /api/show` or `ollama ps`.

The Ollama library lists `qwen3:8b` at 40k; the Qwen 3 announcement lists the 8B weights at 128k. Do not treat either figure as the loaded window.

Typical pitfall: copying `32000` from the comment while the runner still has `num_ctx` at 4096. dragiter then allows a payload the runner will truncate. A reverse proxy that closes a silent prefill at 60 s returns HTTP 504 / gateway timeout; that fault is **not** retried.

See Manual, How to connect; live streaming and retry rules. See Reference §1a, §2 and §9.

If it is unclear, send the `-s -v` board, the live TOML, `POST /api/show` for the same tag, and whether a 504 arrived before the first stream token.

---

## 3. xAI Grok

Shipped file: `examples/01_md_sample/config-grok.toml`.  
OpenAI-compatible base: `https://api.x.ai/v1`.  
Example model: `grok-4.6`.

```toml
# api_key = "DO-NOT-PUT-A-REAL-KEY-HERE"
base_url = "https://api.x.ai/v1"
model_name = "grok-4.6"
# chars_per_token = 3.8
# max_context_tokens = 128000
# max_output_tokens = 8192
```

| model_name | chars_per_token | max_context_tokens | max_output_tokens | Source |
|---|---:|---:|---:|---|
| `grok-4.6` | 3.8 | 128000 | 8192 | comment in `config-grok.toml` (2026.9.13) |
| `grok-4.6` recommended | 3.8 | 128000 | 10240 | cookbook, 8 % of 128 000, 15 September 2026 |
| `grok-4.6` vendor window | — | 500000 | no published text output cap | xAI model page, retrieved 15 September 2026 |
| `grok-4.3` | — | 1000000 | — | Manual how-to uses `--model-name "grok-4.3"`; xAI lists a 1M window |
| `grok-beta` | — | — | — | named in `docs/info.txt` only |

The Manual example (`grok-4.3`) and the shipped file (`grok-4.6`) disagree. Prefer the file in front of you and name the version if a ticket cites the other slug.

xAI documents “no text output limit” for Grok 4.6. That is not a reason to omit `max_output_tokens`. Without the third key the board stays `n/a`. Do not set \(W\) to 500 000 on the first run: cost and time-to-first-token rise with prefill.

Typical pitfall: treating the vendor 500k figure as the dragiter working total, or leaving `max_output_tokens` unset because the vendor cap is missing.

See Manual, How to connect; How to keep requests inside the model’s context window. See Reference §2 and §9.

If it is unclear, send the `-s -v` board and the live `model_name`.

---

## 4. Anthropic Claude

Shipped file: `examples/01_md_sample/config-claude.toml`.  
Base in the file: `https://api.anthropic.com/v1`.  
Example model: `claude-sonnet-4-6`.

```toml
# api_key = "DO-NOT-PUT-A-REAL-KEY-HERE"
base_url = "https://api.anthropic.com/v1"
model_name = "claude-sonnet-4-6"
# chars_per_token = 3.8
# max_context_tokens = 128000
# max_output_tokens = 8192
```

| model_name | chars_per_token | max_context_tokens | max_output_tokens | Source |
|---|---:|---:|---:|---|
| `claude-sonnet-4-6` | 3.8 | 128000 | 8192 | comment in `config-claude.toml` (2026.9.13) |
| `claude-sonnet-4-6` recommended | 3.8 | 128000 | 10240 | cookbook, 8 % of 128 000, 15 September 2026 |
| `claude-sonnet-4-6` vendor window | — | 1000000 | 128000 | Anthropic context-windows page, retrieved 15 September 2026 |
| Claude Sonnet 5 / Opus 5 family | — | 1000000 | 128000 | same page; no slug in the 2026.9.13 tree |
| Claude Sonnet 4.5 / Haiku 4.5 | — | 200000 | 64000 (Haiku 4.5) | same page; no slug in the tree |

The shipped 128 000 working total matches the Manual’s typical cloud start. The vendor 1M window is real for Sonnet 4.6 and is **not** the first value to paste into `max_context_tokens`. Setting `max_output_tokens` to the vendor 128 000 while \(W\) stays 128 000 leaves no input budget.

Typical pitfall: confusing the consumer-chat 200k figure with the API 1M figure, or pairing a 128k working total with a 128k output reserve.

See Manual, How to supply API keys securely; window check. See Reference §2.

If it is unclear, send the `-s -v` board and whether the request used the Anthropic Messages API or the OpenAI-compatible proxy in front of it.

---

## 5. Google Gemini

Shipped file: `examples/01_md_sample/config-google.toml`.  
OpenAI-compatible base: `https://generativelanguage.googleapis.com/v1beta/openai/`.  
Example model: `gemini-3.6-flash`.

```toml
# api_key = "DO-NOT-PUT-A-REAL-KEY-HERE"
base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
model_name = "gemini-3.6-flash"
# chars_per_token = 3.8
# Maximum context window of the model (input + output)
# Gemini 2.5 Flash supports up to 1M tokens. 200k-500k is a good practical range.
# max_context_tokens = 200000
# max_output_tokens = 8192
```

| model_name | chars_per_token | max_context_tokens | max_output_tokens | Source |
|---|---:|---:|---:|---|
| `gemini-3.6-flash` | 3.8 | 200000 | 8192 | comment in `config-google.toml` (2026.9.13) |
| `gemini-3.6-flash` recommended | 3.8 | 200000 | 16384 | cookbook, 8 % of 200 000, under the vendor output cap, 15 September 2026 |
| `gemini-3.6-flash` vendor limits | — | 1048576 input | 65536 output | Google model page, retrieved 15 September 2026 |
| `gemini-3.8-flash` | — | 1048576 | 65536 | Google Flash page, retrieved 15 September 2026; not in the tree |

The comment in the shipped file still talks about **Gemini 2.5 Flash**. The live `model_name` is `gemini-3.6-flash`. Treat that comment as stale and keep the 200 000 working total as a practical cap, not as the vendor maximum.

Google counts a combined context window and also publishes separate input / output caps. dragiter has one working total plus one output reserve. Do not put 1 048 576 in `max_context_tokens` and 65 536 in `max_output_tokens` on a first run.

Typical pitfall: taking the 1M input cap as \(W\) and the 64k output cap as \(O\) at the same time. Prefill of that size is what trips a 60 s first-byte proxy even though the client read timeout is unlimited.

See Manual, How to connect (Google via the OpenAI-compatible base URL). See Reference §2 and §9.

If it is unclear, send the `-s -v` board and the exact `model_name` string.

---

## 6. What this page will not do

It will not list LiteLLM or any other proxy as a fifth provider — there is no shipped example config.

It will not treat architecture limits, `num_ctx`, and `max_context_tokens` as one number.

It will not retry a gateway timeout. Shrink \(W\), pack or split material, or raise the proxy first-byte limit.

See Manual, Design philosophy (streaming, 504 not retried). See Reference §1a (`CompletionRetryPolicy`).
