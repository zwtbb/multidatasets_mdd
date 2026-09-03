# MV30 Representation-Control Sensitivity

Generated: `2026-09-02T17:42:41+00:00`

## Reviewer-Facing Question

MV25 showed that raw E-DAIC/CMDC corpus identity is near-perfect but becomes near-chance after fold-internal length and severity residualization. MV30 decomposes that result and adds a nonlinear probe plus shuffled-control rows.

## Primary E-DAIC/CMDC Check

| view | probe | raw BA | length-only BA | severity-only BA | length+severity BA | shuffled-control BA | interpretation |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| openface_video_common | linear_logistic | 1.000 [1.000, 1.000] | 0.508 [0.496, 0.521] | 1.000 [1.000, 1.000] | 0.514 [0.503, 0.526] | 1.000 [1.000, 1.000] | aligned length/acquisition controls account for the raw identity signal |
| openface_video_common | nonlinear_random_forest | 0.801 [0.754, 0.849] | 0.502 [0.499, 0.506] | 0.794 [0.752, 0.836] | 0.504 [0.500, 0.508] | 0.795 [0.743, 0.848] | near-chance after aligned controls |
| qwen3_text | linear_logistic | 1.000 [1.000, 1.000] | 0.495 [0.487, 0.502] | 1.000 [1.000, 1.000] | 0.494 [0.482, 0.505] | 1.000 [1.000, 1.000] | aligned length/acquisition controls account for the raw identity signal |
| qwen3_text | nonlinear_random_forest | 0.999 [0.997, 1.001] | 0.988 [0.980, 0.995] | 1.000 [1.000, 1.000] | 0.987 [0.983, 0.991] | 1.000 [1.000, 1.000] | identity persists after aligned controls |
| wavlm_audio | linear_logistic | 1.000 [1.000, 1.000] | 0.481 [0.458, 0.505] | 1.000 [1.000, 1.000] | 0.486 [0.463, 0.509] | 1.000 [0.999, 1.000] | aligned length/acquisition controls account for the raw identity signal |
| wavlm_audio | nonlinear_random_forest | 0.961 [0.956, 0.965] | 0.600 [0.585, 0.615] | 0.963 [0.959, 0.966] | 0.614 [0.599, 0.629] | 0.959 [0.948, 0.969] | modest residual identity remains |

## Writing Implication

The manuscript should not say that language or protocol was directly residualized. A defensible wording is that the raw identity signal is strongly coupled to corpus-linked length/acquisition structure and clinical severity; in the primary E-DAIC/CMDC rows, length/acquisition controls account for most of the raw separability, while severity alone does not.

Same-language lineage probes remain useful because they show whether identity persists after aligned controls when language is held constant.

## Files

- `control_decomposition_summary.csv`
- `control_decomposition_table.csv`
- `control_decomposition_table.md`
- `residualization_protocol.md`
