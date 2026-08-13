# Project Instructions

## Session Memory

- `MEMORY.md` is the master memory for this experiment project. It records
  only current global status, cross-session decisions, active gates, and the
  session-memory index.
- Detailed histories belong in per-session files under
  `memory/sessions/` in the current repository checkout.
- At the start of every new session, read `MEMORY.md` completely before making
  plans, edits, audit claims, or experiment decisions. Then read only the
  relevant session memory file(s) listed there for the task being resumed or
  extended.
- Each new focused task/session should create or update its own session memory
  file under `memory/sessions/` in its current checkout, using
  `memory/templates/session_memory_template.md` as the shape.
- Update the master `MEMORY.md` only with stable cross-session facts, final
  decisions, current blockers, and next orchestration steps. Do not put long
  per-run logs or full metric tables in the master memory.
- Generated manifests, audit reports, matrix status files, and final tables
  remain the local numeric source of truth; memory files should cite their paths
  instead of duplicating large generated tables. This does not mean every
  generated artifact is Git-tracked. Phase 2 baseline result artifacts are
  local-only by default.
- In Codex worktree sessions, code, docs, session memory, and generated outputs
  should be written under the current worktree root. Raw data paths may still
  point to the canonical server dataset roots declared in `datasets/registry.yaml`;
  do not write experiment outputs back into `/root/autodl-tmp` from a worktree.

## Research Objective

The main goal of this experiment project is to systematically study label,
protocol, and population differences across depression-detection datasets, and
to propose a symptom-construct aligned framework. Model predictions should be
grounded in transferable symptom evidence rather than dataset protocol shortcuts
or population-specific spurious correlations.

## Research And Network Access

- It is allowed to browse the internet whenever useful for checking papers,
  code, documentation, datasets, benchmark definitions, dataset licenses,
  official repositories, or related technical details.
- Prefer primary sources for factual claims: official dataset pages, papers,
  code repositories, documentation, and challenge pages.

## Behavior Guardrails / 行为准则

- 不要假设。不要隐藏不确定性、困惑、阻塞或权衡取舍；尽早用具体证据和当前可选路径暴露出来。
- 只写解决当前已验证问题的最小代码；不要添加推测性功能、推测性分支，或没有实验合同支撑的未来扩展。
- 只修改必须修改的地方；只清理本轮工作自己产生的问题。
- 在声称完成前先明确定义成功标准；验证通过前持续迭代，否则记录真实 blocker。

### Anti-Overengineering / Anti-Defensive Programming

- 信任内部代码、框架保证和项目不变量，除非当前证据明确推翻它们。
- 只在系统边界做校验：用户输入、当前受控流程之外的文件、外部 API、网络调用、安装工具、数据集输入、仓库发布边界。
- 禁止为项目合同中“不可能发生”的内部状态添加错误处理、回退、空值检查或额外验证；让不可能的内部状态快速失败。
- 绝不吞掉错误：禁止宽泛 `catch`/`except`、`rescue nil`、静默默认值、空值回退或只给模糊 warning 的处理方式。
- 禁止为一次性操作创建辅助函数、工具类、抽象或框架，除非它确实消除重复复杂度，或符合项目既有模式。
- 优先快速失败并给出有用错误信息，而不是掩盖问题。

## Dataset Governance

- Use `/root/autodl-tmp/datasets/registry.yaml` as the source of truth for
  dataset paths, roles, label types, protocols, modalities, and status.
- Use generated manifests under `/root/autodl-tmp/datasets/manifests/` as the
  experiment input interface.
- Do not train from ad hoc raw-directory scans unless the registry and manifest
  layer is being intentionally updated.
- Keep all splits subject-level. Do not split segments, modalities, tasks, or
  sessions from the same subject across train/dev/test.
- Raw datasets, large features, archives, audio, video, model weights, and local
  runtime files must stay out of Git.

## Audit And File Hygiene

- Regenerate dataset audit artifacts with:

```bash
python /root/autodl-tmp/scripts/audit_datasets.py
```

- The current audit source of truth is `/root/autodl-tmp/datasets/audit/`.
- Static or stale governance files that duplicate generated audit output should
  be updated or deleted immediately.
- Do not keep obsolete conclusions around as extra Markdown files.
