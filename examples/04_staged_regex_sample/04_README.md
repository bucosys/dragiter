# Getting Started with Example 04

This example does two jobs at once.

1. It shows that `regex_patterns` is staged and countable.
2. It walks the compact requirements profile **one packed chunk at a time**
   (`sequential_processing = true`).

The corpus is `04_dragiter_requirements_profile.md`. It states the
product contract; it is no longer padded to force overflow.

- Pattern 0: `^##\s+` — chapter grain.
- Pattern 1: `^###\s+` — only when a piece still exceeds `pack_limit_chars`.
- Pack budget on the section: `4000` characters.
- Pack budgets around 1500 or below exceed the default 200-chunk cap.
  Raise it with `--max-chunks 400` (or `DRAGITER_MAX_CHUNKS`).
- No loop file. No singular `regex_pattern` key.

Simulate first and read the board. With `--pack-limit-chars 0` expect one
chunk per `##` chapter that has body text. With the section budget,
chapters that still exceed `pack_limit_chars` may split on `###` and
neighbours may pack. Counts change if you edit the profile.

## Step 1. Work from the example directory

The resource glob is only the profile file name. If that file is not in
the process working directory (or in `-b`), dragiter loads **no chunks**.
The simulate file then looks like `session_0001.md`, mode `batched`,
`file none`, and raw `{CHUNK_*}` placeholders.

    cd examples/04_staged_regex_sample
    ls 04_dragiter_requirements_profile.md 04_prompt_staged_regex.toml 04_resource_staged_regex.toml

From elsewhere, pass the example directory as the base:

    dragiter -b examples/04_staged_regex_sample \
      -p examples/04_staged_regex_sample/04_prompt_staged_regex.toml \
      -r examples/04_staged_regex_sample/04_resource_staged_regex.toml \
      -s -O out

Confirm the prompt file starts with `You are a ruthless technical editor`
and contains `sequential_processing = true`. An older copy still says
`precise analyst` and stays batched.

## Step 2. Prove the split before spending tokens

Chapter grain only:

    dragiter -s --pack-limit-chars 0 -p 04_prompt_staged_regex.toml -r 04_resource_staged_regex.toml

Expect one session per chapter-grain piece (see the simulate board).

Overflow plus packing:

    dragiter -s -p 04_prompt_staged_regex.toml -r 04_resource_staged_regex.toml

Read sessions / chunks from the board. `pack` should show `4,000`.
The two runs should differ only if at least one chapter exceeds the
budget; on the compact profile they may match.

Optional waterfall:

    dragiter -s -v -d -p 04_prompt_staged_regex.toml -r 04_resource_staged_regex.toml

`--debug` should mention `pattern 1/2` and `pattern 2/2` on the long
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

## Further information

    dragiter-gen-docs .
