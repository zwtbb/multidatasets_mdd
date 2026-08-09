# GitHub Publish Workflow

This repository has two Git histories:

- Local `/root/autodl-tmp/main`: the long server-working history. It is useful
  locally, but it contains early generated Phase 2 result blobs in old commits.
- GitHub `zwtbb/multidatasets_mdd main`: the clean public/reproducible lineage
  created from audited snapshots.

Do not push the local `main` history directly to GitHub.

Use `scripts/publish_clean_github_snapshot.py` for future GitHub updates. The
helper archives the committed source tree, overlays it onto a fresh clone of
the clean remote branch, runs artifact and secret checks, creates a clean
lineage commit, and only pushes when `--push` is provided.

## Normal Publish

1. Commit the local source changes that should be included.

```bash
git status --short
git add <safe paths>
git commit -m "<local commit message>"
```

2. Dry-run the clean publish candidate.

```bash
python scripts/publish_clean_github_snapshot.py \
  --message "<clean GitHub commit message>"
```

3. Review the printed source commit, file count, diff stat, and policy checks.

4. Push the audited clean snapshot.

```bash
python scripts/publish_clean_github_snapshot.py \
  --push \
  --message "<clean GitHub commit message>"
```

## What Belongs On GitHub

Track the core reproducible experiment skeleton:

- Maintained scripts and configs.
- Dataset registry, lightweight manifests, and audit summaries.
- Governance docs, issue log, README, and memory files.
- Small Phase 3+ diagnostic and method-validation summaries needed for paper
  reproducibility.

Keep these local-only:

- Raw datasets, archives, audio, video, pretrained weights, checkpoints, caches,
  and local runtime files.
- Raw clinical text, raw prompts, raw model responses, source-locator maps, and
  per-subject evidence packets.
- Bulky feature arrays, embeddings, row-level predictions, and model binaries.
- Generated `analysis/phase2_baselines/` result artifacts.

## Publish Gate

The helper rejects the publish tree when it finds:

- `analysis/phase2_baselines/`.
- CSV paths containing `predictions`, `embeddings`, or `weights`.
- `model*.joblib` or `model*.pkl` files.
- Plaintext credential-like content such as GitHub token patterns, basic-auth
  GitHub URLs, or obvious password/token assignments.

The checks are intentionally conservative. If a small CSV summary is rejected
because of its name, rename it to a non-row-level summary name only after
confirming it does not contain predictions, embeddings, subject-level rows, raw
text, or source paths.

## Authentication

Use GitHub token, SSH key, or `gh auth login` for authentication. Do not store
or use plaintext GitHub passwords in files, commands, memory, shell history, or
Git config.
