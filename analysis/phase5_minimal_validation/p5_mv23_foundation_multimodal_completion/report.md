# P5 MV23 Foundation Multimodal Completion Stress Test

Generated: `2026-08-24T13:01:06+00:00`

## Scope

MV23 completes the lightweight foundation-backbone reinforcement by adding audio-only, video-proxy, text-audio, and text-audio-video feature views to the same PHQ shared-item transfer contract used in MV22. It compares direct/alignment baselines with a lightweight measurement-aware latent-total proxy head.

## View Coverage

| view | dataset | asset | modality | rows | input columns |
| --- | --- | --- | --- | ---: | ---: |
| audio_wav2vec2_base | cmdc | audio_wav2vec2_base | audio | 77 | 768 |
| audio_wav2vec2_base | edaic | audio_wav2vec2_base | audio | 219 | 768 |
| audio_wavlm_base_plus | cmdc | audio_wavlm_base_plus | audio | 77 | 768 |
| audio_wavlm_base_plus | edaic | audio_wavlm_base_plus | audio | 219 | 768 |
| bge_m3_plus_wavlm_audio_plus_openface_video | cmdc | audio_wavlm_base_plus | audio | 77 | 768 |
| bge_m3_plus_wavlm_audio_plus_openface_video | cmdc | text_bge_m3 | text | 77 | 1024 |
| bge_m3_plus_wavlm_audio_plus_openface_video | cmdc | video_openface_common | video | 44 | 204 |
| bge_m3_plus_wavlm_audio_plus_openface_video | edaic | audio_wavlm_base_plus | audio | 219 | 768 |
| bge_m3_plus_wavlm_audio_plus_openface_video | edaic | text_bge_m3 | text | 219 | 1024 |
| bge_m3_plus_wavlm_audio_plus_openface_video | edaic | video_openface_common | video | 219 | 204 |
| multilingual_e5_plus_wavlm_audio_plus_openface_video | cmdc | audio_wavlm_base_plus | audio | 77 | 768 |
| multilingual_e5_plus_wavlm_audio_plus_openface_video | cmdc | text_multilingual_e5 | text | 77 | 768 |
| multilingual_e5_plus_wavlm_audio_plus_openface_video | cmdc | video_openface_common | video | 44 | 204 |
| multilingual_e5_plus_wavlm_audio_plus_openface_video | edaic | audio_wavlm_base_plus | audio | 219 | 768 |
| multilingual_e5_plus_wavlm_audio_plus_openface_video | edaic | text_multilingual_e5 | text | 219 | 768 |
| multilingual_e5_plus_wavlm_audio_plus_openface_video | edaic | video_openface_common | video | 219 | 204 |
| qwen3_plus_wav2vec2_audio | cmdc | audio_wav2vec2_base | audio | 77 | 768 |
| qwen3_plus_wav2vec2_audio | cmdc | text_qwen3 | text | 77 | 1024 |
| qwen3_plus_wav2vec2_audio | edaic | audio_wav2vec2_base | audio | 219 | 768 |
| qwen3_plus_wav2vec2_audio | edaic | text_qwen3 | text | 219 | 1024 |
| qwen3_plus_wavlm_audio | cmdc | audio_wavlm_base_plus | audio | 77 | 768 |
| qwen3_plus_wavlm_audio | cmdc | text_qwen3 | text | 77 | 1024 |
| qwen3_plus_wavlm_audio | edaic | audio_wavlm_base_plus | audio | 219 | 768 |
| qwen3_plus_wavlm_audio | edaic | text_qwen3 | text | 219 | 1024 |
| qwen3_plus_wavlm_audio_plus_openface_video | cmdc | audio_wavlm_base_plus | audio | 77 | 768 |
| qwen3_plus_wavlm_audio_plus_openface_video | cmdc | text_qwen3 | text | 77 | 1024 |
| qwen3_plus_wavlm_audio_plus_openface_video | cmdc | video_openface_common | video | 44 | 204 |
| qwen3_plus_wavlm_audio_plus_openface_video | edaic | audio_wavlm_base_plus | audio | 219 | 768 |
| qwen3_plus_wavlm_audio_plus_openface_video | edaic | text_qwen3 | text | 219 | 1024 |
| qwen3_plus_wavlm_audio_plus_openface_video | edaic | video_openface_common | video | 219 | 204 |
| video_openface_common | cmdc | video_openface_common | video | 44 | 204 |
| video_openface_common | edaic | video_openface_common | video | 219 | 204 |

## Best Direct Or Alignment Baselines

| view | transfer | method | macro item MAE | total MAE | domain BA | target N |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| audio_wav2vec2_base | cmdc_to_edaic_phq_shared | groupdro_severity_proxy | 0.9205 | 5.3830 | 0.9800 | 219 |
| audio_wav2vec2_base | cmdc_to_edaic_phq_shared | dann_itemwise_mlp | 0.9263 | 5.5231 | 0.9510 | 219 |
| audio_wav2vec2_base | edaic_to_cmdc_phq_shared | coral_itemwise_ridge | 0.8939 | 6.3422 | 0.2249 | 77 |
| audio_wav2vec2_base | edaic_to_cmdc_phq_shared | dann_itemwise_mlp | 0.9011 | 6.1341 | 0.9810 | 77 |
| audio_wavlm_base_plus | cmdc_to_edaic_phq_shared | groupdro_severity_proxy | 0.9147 | 5.4323 | 0.9978 | 219 |
| audio_wavlm_base_plus | cmdc_to_edaic_phq_shared | irm_severity_env_proxy | 0.9161 | 5.4316 | 0.9978 | 219 |
| audio_wavlm_base_plus | edaic_to_cmdc_phq_shared | erm_itemwise_ridge | 0.9295 | 5.7005 | 1.0000 | 77 |
| audio_wavlm_base_plus | edaic_to_cmdc_phq_shared | coral_itemwise_ridge | 0.9295 | 6.6236 | 0.2335 | 77 |
| bge_m3_plus_wavlm_audio_plus_openface_video | cmdc_to_edaic_phq_shared | mmd_mean_itemwise_ridge | 0.9659 | 5.5845 | 0.3745 | 219 |
| bge_m3_plus_wavlm_audio_plus_openface_video | cmdc_to_edaic_phq_shared | coral_itemwise_ridge | 0.9748 | 6.2828 | 0.2123 | 219 |
| bge_m3_plus_wavlm_audio_plus_openface_video | edaic_to_cmdc_phq_shared | mmd_mean_itemwise_ridge | 0.7691 | 4.5772 | 0.2161 | 44 |
| bge_m3_plus_wavlm_audio_plus_openface_video | edaic_to_cmdc_phq_shared | coral_itemwise_ridge | 0.8840 | 5.8834 | 0.2603 | 44 |
| multilingual_e5_plus_wavlm_audio_plus_openface_video | cmdc_to_edaic_phq_shared | mmd_mean_itemwise_ridge | 0.9847 | 5.6639 | 0.3828 | 219 |
| multilingual_e5_plus_wavlm_audio_plus_openface_video | cmdc_to_edaic_phq_shared | coral_itemwise_ridge | 1.0254 | 6.7891 | 0.2215 | 219 |
| multilingual_e5_plus_wavlm_audio_plus_openface_video | edaic_to_cmdc_phq_shared | mmd_mean_itemwise_ridge | 0.8405 | 4.8174 | 0.2335 | 44 |
| multilingual_e5_plus_wavlm_audio_plus_openface_video | edaic_to_cmdc_phq_shared | coral_itemwise_ridge | 0.9336 | 6.4592 | 0.2435 | 44 |
| qwen3_plus_wav2vec2_audio | cmdc_to_edaic_phq_shared | coral_itemwise_ridge | 0.8988 | 5.7646 | 0.2162 | 219 |
| qwen3_plus_wav2vec2_audio | cmdc_to_edaic_phq_shared | groupdro_severity_proxy | 1.0577 | 5.2183 | 0.9992 | 219 |
| qwen3_plus_wav2vec2_audio | edaic_to_cmdc_phq_shared | mmd_mean_itemwise_ridge | 0.5974 | 3.3659 | 0.2313 | 77 |
| qwen3_plus_wav2vec2_audio | edaic_to_cmdc_phq_shared | coral_itemwise_ridge | 0.8300 | 5.8406 | 0.2069 | 77 |
| qwen3_plus_wavlm_audio | cmdc_to_edaic_phq_shared | coral_itemwise_ridge | 0.9336 | 5.9686 | 0.2205 | 219 |
| qwen3_plus_wavlm_audio | cmdc_to_edaic_phq_shared | groupdro_severity_proxy | 1.0502 | 5.2616 | 1.0000 | 219 |
| qwen3_plus_wavlm_audio | edaic_to_cmdc_phq_shared | coral_itemwise_ridge | 0.9326 | 6.5923 | 0.2026 | 77 |
| qwen3_plus_wavlm_audio | edaic_to_cmdc_phq_shared | mmd_mean_itemwise_ridge | 0.9910 | 7.0666 | 0.2213 | 77 |
| qwen3_plus_wavlm_audio_plus_openface_video | cmdc_to_edaic_phq_shared | mmd_mean_itemwise_ridge | 0.8333 | 6.6667 | 0.3592 | 219 |
| qwen3_plus_wavlm_audio_plus_openface_video | cmdc_to_edaic_phq_shared | erm_itemwise_ridge | 0.9878 | 5.8745 | 0.9985 | 219 |
| qwen3_plus_wavlm_audio_plus_openface_video | edaic_to_cmdc_phq_shared | coral_itemwise_ridge | 0.9573 | 6.6236 | 0.2283 | 44 |
| qwen3_plus_wavlm_audio_plus_openface_video | edaic_to_cmdc_phq_shared | mmd_mean_itemwise_ridge | 0.9933 | 6.9526 | 0.2130 | 44 |
| video_openface_common | cmdc_to_edaic_phq_shared | coral_itemwise_ridge | 1.0524 | 6.8920 | 0.2024 | 219 |
| video_openface_common | cmdc_to_edaic_phq_shared | erm_itemwise_ridge | 1.1550 | 6.3775 | 0.9940 | 219 |
| video_openface_common | edaic_to_cmdc_phq_shared | coral_itemwise_ridge | 0.9234 | 6.2580 | 0.2427 | 44 |
| video_openface_common | edaic_to_cmdc_phq_shared | mmd_mean_itemwise_ridge | 0.9456 | 6.2204 | 0.2431 | 44 |

## Measurement-Aware Proxy

| view | transfer | macro item MAE | total MAE | theta MAE | latent BA | post-head BA | target N |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| audio_wav2vec2_base | cmdc_to_edaic_phq_shared | 0.9520 | 7.0179 | 1.8749 | 0.5363 | 0.5363 | 219 |
| audio_wav2vec2_base | edaic_to_cmdc_phq_shared | 1.2858 | 9.6921 | 1.4739 | 0.7377 | 0.7377 | 77 |
| audio_wavlm_base_plus | cmdc_to_edaic_phq_shared | 2.0523 | 16.3532 | 6.0819 | 0.9599 | 0.9550 | 219 |
| audio_wavlm_base_plus | edaic_to_cmdc_phq_shared | 0.8242 | 6.5574 | 2.5409 | 0.8704 | 0.8709 | 77 |
| bge_m3_plus_wavlm_audio_plus_openface_video | cmdc_to_edaic_phq_shared | 1.4943 | 11.5054 | 953.5174 | 0.5361 | 0.5361 | 219 |
| bge_m3_plus_wavlm_audio_plus_openface_video | edaic_to_cmdc_phq_shared | 0.8153 | 5.7564 | 0.9174 | 0.6632 | 0.6632 | 44 |
| multilingual_e5_plus_wavlm_audio_plus_openface_video | cmdc_to_edaic_phq_shared | 0.9390 | 7.2753 | 850.7520 | 0.5518 | 0.5525 | 219 |
| multilingual_e5_plus_wavlm_audio_plus_openface_video | edaic_to_cmdc_phq_shared | 0.7544 | 5.7396 | 1.0933 | 0.7511 | 0.7511 | 44 |
| qwen3_plus_wav2vec2_audio | cmdc_to_edaic_phq_shared | 0.9201 | 7.2609 | 6.4619 | 0.9027 | 0.9073 | 219 |
| qwen3_plus_wav2vec2_audio | edaic_to_cmdc_phq_shared | 1.7337 | 13.8089 | 2.2946 | 0.9238 | 0.9253 | 77 |
| qwen3_plus_wavlm_audio | cmdc_to_edaic_phq_shared | 0.8705 | 6.8112 | 5.2121 | 0.8693 | 0.8746 | 219 |
| qwen3_plus_wavlm_audio | edaic_to_cmdc_phq_shared | 1.5230 | 11.5750 | 1.6301 | 0.8572 | 0.8579 | 77 |
| qwen3_plus_wavlm_audio_plus_openface_video | cmdc_to_edaic_phq_shared | 0.8587 | 6.8268 | 1475.9264 | 0.5871 | 0.5871 | 219 |
| qwen3_plus_wavlm_audio_plus_openface_video | edaic_to_cmdc_phq_shared | 1.1070 | 8.0703 | 1.0810 | 0.6553 | 0.6553 | 44 |
| video_openface_common | cmdc_to_edaic_phq_shared | 0.9459 | 7.2665 | 9.8001 | 0.7795 | 0.7929 | 219 |
| video_openface_common | edaic_to_cmdc_phq_shared | 1.4275 | 10.9652 | 1.5821 | 0.8569 | 0.8562 | 44 |

## Cross-View Top Rows

| transfer | view | method | family | macro item MAE | total MAE | identity BA |
| --- | --- | --- | --- | ---: | ---: | ---: |
| cmdc_to_edaic_phq_shared | qwen3_plus_wavlm_audio_plus_openface_video | mmd_mean_itemwise_ridge | direct_or_alignment_baseline | 0.8333 | 6.6667 | 0.3592 |
| cmdc_to_edaic_phq_shared | qwen3_plus_wavlm_audio_plus_openface_video | measurement_aware_latent_total_proxy | measurement_aware_proxy | 0.8587 | 6.8268 | 0.5871 |
| cmdc_to_edaic_phq_shared | qwen3_plus_wavlm_audio | measurement_aware_latent_total_proxy | measurement_aware_proxy | 0.8705 | 6.8112 | 0.8746 |
| cmdc_to_edaic_phq_shared | qwen3_plus_wav2vec2_audio | coral_itemwise_ridge | direct_or_alignment_baseline | 0.8988 | 5.7646 | 0.2162 |
| cmdc_to_edaic_phq_shared | audio_wavlm_base_plus | groupdro_severity_proxy | direct_or_alignment_baseline | 0.9147 | 5.4323 | 0.9978 |
| edaic_to_cmdc_phq_shared | qwen3_plus_wav2vec2_audio | mmd_mean_itemwise_ridge | direct_or_alignment_baseline | 0.5974 | 3.3659 | 0.2313 |
| edaic_to_cmdc_phq_shared | multilingual_e5_plus_wavlm_audio_plus_openface_video | measurement_aware_latent_total_proxy | measurement_aware_proxy | 0.7544 | 5.7396 | 0.7511 |
| edaic_to_cmdc_phq_shared | bge_m3_plus_wavlm_audio_plus_openface_video | mmd_mean_itemwise_ridge | direct_or_alignment_baseline | 0.7691 | 4.5772 | 0.2161 |
| edaic_to_cmdc_phq_shared | bge_m3_plus_wavlm_audio_plus_openface_video | measurement_aware_latent_total_proxy | measurement_aware_proxy | 0.8153 | 5.7564 | 0.6632 |
| edaic_to_cmdc_phq_shared | audio_wavlm_base_plus | measurement_aware_latent_total_proxy | measurement_aware_proxy | 0.8242 | 6.5574 | 0.8709 |

## Interpretation Boundary

- MV23 is a bounded foundation-view stress test, not a full multimodal training run.
- Audio uses existing WavLM base-plus and wav2vec2-base caches; WavLM Large/HuBERT Large remain unclaimed unless separate caches are generated.
- Video is an OpenFace common-statistics proxy, not VideoMAE.
- The measurement-aware row is a lightweight latent-total proxy head, used to test the framework logic under stronger/fused representations.
- No participant-level feature matrix, prediction row, theta table, model internals, raw text, raw audio, or raw video is tracked.

## Decision

- Status: `complete`.
- Artifact hygiene passed: `True`.
- Views executed: `8`.
