# Session Memory: Remote And GitHub Cleanup

Status: complete
Last updated: 2026-09-02 UTC
Thread/task: main-agent remote/GitHub hygiene cleanup

## Scope

This session owns repository and remote hygiene after the MV24 fair-ablation
and manuscript revisions. It does not run new experiments, change manuscript
claims, sync Feishu, delete raw datasets, or delete reusable model/data caches.

## Current State

- Local tracked MV24/manuscript changes were committed on the old working
  branch as `c0cd6e9` (`Update MV24 fair ablations and manuscript claims`).
- The clean publish helper then published the same tree to GitHub `main` as
  `475360f` (`Publish MV24 fair ablation manuscript snapshot`).
- A cleanup-record commit was later pushed on clean `main` as `dd6dbcb`
  (`Record remote GitHub cleanup`).
- Local `/root/autodl-tmp` now sits on clean `main` tracking `origin/main`.
- GitHub remote branch inventory now contains only `main` at `dd6dbcb`.
- Old remote branches `codex/daic-woz`, `codex/main-result-table`, and
  `codex/measurement-aware-architecture` were deleted.
- Old local server-working branch refs and stale worktrees were removed after
  confirming the active tree matched the clean published tree.
- Python `__pycache__` directories, Hugging Face `*.incomplete` blobs, and the
  small `.Trash-0` directory were removed.

## Key Decisions

- Future GitHub updates should start from clean `main` and still use
  `scripts/publish_clean_github_snapshot.py` for the safety scan.
- Do not recreate or push old server-working branch history.
- MV27 remains excluded from Git and GitHub because it is not part of the
  current approved manuscript/paper evidence path.
- Large datasets, Phase 2 feature/result caches, model caches, and local-only
  experiment artifacts were retained because they remain useful for reruns and
  audit traceability.

## Files Owned Or Touched

- `/root/autodl-tmp/.gitignore`
- `/root/autodl-tmp/.git/info/exclude` local-only
- `/root/autodl-tmp/MEMORY.md`
- `/root/autodl-tmp/memory/ACTIVE_HANDOFF.md`
- `/root/autodl-tmp/memory/sessions/session_104_remote_github_cleanup.md`

## Generated Artifacts

No experiment artifacts were generated.

Validation commands:

```bash
git status --short --branch
git ls-remote origin refs/heads/main
git ls-remote origin 'refs/heads/*'
gh api repos/zwtbb/multidatasets_mdd/branches --paginate --jq '.[].name'
git count-objects -vH
```

## Blockers And Risks

- The 2026-09-02 MV24 fair-ablation and targeted-item manuscript revision is
  published to GitHub but still has not been synced to Feishu.
- MV27 local files are intentionally ignored, not deleted, because they may be
  useful only if the user later decides to include the negative binary
  benchmark supplement.

## Next Handoff

Continue future work from clean `main`. Before another GitHub update, commit
the intended source tree locally, run the clean publish helper first without
`--push`, then rerun with `--push` only after the helper reports no banned
paths or secret-like content.
