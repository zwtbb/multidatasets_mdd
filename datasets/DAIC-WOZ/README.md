# DAIC-WOZ Local Layout

Last updated: 2026-08-24 UTC

This directory configures DAIC-WOZ as the AVEC2017 benchmark view over the
overlapping E-DAIC subject folders.

## Layout

- `splits/`: local DAIC-WOZ/AVEC2017 split and label CSV files downloaded from
  the USC ICT DAIC-WOZ file index.
- `documents/`: local DAIC-WOZ documentation PDF from the same index.
- `extracted/`: symlinks to `/root/autodl-tmp/datasets/edaic/extracted/*_P`
  for the 189 official DAIC-WOZ subject IDs in the 300-492 range.

The symlinked folders are not a second raw-data copy. They exist so
`datasets/registry.yaml` and `scripts/audit_datasets.py` can expose a clean
`daicwoz` manifest while preserving one physical extracted-data source.

## Usage Contract

- Use `daicwoz` only for DAIC-WOZ/AVEC2017 benchmark reproduction.
- Use `edaic` for the 275-subject E-DAIC project contract.
- Do not pool `daicwoz` and `edaic` as independent datasets. Their DAIC-WOZ
  subjects overlap exactly with E-DAIC subject folders `300_P` through
  `492_P` where present in the official DAIC-WOZ splits.

Regenerate the DAIC-WOZ manifest and aggregate audit with:

```bash
python /root/autodl-tmp/scripts/audit_datasets.py
```
