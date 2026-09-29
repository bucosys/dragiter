# Getting Started with Example 04

This example does three jobs at once.

1. It shows that `regex_patterns` is staged and countable.
2. It walks the compact requirements profile **one packed chunk at a time**
   (`sequential_processing = true`).
3. It shows `chunk_substitutions` cleaning a pasted-from-a-spreadsheet
   Markdown table (section 5.2): padded columns, a separator row, an
   inline dash run and a leftover blank-line run all get stripped or
   shortened before that piece becomes a chunk.

The corpus is `04_dragiter_requirements_profile.md`. It states the
product contract and is no longer padded with dummy text. Overflow is
produced by a section budget that sits below the longest `##` chapter —
chapter 5, which carries that pasted table, at well over 2 500
characters raw — not by inflating the file.

- Pattern 0: `^##\s+` — chapter grain.
- Pattern 1: `^###\s+` — only when a piece still exceeds `pack_limit_chars`.
- Pack budget on the section: `500` characters.
- `chunk_substitutions`: four rules, applied to each split piece in
  order — collapse `[ \t]{2,}`, drop a Markdown separator/rule line,
  shorten `-{3,}`, collapse `\n{3,}`. See section 5.2 of the profile and
  `04_resource_staged_regex.toml`.
- The default 200-chunk cap is far above this compact file. Demonstrate
  the breaker with `--max-chunks 1` (or any value below the packed count).
- No loop file. No singular `regex_pattern` key.

Simulate first and read the board. With `--pack-limit-chars 0` expect one
chunk per `##` heading that has body text, plus the title block
(21 pieces on the shipped profile). With the section budget of 500,
several chapters split on `###`, neighbours pack, `small / over` shows
leftover pieces above 500, and the session count is no longer 21.
Counts change if you edit the profile.

Read the chapter-5 chunk either way (`ID` `0006` at `--pack-limit-chars
0`) and confirm the table inside it has a single-spaced header, no
`|---` separator row, and no run of three or more dashes — that is
`chunk_substitutions` having already run, before you ever see the
piece.

A simulate run now writes the run board **and**, for every session, that
session's board followed by its complete outgoing request — the same
content whether the sink is `-o`, `-O` or plain stdout. Plain stdout is
consequently much longer than a summary board alone; prefer `-O out` (see
Step 1) if you just want a manageable read.

## Step 1. Work from the example directory

The resource glob is only the profile file name. If that file is not in
the process working directory (or in `-b`), dragiter loads **no chunks**.
The simulate file then falls back to the name `session_0001.md`, and its
content is the board for that session (`mode batched`, `file none`) followed
by the outgoing request with raw, unsubstituted `{CHUNK_*}` placeholders.

    cd examples/04_staged_regex_sample
    ls 04_dragiter_requirements_profile.md 04_prompt_staged_regex.toml 04_resource_staged_regex.toml

From elsewhere, pass the example directory as the base:

    mkdir -p out
    dragiter -b examples/04_staged_regex_sample \
      -p examples/04_staged_regex_sample/04_prompt_staged_regex.toml \
      -r examples/04_staged_regex_sample/04_resource_staged_regex.toml \
      -s -O out

`-O`'s target directory is never created automatically, so `mkdir -p out`
must run first.

Confirm the prompt file starts with `You are a ruthless technical editor`
and contains `sequential_processing = true`. An older copy still says
`precise analyst` and stays batched.

Running the same `-s -O out` (or any `-s -o FILE`) command a second time
now fails: simulate commits its output through the same mechanism as a
live run, and the default output mode `x` (exclusive create) refuses to
overwrite an existing target. Pass `-m w` to repeat a run into the same
target.

## Step 2. Prove the split before spending tokens

Chapter grain only:

    dragiter -s --pack-limit-chars 0 -p 04_prompt_staged_regex.toml -r 04_resource_staged_regex.toml

Expect one session per chapter-grain piece (see the simulate board).

Overflow plus packing:

    dragiter -s -p 04_prompt_staged_regex.toml -r 04_resource_staged_regex.toml

Read sessions / chunks from the board. `pack` should show `500`.
The two runs must differ: the section budget refines long chapters on
`###` and then packs neighbours. `small / over` is not `0 / 0`.

Chunk-cap abort (does not call the model):

    dragiter -s --max-chunks 1 -p 04_prompt_staged_regex.toml -r 04_resource_staged_regex.toml

That run must stop with `max_chunks` in the error. Raise the cap, or
omit the flag, to continue.

Optional waterfall:

    dragiter -s -v -d -p 04_prompt_staged_regex.toml -r 04_resource_staged_regex.toml

`--debug` must mention `pattern 1/2` and `pattern 2/2` on the long
chapters. It must not dump the profile text.

## Step 3. First cleaning pass (sequential, live)

    mkdir -p out_pass1
    dragiter -v -c ../01_md_sample/config-ollama.toml \
      -p 04_prompt_staged_regex.toml \
      -r 04_resource_staged_regex.toml \
      -O out_pass1 \
      -m x

One streamed call per packed chunk. Interrupt is exit status 130;
exclusive mode leaves finished files in place.

Concatenate in identifier order:

    cat out_pass1/04_clean_*.md > 04_pass1.md

## Step 4. Repeat if the draft is still padded

Point a copy of the resource file at `04_pass1.md` (or replace the
glob target), then write `out_pass2` the same way. Stop when a simulate
board plus a short read show only product rules.

Each pass can change chunk counts. Re-run step 2 against the new file
before the next live pass.

## What would fail this example

- `sequential_processing = false` (one giant batched request)
- a resource file that still contains `regex_pattern`
- a resource file whose first pattern does not cut on `## `
- a glob that also swallows this README
- a resource file whose `chunk_substitutions` no longer strip the
  section 5.2 table's separator row, padded columns or dash run

## Further information

    dragiter-gen-docs .
