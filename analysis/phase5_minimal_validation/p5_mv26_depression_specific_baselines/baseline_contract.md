# MV26 Depression-Specific Baseline Contract

MV26 is a targeted close-baseline stress test, not a broad leaderboard expansion. It asks whether the measurement-aware target layer still adds value after three depression-specific modeling ideas: GNN-SDA-style semi-supervised graph domain adaptation, QuestMF-style question-wise ordinal fusion, and SCD-MLLM-style heterogeneous multimodal adapter/fusion.

All rows use the same E-DAIC <-> CMDC split, the same eight shared PHQ items, the same official MV24 Qwen3 + WavLM + OpenFace subject representation, the same five seeds, and the same labeled target calibration budget. The intended contrast within each family is the final target pathway: direct ordinal item head versus shared symptom layer plus corpus-specific cumulative ordinal heads.

| method | reference | MV26 adaptation | target calibration labels |
| --- | --- | --- | --- |
| gnn_sda_style_direct_head | Chen et al., IEEE Transactions on Multimedia 2024, Semi-Supervised Domain Adaptation for Major Depressive Disorder Detection | static kNN graph over official MV24 foundation representations, adversarial domain head, target unlabeled pseudo-labeling, and shared direct ordinal item head | yes |
| gnn_sda_style_measurement_aware | Chen et al., IEEE Transactions on Multimedia 2024, Semi-Supervised Domain Adaptation for Major Depressive Disorder Detection | replace the direct target head with a shared symptom layer and corpus-specific cumulative ordinal heads | yes |
| questmf_style_direct_head | Mandal et al., CLPsych 2025, Enhancing Depression Detection via Question-wise Modality Fusion | per-PHQ-item gates over Qwen3 text, WavLM audio, and OpenFace video features with a direct ordinal item head | yes |
| questmf_style_measurement_aware | Mandal et al., CLPsych 2025, Enhancing Depression Detection via Question-wise Modality Fusion | per-item fused evidence is converted to shared symptom scores and reconstructed through corpus-specific cumulative ordinal heads | yes |
| scd_mllm_style_direct_head | Chen et al., Pattern Recognition 2026, Towards Stable Cross-Domain Depression Recognition under Missing Modalities | prompt-like corpus tokens and masked text/audio/video adapters over official frozen foundation features feed an adaptive fusion representation and a direct ordinal item head | yes |
| scd_mllm_style_measurement_aware | Chen et al., Pattern Recognition 2026, Towards Stable Cross-Domain Depression Recognition under Missing Modalities | the adaptive fusion representation feeds the paper's shared symptom layer plus corpus-specific cumulative ordinal measurement heads | yes |

Rows are style/adapted implementations under our subject-level frozen-feature and PHQ shared-item target contract. They should be cited as controlled target-pathway stress tests rather than exact reproductions of external leaderboard settings.
