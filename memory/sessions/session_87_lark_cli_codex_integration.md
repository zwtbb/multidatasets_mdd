# Session Memory: Lark CLI Codex Integration

Status: complete
Last updated: 2026-08-25 UTC
Thread/task: connect Feishu/Lark CLI to Codex for paper-writing collaboration

## Scope

This session owns the environment-level Feishu/Lark CLI setup for the current
Codex shell. It does not change manuscript content, experimental evidence, or
claim boundaries.

## Current State

- `lark-cli` is installed at `/usr/bin/lark-cli` via the official npm installer
  from `@larksuite/cli@1.0.89`.
- The installer also completed its Agent skills installation step.
- `lark-cli config init --new --lang zh` completed successfully for brand
  `feishu`; the configured CLI app id is `cli_aa06306e8eb8dbb5`.
- `lark-cli auth login --recommend` completed successfully. `auth status
  --json --verify` reported both `user` and `bot` identities as ready, with
  document, docx, drive, wiki, sheets, im, minutes, task, and related scopes.
- A minimal write/read smoke test succeeded:
  - Created `Codex 接入测试` in `my_library`.
  - Test URL:
    `https://tcn9unqodkum.feishu.cn/docx/IsKDdFHAWoYGJxx1cBAcMkwvnqg`
  - `docs +fetch --doc-format markdown` returned the expected title and body.
- The user-provided manuscript wiki page was repaired directly:
  `https://tcn9unqodkum.feishu.cn/wiki/FeR4wSHOdiydQJkiQsBcqShcn0d`
  resolves to docx `IhyidscO8ojjNtxbaTtc75i4nmh`. The page now has six real
  image blocks, no repository-local image paths, no prose hard-wrap pairs, and
  no short standalone `$$...$$` formula lines.

## Key Decisions

- Use the official CLI path rather than creating a custom connector or
  modifying the experiment repository.
- Use `--recommend` scopes first. Add exact scopes later only if a real command
  returns a missing-scope error.
- For paper collaboration, operate directly on the Feishu wiki/docx page after
  fetching current content. Temporary Markdown/image export artifacts are not
  kept in the repository.
- For document creation/update, follow the CLI's `lark-doc` contract:
  read/fetch the target first, use `docs +update` for targeted edits, and use
  Markdown import only for faithful Markdown/document-package transfer.

## Files Owned Or Touched

- `/root/autodl-tmp/memory/sessions/session_87_lark_cli_codex_integration.md`
- `/root/autodl-tmp/MEMORY.md`
- `/root/autodl-tmp/memory/ACTIVE_HANDOFF.md`

## Generated Artifacts

- Feishu smoke-test document:
  `https://tcn9unqodkum.feishu.cn/docx/IsKDdFHAWoYGJxx1cBAcMkwvnqg`
- Repaired manuscript wiki/docx:
  `https://tcn9unqodkum.feishu.cn/wiki/FeR4wSHOdiydQJkiQsBcqShcn0d`
  / `https://tcn9unqodkum.feishu.cn/docx/IhyidscO8ojjNtxbaTtc75i4nmh`

Useful verification commands:

```bash
lark-cli auth status --json --verify
lark-cli docs +fetch --as user --doc 'https://tcn9unqodkum.feishu.cn/docx/IsKDdFHAWoYGJxx1cBAcMkwvnqg' --doc-format markdown
```

## Blockers And Risks

- The CLI warns that `HTTPS_PROXY=http://127.0.0.1:1080` is present, so requests
  including credentials may transit through that proxy. The setup was left using
  the current environment because authentication and verification succeeded.
- Future Feishu document updates should still be treated as real writes to the
  user's workspace. Use dry-run for large imports or risky overwrite/update
  operations.

## Next Handoff

Use `lark-cli` directly from this shell for Feishu document collaboration. For
the manuscript, fetch the existing wiki/docx page, make targeted edits, and
write them back with `docs +update`. Use dry-run or revision IDs for broad
updates, and remove any temporary export files after use.
