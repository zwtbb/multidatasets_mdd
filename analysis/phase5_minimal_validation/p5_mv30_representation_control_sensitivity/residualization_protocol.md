# MV30 Residualization Protocol

The identity probe is fold-internal. Within each training fold, feature values are imputed from training medians, standardized on the training fold, residualized by ordinary least squares against the selected controls with an intercept, then projected by PCA fitted only on the training fold before held-out classification.

The severity control is one clinical total-score covariate. The length control is not a single scalar: each modality contributes the available log-transformed acquisition or availability counters, such as transcript segment/token/chunk counts for text, duration/chunk counts for audio, and frame/segment counts for video.

The shuffled-control row keeps the same covariate marginals but permutes rows within each train/evaluation fold before residualization. If shuffled controls do not remove identity while aligned controls do, the drop is attributed to corpus-linked length/acquisition structure rather than to residualization being mechanically too strong.

| probe | length controls | severity controls | length+severity controls |
| --- | ---: | ---: | ---: |
| cmdc_pdch_qwen3_text_same_language_hamd | 3 | 1 | 4 |
| cmdc_pdch_wavlm_audio_same_language_hamd | 3 | 1 | 4 |
| edaic_cmdc_openface_video_nontext | 1 | 1 | 2 |
| edaic_cmdc_qwen3_text_cross_language | 3 | 1 | 4 |
| edaic_cmdc_wavlm_audio_nontext | 3 | 1 | 4 |
| edaic_internal_openface_video_lineage | 2 | 1 | 3 |
| edaic_internal_qwen3_text_lineage | 5 | 1 | 6 |
| edaic_internal_wavlm_audio_lineage | 4 | 1 | 5 |
