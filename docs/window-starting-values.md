# Window Starting Values

**Status:** accepted starting-value list for the shipped example providers  
**Language:** British English  
**Not:** a tutorial, a how-to, a second manual, or a flag list

Working figures for `chars_per_token`, `max_context_tokens` and `max_output_tokens`.  
Procedures live in the Manual (*How to keep requests inside the model’s context window*).  
Exact keys, ranges and board cells live in the Technical Reference (§2 and §9).

The estimator runs only when all three keys are set. Otherwise the board shows `window n/a`.  
`max_context_tokens` (\(W\)) is input plus reserved output.  
`max_output_tokens` (\(O\)) is the reserved reply **and** the API `max_tokens` value.  
Input budget is \(W - O\). `chars_per_token` is characters divided by this figure, truncated; it is not a vendor tokenizer. There is no runtime default.

Check a change with simulation:

```bash
dragiter -s -v -c config-ollama.toml -p prompt.toml -r resource.toml
```

---

## Starting values

| Provider | `model_name` | File | `chars_per_token` | `max_context_tokens` | `max_output_tokens` |
|---|---|---|---:|---:|---:|
| Ollama | `qwen3:8b` | `examples/01_md_sample/config-ollama.toml` (same triple in examples 02 and 03) | 3.8 | 4096 | 1024 |
| xAI Grok | `grok-4.6` | `examples/01_md_sample/config-grok.toml` | 3.8 | 128000 | 10240 |
| Anthropic Claude | `claude-sonnet-5` | `examples/01_md_sample/config-claude.toml` | 3.8 | 128000 | 10240 |
| Google Gemini | `gemini-3.8-flash` | `examples/01_md_sample/config-google.toml` | 3.8 | 128000 | 10240 |

When this page and a shipped file disagree, the file in front of you wins.

---

## Pitfalls

**Ollama.** \(W\) is the loaded `num_ctx`, not the library architecture figure. The OpenAI-compatible `/v1` API does not set or return `num_ctx`. Read the CONTEXT column of `ollama ps` before raising \(W\). Local Ollama is not a getting-started path.

**Grok.** Do not paste the vendor 500 000-token window as \(W\). Long-context pricing starts above 200 000 tokens. Omit none of the three keys: “no text output limit” is not a reason to leave `max_output_tokens` unset.

**Claude.** Do not paste the vendor 1M window as \(W\), and do not set \(O\) near \(W\).

**Gemini.** Do not paste the vendor 1 048 576 input cap as \(W\) or the 65 536 output cap as \(O\) on a first run.
