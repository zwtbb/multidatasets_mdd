# P5_MV06 Evidence Localization Readiness

Generated: `2026-08-09T05:48:54+00:00`

## Scope

This readiness pass checks whether existing minimal-validation predictions can support a bounded evidence-localization workflow. It does not read raw clinical text, export snippets, or write source paths. Any future snippet review must stay local-only unless separately deidentified and approved.

## Available Evidence Sources

- E-DAIC: MV01 PHQ C01-C08 construct predictions with manifest text availability.
- CMDC: MV01 PHQ C01-C08 predictions and limited MV02 HAMD sanity predictions with manifest text availability.
- PDCH: MV02 HAMD item/construct predictions with manifest text availability.

## Candidate Buckets

- `high_prediction_error`: cases where evidence review should explain likely model failure.
- `low_prediction_error`: cases where evidence review should test whether model success is supported by symptom evidence.
- `high_true_severity`: cases likely to contain explicit clinical evidence for the target construct.

## Annotation Fields

| field | values | tracked? |
| --- | --- | --- |
| symptom_construct | C01-C13 or HAMD item | aggregate only |
| evidence_presence | explicit_support; explicit_negation; insufficient; protocol_artifact | aggregate only |
| evidence_source | participant; interviewer; scale_item; unknown | aggregate only |
| evidence_strength | 0; 1; 2 | aggregate only |
| time_status | current; past; hypothetical; unclear | aggregate only |
| raw_snippet | free text | local-only, never tracked by default |
| source_path | filesystem path | local-only, never tracked by default |

## Stop Conditions

- Stop evidence claims if candidate evidence mainly highlights prompts, fixed questions, or dataset identity cues.
- Stop C09 claims unless the evidence is an explicit scale item or explicit clinical text.
- Stop cross-dataset evidence claims unless evidence agreement is separately shown for each dataset.
