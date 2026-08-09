# Phase 2 Unified Baseline Protocol

Phase 2 freezes a credible, repeatable baseline matrix before any new method
design. The goal is not to add architectural novelty. The goal is to make the
simple unimodal, simple multimodal, and required public baselines comparable
under one evaluation contract.

## Scope

Allowed baseline families:

- Text: TF-IDF with Logistic or Ridge, frozen DeBERTa or ModernBERT embeddings
  with MLP, and sentence-level encoder with attention pooling.
- Audio: eGeMAPS with SVM or XGBoost, frozen WavLM embedding with linear or MLP,
  and frozen wav2vec2 embedding with linear or MLP.
- Video: OpenFace statistical features with MLP, and official visual features
  with temporal pooling.
- Gait: statistical gait features with Logistic or XGBoost, and IMU temporal
  encoder with MLP.
- Multimodal: Early Fusion, Late Fusion, and Gated Fusion only.

Forbidden in Phase 2:

- Hypergraph modules.
- Causal modules.
- LLM summaries.
- Contrastive learning.
- Personality gating.
- Public/private personality-domain disentanglement as a new contribution.
- Full fine-tuning of large pretrained encoders by default.

Most pretrained encoders are frozen at the start of Phase 2. Small datasets
should not begin with broad encoder fine-tuning.

## Required Public Baselines

E-DAIC:

- AVEC/E-DAIC official baseline.
- QuestMF.
- Existing local text, audio, and late-fusion baselines.
- QuestMF already covers PHQ-8 question-wise multimodal fusion and ordinal
  prediction, so PHQ item-wise prediction alone is not a novelty claim.

MPDD-AVG-2026:

- Official MPDD baseline.
- P3HF only if the available code and input features match the local MPDD-Young
  version.
- P3HF already covers personality-guided representation, public/private feature
  separation, and Hypergraph-Former. These are prior-art coverage, not standalone
  main innovations here.

PDCH:

- Official text-only baseline.
- Official audio-text baseline.
- Simple frozen WavLM and text-encoder baselines.
- First follow the original split or official cross-validation setting.

EATD-Corpus:

- Official GRU and BiLSTM baselines.
- Simple audio, text, and fusion baselines.

MODMA:

- eGeMAPS baseline.
- Frozen WavLM baseline.
- Task-specific and cross-task tests.

## Unified Metrics

Binary classification:

- Macro-F1
- Balanced Accuracy
- AUROC
- AUPRC

Severity regression:

- CCC
- MAE
- RMSE
- Spearman

Ordinal prediction:

- QWK
- Ordinal MAE
- Macro-F1

Credibility and calibration:

- ECE
- Brier Score

Every experiment must use at least five random seeds, subject-level splits,
bootstrap 95% confidence intervals, and no test-set hyperparameter selection.

## Machine-Readable Contract

The source of truth for Phase 2 runs is:

- `baselines/phase2_baseline_matrix.yaml`

Generate the planned baseline matrix and readiness audit with:

```bash
python scripts/phase2_baseline_matrix.py
```

The generated table columns are:

- `dataset`
- `modality`
- `task`
- `model`
- `metric`
- `mean`
- `std`

`mean` and `std` must remain blank until a validated five-seed result exists.
The project should not enter method design until this matrix is populated with
audited results.

## Subject Split Layer

Generate the Phase 2 subject split layer before running newly unlocked CMDC,
PDCH, or MODMA baselines:

```bash
python scripts/phase2_build_subject_splits.py
python scripts/phase2_baseline_matrix.py --strict
```

Generated files:

- `datasets/splits/phase2_subject_splits.csv`
- `analysis/phase2_baselines/phase2_subject_splits_summary.json`
- `analysis/phase2_baselines/phase2_subject_splits_report.md`

Current audit summary:

- 11220 split rows.
- 42 dataset/target/protocol combinations.
- Split output columns are limited to dataset, protocol, fold, role, subject ID,
  train task, eval task, and source metadata.
- No label-like columns or path-like columns are written.
- No train/evaluation subject-overlap violations are present.
- E-DAIC manifests now expose 275 valid subject rows with resolved transcript,
  audio, and OpenFace feature paths. Its official split remains 163 train,
  56 dev, and 56 test subjects.
- E-DAIC has 2 completed text TF-IDF rows, 3 completed frozen/simple text
  encoder rows including the sentence-attention row, 2 completed audio eGeMAPS
  rows, 4 completed frozen audio encoder rows, 2 completed video feature rows,
  all 3 audio/video/text fusion rows completed, both public reproduction rows
  completed (AVEC official and QuestMF), and 3 existing local baseline rows
  registered from audited local components.
- CMDC has 2 completed text TF-IDF rows, 1 completed frozen text encoder row,
  1 completed audio eGeMAPS row, 2 completed frozen audio encoder rows, all 3
  binary audio/text fusion rows completed, 1 completed HAMD-17 audio/text
  late-fusion row, and both planned video baseline rows completed.
- EATD-Corpus has 2 completed text TF-IDF rows, 1 completed audio eGeMAPS row,
  1 completed frozen WavLM row, all 3 SDS audio/text fusion rows completed,
  and both planned official GRU/BiLSTM-style public reproduction rows completed
  with the documented audited-feature adaptation caveat.
- MODMA has all 6 planned simple audio rows completed: 1 audio eGeMAPS row, 4
  frozen WavLM rows, and 1 frozen wav2vec2 row.
- MPDD-AVG-2026 has 2 completed gait-statistics rows, 1 completed IMU temporal
  row, both planned frozen WavLM audio rows, both planned video rows
  (ResNet temporal pooling and OpenFace statistics), all 3 AVP fusion rows, and
  the official public baseline completed. P3HF is retained only as a
  conditionally excluded public row.
- PDCH has 1 completed text TF-IDF row, 1 completed frozen text encoder row,
  1 completed audio eGeMAPS row, 1 completed frozen WavLM row,
  1 completed audio/text late-fusion row, and both official public reproduction
  rows completed: text-only and audio-text.

## Completed Result Blocks

E-DAIC text TF-IDF:

```bash
python scripts/phase2_run_edaic_text_tfidf.py
python scripts/phase2_baseline_matrix.py --strict
```

Completed runs:

- `edaic_text_phq8_tfidf_ridge`
- `edaic_text_binary_tfidf_logistic`

Protocol:

- Use manifest-resolved E-DAIC transcript paths only.
- Fit on the official 163-subject train split and evaluate on the official
  56-subject dev split.
- Leave the 56-subject test split unused.
- Concatenate transcript ASR `Text` rows in timestamp order.
- Use fixed TF-IDF + Ridge and TF-IDF + Logistic hyperparameters.
- Do not use dev or test labels for hyperparameter selection.
- Do not write raw transcript text or source paths.

Audit summary:

- 5 seeds: 0, 1, 2, 3, 4.
- 1000 subject-bootstrap resamples.
- 560 prediction rows across the two completed runs.
- No train/dev subject overlap.
- Transcript turn counts range from 42 to 203 turns per subject.
- The transcript CSVs do not expose a speaker column, so interviewer-only and
  participant-only controls remain separate RQ2 work.
- PHQ-8 mean metrics: CCC 0.0141, MAE 4.7452, RMSE 5.6466, Spearman 0.3458.
- Binary mean metrics: Macro-F1 0.4400, Balanced Accuracy 0.5000, AUROC 0.6098,
  AUPRC 0.4178, ECE 0.2168, Brier Score 0.2124.

E-DAIC frozen text encoder MLP:

```bash
python scripts/phase2_run_edaic_text_encoders.py --chunk-batch-size 16
python scripts/phase2_baseline_matrix.py --strict
```

Completed runs:

- `edaic_text_phq8_deberta_mlp`
- `edaic_text_phq8_modernbert_mlp`

Protocol:

- Use manifest-resolved E-DAIC transcript CSV paths.
- Encoders: frozen `microsoft/deberta-v3-base` and
  `answerdotai/ModernBERT-base`; no encoder parameters are updated.
- Fit on the official 163-subject train split and evaluate on the official
  56-subject dev split.
- Leave the 56-subject test split unused.
- Concatenate transcript ASR `Text` rows in timestamp order.
- Split long transcripts into max-length chunks, extract normalized CLS
  embeddings, token-count-weighted average chunks, and L2-normalize the
  subject embedding.
- Regression head: fixed MLPRegressor with one hidden layer of 64 units,
  `alpha=0.01`, `solver=lbfgs`, and `max_iter=2000`.
- Regression outputs are clipped to the train-split observed PHQ-8 range.
- Do not use dev or test labels for encoder extraction or hyperparameter
  selection.
- Do not write raw transcript text, source paths, or file names.

Audit summary:

- 5 seeds: 0, 1, 2, 3, 4.
- 1000 subject-bootstrap resamples.
- 560 prediction rows across the two completed runs.
- 219 train/dev subject feature rows per encoder.
- 768 embedding features per encoder.
- No train/dev subject overlap.
- DeBERTa mean metrics: CCC -0.0582, MAE 5.5151, RMSE 6.8755, Spearman
  -0.0658.
- ModernBERT mean metrics: CCC 0.2747, MAE 4.5642, RMSE 5.7808, Spearman
  0.2781.
- Prediction and feature artifacts do not write raw text or source paths.

E-DAIC sentence-attention text:

```bash
python scripts/phase2_run_edaic_text_sentence_attention.py
python scripts/phase2_baseline_matrix.py --strict
```

Completed run:

- `edaic_text_phq8_sentence_attention`

Protocol:

- Use manifest-resolved E-DAIC transcript CSV paths.
- Encoder: frozen `sentence-transformers/all-MiniLM-L6-v2` through
  Transformers `AutoTokenizer`/`AutoModel`; no encoder parameters are updated.
- Fit the attention head on the official 163-subject train split and evaluate
  on the official 56-subject dev split.
- Leave the 56-subject test split unused.
- Treat each non-empty ASR transcript `Text` row as one sentence/turn unit.
- Mean-pool last hidden states with the tokenizer attention mask, L2-normalize
  each 384-dimensional turn embedding, then learn a small attention-pooling
  regression head over turns.
- Attention head: hidden size 64, fixed `max_epochs=200`, `lr=1e-3`,
  `weight_decay=1e-4`, and `train_batch_size=32`.
- Standardize PHQ-8 with train-split mean/std and clip predictions to the
  train-split observed PHQ-8 range.
- Do not use dev or test labels for encoder extraction or hyperparameter
  selection.
- Do not write raw transcript text, source paths, or file names.

Audit summary:

- 5 seeds: 0, 1, 2, 3, 4.
- 1000 subject-bootstrap resamples.
- 280 prediction rows for the completed run.
- 219 train/dev subjects.
- 20512 transcript turns and 334627 tokenizer tokens across train/dev.
- 384 embedding dimensions.
- No train/dev subject overlap.
- Mean metrics: CCC 0.3518, MAE 4.8321, RMSE 6.2280, Spearman 0.3532.
- Prediction and metadata artifacts do not write raw text or source paths.

E-DAIC audio eGeMAPS:

```bash
python scripts/phase2_run_edaic_audio_egemaps.py
python scripts/phase2_baseline_matrix.py --strict
```

Completed runs:

- `edaic_audio_phq8_egemaps_svr`
- `edaic_audio_binary_egemaps_svm`

Protocol:

- Use manifest-resolved E-DAIC audio subject rows and local official
  `OpenSMILE2.3.0_egemaps.csv` frame-level feature files.
- Fit on the official 163-subject train split and evaluate on the official
  56-subject dev split.
- Leave the 56-subject test split unused.
- Aggregate 23 low-level eGeMAPS columns to 92 subject-level mean/std/min/max
  features.
- Keep `frame_count` only as an audit field, not as a model feature.
- Use fixed eGeMAPS + linear SVR and eGeMAPS + linear SVM hyperparameters.
- Do not use dev or test labels for hyperparameter selection.
- Do not write raw audio or source paths.

Audit summary:

- 5 seeds: 0, 1, 2, 3, 4.
- 1000 subject-bootstrap resamples.
- 560 prediction rows across the two completed runs.
- No train/dev subject overlap.
- Frame counts range from 41468 to 362761 frames per subject.
- PHQ-8 mean metrics: CCC 0.0970, MAE 5.2571, RMSE 6.5215, Spearman 0.0727.
- Binary mean metrics: Macro-F1 0.4313, Balanced Accuracy 0.4318, AUROC 0.4886,
  AUPRC 0.2368, ECE 0.0288, Brier Score 0.1707.

E-DAIC frozen audio encoders:

```bash
python scripts/phase2_run_edaic_audio_frozen_encoders.py --local-files-only --chunk-batch-size 8
python scripts/phase2_baseline_matrix.py --strict
```

Completed runs:

- `edaic_audio_phq8_wavlm_linear`
- `edaic_audio_phq8_wavlm_mlp`
- `edaic_audio_phq8_wav2vec2_linear`
- `edaic_audio_phq8_wav2vec2_mlp`

Protocol:

- Use manifest-resolved E-DAIC audio WAV paths.
- Encoders: frozen `microsoft/wavlm-base-plus` and
  `facebook/wav2vec2-base`; no encoder parameters are updated.
- Fit heads on the official 163-subject train split and evaluate on the
  official 56-subject dev split.
- Leave the 56-subject test split unused.
- Split audio into 20-second chunks. For each chunk, mean-pool last hidden
  states with the encoder attention mask, then duration-weight chunk embeddings
  into one 768-dimensional subject embedding.
- Linear head: Ridge regression with train-only inner 5-fold alpha selection
  over a fixed grid.
- MLP head: fixed MLPRegressor with one hidden layer of 64 units,
  `alpha=0.01`, `solver=lbfgs`, and `max_iter=2000`.
- Regression outputs are clipped to the train-split observed PHQ-8 range.
- Do not use dev or test labels for encoder extraction or hyperparameter
  selection.
- Do not write raw audio, source paths, or file names.

Audit summary:

- 5 seeds: 0, 1, 2, 3, 4.
- 1000 subject-bootstrap resamples.
- 1120 prediction rows across the four completed runs.
- 219 train/dev subject feature rows per encoder.
- 58.7155 total train/dev audio hours.
- 10682 chunks per encoder with 20-second chunking.
- No train/dev subject overlap.
- WavLM linear mean metrics: CCC 0.1274, MAE 4.6681, RMSE 5.7168, Spearman
  0.1913.
- WavLM MLP mean metrics: CCC 0.3061, MAE 5.0385, RMSE 6.4148, Spearman
  0.3377.
- wav2vec2 linear mean metrics: CCC 0.0596, MAE 4.6767, RMSE 5.9095,
  Spearman 0.0812.
- wav2vec2 MLP mean metrics: CCC 0.1179, MAE 5.6683, RMSE 7.0972, Spearman
  0.1243.
- Prediction and feature artifacts do not write raw audio or source paths.

E-DAIC video features:

```bash
python scripts/phase2_run_edaic_video_features.py
python scripts/phase2_baseline_matrix.py --strict
```

Completed runs:

- `edaic_video_phq8_openface_mlp`
- `edaic_video_phq8_official_temporal_pooling`

Protocol:

- Use manifest-resolved E-DAIC video subject rows and local official feature
  files from each subject folder.
- Fit on the official 163-subject train split and evaluate on the official
  56-subject dev split.
- Leave the 56-subject test split unused.
- OpenFace row: aggregate frame-level OpenFace columns to 204 subject-level
  mean/std/min/max features, then fit a fixed MLP regressor.
- Official visual row: pool `CNN_ResNet.mat` frame-level features to 4096
  subject-level mean/std features, then fit a fixed Ridge regressor.
- Keep frame counts only as audit fields, not as model features.
- Do not use dev or test labels for hyperparameter selection.
- Do not write raw video or source paths.

Audit summary:

- 5 seeds: 0, 1, 2, 3, 4.
- 1000 subject-bootstrap resamples.
- 560 prediction rows across the two completed runs.
- No train/dev subject overlap.
- OpenFace and ResNet frame counts range from 12447 to 108830 frames per
  subject in the official train/dev splits.
- OpenFace mean metrics: CCC 0.1717, MAE 5.2344, RMSE 6.8062, Spearman 0.1958.
- Official visual temporal-pooling mean metrics: CCC 0.3898, MAE 4.8506, RMSE
  5.9121, Spearman 0.3875.

E-DAIC audio/video/text fusion:

```bash
python scripts/phase2_run_edaic_av_fusion.py
python scripts/phase2_baseline_matrix.py --strict
```

Completed runs:

- `edaic_av_phq8_early_fusion`
- `edaic_av_phq8_late_fusion`
- `edaic_av_phq8_gated_fusion`

Protocol:

- Use manifest-resolved E-DAIC transcripts plus cached subject-level audio
  eGeMAPS and official ResNet temporal-pooling video features.
- Fit on the official 163-subject train split and evaluate on the official
  56-subject dev split.
- Leave the 56-subject test split unused.
- Early Fusion concatenates train-fit TF-IDF text features, standardized audio
  eGeMAPS features, and standardized ResNet temporal-pooling features, then
  fits fixed Ridge regression.
- Late Fusion averages audited dev predictions from
  `edaic_text_phq8_tfidf_ridge`, `edaic_audio_phq8_egemaps_svr`, and
  `edaic_video_phq8_official_temporal_pooling`.
- Gated Fusion sets global text/audio/video weights from train-only 5-fold OOF
  inverse MAE, then applies those weights to full-train component dev
  predictions.
- Do not use dev or test labels for hyperparameter or gate-weight selection.
- Do not write raw text, raw audio, raw video, or source paths.

Audit summary:

- 5 seeds: 0, 1, 2, 3, 4.
- 1000 subject-bootstrap resamples.
- 840 prediction rows across the three completed runs.
- No train/dev subject overlap.
- Late-fusion component alignment covers 280 audited dev prediction rows with
  0 label mismatches.
- Early-fusion feature width is 28336 for seed 0: 24148 TF-IDF text features,
  92 audio features, and 4096 video features.
- Early Fusion mean metrics: CCC 0.3263, MAE 5.0049, RMSE 6.0902, Spearman
  0.3071.
- Late Fusion mean metrics: CCC 0.2456, MAE 4.4296, RMSE 5.2917, Spearman
  0.3486.
- Gated Fusion mean metrics: CCC 0.2393, MAE 4.4306, RMSE 5.2971, Spearman
  0.3445.

E-DAIC existing local baselines:

```bash
python scripts/phase2_run_edaic_existing_baselines.py
python scripts/phase2_baseline_matrix.py --strict
```

Completed runs:

- `edaic_existing_text_baseline`
- `edaic_existing_audio_baseline`
- `edaic_existing_late_fusion`

Protocol:

- Use only already audited E-DAIC Phase 2 prediction files.
- Existing text baseline is registered from `edaic_text_phq8_tfidf_ridge`.
- Existing audio baseline is registered from `edaic_audio_phq8_egemaps_svr`.
- Existing late fusion is the unweighted mean of aligned audited local text and
  audio dev predictions.
- No separate legacy E-DAIC existing-baseline prediction artifact is present in
  the current workspace, so this block records the audited local components
  transparently.
- No test split is used and no dev/test labels are used for hyperparameter or
  fusion-weight selection.
- Do not write raw text, raw audio, source paths, or feature paths.

Audit summary:

- 5 seeds: 0, 1, 2, 3, 4.
- 1000 subject-bootstrap resamples.
- 840 prediction rows across the three completed runs.
- 56 dev subjects.
- Existing late-fusion alignment covers 280 audited dev prediction rows with
  0 label mismatches.
- Existing text mean metrics: CCC 0.0141, MAE 4.7452, RMSE 5.6466, Spearman
  0.3458.
- Existing audio mean metrics: CCC 0.0970, MAE 5.2571, RMSE 6.5215, Spearman
  0.0727.
- Existing late-fusion mean metrics: CCC 0.0696, MAE 4.7527, RMSE 5.7914,
  Spearman 0.0676.

E-DAIC AVEC 2019 DDS public-reproduction runner:

```bash
python scripts/phase2_run_edaic_public_avec.py
python scripts/phase2_baseline_matrix.py --strict
```

Prepared run:

- `edaic_public_avec_official`

Protocol:

- Public source: `https://github.com/AudioVisualEmotionChallenge/AVEC2019`,
  commit `c49d4b2f3d49905940d97a5ec4e0d3a6f08ef805`.
- Paper source: `https://arxiv.org/abs/1907.11510`.
- Preserve the official DDS model family: one 1-layer 64-dimensional GRU
  regressor per feature set, dropout 0.2, CCC loss, `Adam(amsgrad=True)`, and
  official per-feature learning rates.
- Use official development-CCC best-epoch selection and unweighted mean fusion
  over feature-set predictions.
- Use manifest-resolved E-DAIC train/dev subject rows. The local adaptation is
  limited to mapping official DDS feature readers to per-subject local feature
  files for eGeMAPS, MFCC, AUpose/OpenFace, BoAW/BoVW, ResNet, VGG,
  densenet201, and vgg16.
- Do not write checkpoints, raw text, raw audio/video data, prompts, source
  paths, or file paths to prediction outputs.
- Very long CUDA GRU sequences default to `--long-sequence-mode native_packed`,
  which preserves the official packed-sequence GRU semantics with cuDNN
  disabled for sequences longer than the current cuDNN packed-sequence limit.
  CLI choices are `native_packed`, `padded`, and `auto`; this is a runtime
  compatibility adaptation, not a model change.
- Completed feature/seed dev predictions are saved to progress CSVs after each
  seed so interrupted long runs can be resumed without writing model
  checkpoints.
- Progress loading preserves completed feature/seed blocks across separate
  selected-feature invocations by merging progress CSVs with existing partial
  feature-prediction artifacts.
- Write `phase2_metric_summary.csv` only when the full official matrix contract
  is satisfied: all 10 feature sets, seeds 0-4, 30 epochs, batch size 15, and
  at least 1000 subject-bootstrap resamples.
- Partial or smoke runs write only `edaic_public_avec_partial_*` metric files
  and therefore do not complete the matrix row.

Current status:

- `edaic_public_avec_official` is complete under the full official matrix
  contract: all 10 DDS feature sets, seeds 0-4, 30 epochs, batch size 15, and
  at least 1000 subject-bootstrap resamples.
- Canonical outputs live under
  `analysis/phase2_baselines/edaic_public_avec_official/` and include
  `phase2_metric_summary.csv`, feature-level predictions, fused predictions,
  and training trace.
- Subject `657` is missing `657_CNN_VGG.mat` in the original official AVEC
  feature release. The runner records this as a known official omission,
  excludes subject `657` only for the VGG feature-specific training/evaluation,
  and keeps the subject in final AVEC fusion using the available feature-set
  predictions.
- Historical smoke/partial attempts are not matrix-completing artifacts.

E-DAIC QuestMF public reproduction:

```bash
python scripts/phase2_run_edaic_public_questmf.py --local-files-only
python scripts/phase2_baseline_matrix.py --strict
```

Completed run:

- `edaic_public_questmf`

Protocol:

- Public source: `clpsych2025-questmf`, commit
  `3776a2bb84927b2613abf5686322b63957158c68`.
- Preserve QuestMF's PHQ-8 question-wise ordinal prediction contract, ImbOLL
  loss, text/audio/video recurrent encoders, and question-wise TAV fusion.
- Use the official E-DAIC train/dev split: 163 train subjects and 56 dev
  subjects. Do not use the test split.
- Use frozen `sentence-transformers/all-distilroberta-v1` turn embeddings,
  official openSMILE eGeMAPS turn pooling, and official ResNet turn pooling.
- Train seeds 0-4, all 8 PHQ-8 items, 10 unimodal epochs and 20 fusion epochs,
  with 1000 subject-bootstrap resamples.
- Write matrix metrics only when all 40 seed-question blocks are complete.
- Prediction artifacts do not write raw transcript text, source paths, file
  names, audio, video frames, or checkpoints.
- PHQ item-wise prediction and question-wise multimodal fusion are prior-art
  coverage from QuestMF, not a standalone innovation claim.

Audit summary:

- 2240 item-level prediction rows: 56 dev subjects x 8 PHQ-8 items x 5 seeds.
- 40/40 seed-question blocks complete, each with 56 dev subjects.
- Feature cache covers all 219 train/dev subjects.
- Mean metrics: QWK 0.5118, Ordinal MAE 0.6040, Macro-F1 0.4330, ECE 0.1252,
  Brier Score 0.6582.

EATD text TF-IDF:

```bash
python scripts/phase2_run_eatd_text_tfidf.py
python scripts/phase2_baseline_matrix.py --strict
```

Completed runs:

- `eatd_text_sds_tfidf_ridge`
- `eatd_text_binary_tfidf_logistic`

Audit summary:

- 83 train subjects and 79 validation subjects.
- 5 seeds: 0, 1, 2, 3, 4.
- 1000 subject-bootstrap resamples.
- No train/validation subject overlap.
- No test split used.
- Prediction artifacts do not write raw text.

EATD audio eGeMAPS:

```bash
python scripts/phase2_run_eatd_audio_egemaps.py
python scripts/phase2_baseline_matrix.py --strict
```

Completed run:

- `eatd_audio_sds_egemaps_svr`

Protocol:

- Use manifest-resolved valid EATD positive, neutral, and negative audio paths.
- Extract openSMILE eGeMAPSv02 functionals.
- Aggregate to one subject row with valence-prefixed eGeMAPS features and
  all-valence mean/std features.
- Evaluate the official train/validation subject split with 5 seeds.
- Use fixed RBF-SVR hyperparameters; do not tune on validation or test labels.
- Do not use a test split.
- Do not write raw audio, source paths, or file names.

Audit summary:

- 83 train subjects and 79 validation subjects.
- 486 valid audio segments.
- 440 model feature columns.
- 5 seeds: 0, 1, 2, 3, 4.
- 1000 subject-bootstrap resamples.
- No train/validation subject overlap.
- No test split used.
- Prediction and feature artifacts do not write raw audio or source paths.

EATD frozen WavLM audio:

```bash
python scripts/phase2_run_eatd_audio_wavlm.py --local-files-only
python scripts/phase2_baseline_matrix.py --strict
```

Completed run:

- `eatd_audio_binary_wavlm_linear`

Protocol:

- Use manifest-resolved valid EATD positive, neutral, and negative audio paths.
- Encoder: frozen `microsoft/wavlm-base-plus`; no WavLM parameters are updated.
- Segment embedding: split audio into fixed-duration chunks, mean-pool WavLM
  last hidden states, and duration-weight chunk embeddings per segment.
- Subject embedding: average positive, neutral, and negative segment embeddings
  per subject.
- Linear head: fixed LogisticRegression with balanced class weights.
- Evaluate the official train/validation subject split with 5 seeds.
- Do not use validation/test labels for hyperparameter selection.
- Do not use a test split.
- Do not write raw audio, source paths, or file names.

Audit summary:

- 83 train subjects and 79 validation subjects.
- 486 valid audio segments.
- 486 segment embedding rows and 162 subject feature rows.
- 768 WavLM feature columns.
- 395 prediction rows: 79 validation subjects per seed over 5 seeds.
- 1000 subject-bootstrap resamples.
- No train/validation subject overlap.
- No test split used.
- Prediction and feature artifacts do not write raw audio or source paths.

EATD audio/text fusion:

```bash
python scripts/phase2_run_eatd_audio_text_fusion.py
python scripts/phase2_baseline_matrix.py --strict
```

Completed runs:

- `eatd_audio_text_sds_early_fusion`
- `eatd_audio_text_sds_late_fusion`
- `eatd_audio_text_sds_gated_fusion`

Protocol:

- Use manifest-resolved valid EATD text and cached subject-level eGeMAPS
  features from the completed audio baseline.
- Early Fusion concatenates train-fit TF-IDF and standardized eGeMAPS features,
  then fits Ridge regression. Ridge alpha is selected only inside the train
  split by 5-fold OOF MAE over a fixed grid.
- Late Fusion averages audited EATD text TF-IDF and audio eGeMAPS validation
  predictions.
- Gated Fusion uses train-split-only inner 5-fold OOF MAE to set global
  inverse-error text/audio weights.
- Regression outputs are clipped to the train-split observed SDS target range.
- Evaluate the official train/validation subject split with 5 seeds.
- Do not use validation/test labels for fusion weighting or hyperparameter
  selection.
- Do not use a test split.
- Do not write raw text, raw audio, source paths, or file names to prediction
  outputs.

Audit summary:

- 83 train subjects and 79 validation subjects.
- 1185 prediction rows: 395 per completed fusion run.
- Late-fusion text/audio prediction key alignment is complete.
- Late-fusion label mismatches: 0.
- 440 audio model feature columns.
- 5 seeds: 0, 1, 2, 3, 4.
- 1000 subject-bootstrap resamples.
- No train/validation subject overlap.
- No test split used.
- Prediction artifacts do not write raw inputs or source paths.

EATD official GRU/BiLSTM-style public reproduction:

```bash
python scripts/phase2_run_eatd_public_gru_bilstm.py
python scripts/phase2_baseline_matrix.py --strict
```

Completed runs:

- `eatd_public_gru`
- `eatd_public_bilstm`

Protocol:

- Public source:
  `https://github.com/speechandlanguageprocessing/ICASSP2022-Depression`, commit
  `eded8cc0818d7768fec5e1a6564ef2f07eecf807`.
- Paper source: `https://arxiv.org/abs/2202.08210`.
- Use the official README train/validation subject split: 83 train subjects and
  79 validation subjects.
- Preserve the public recurrent model family over the three EATD emotional
  tasks: GRU and BiLSTM with attention.
- Use the project's audited feature interface because the original feature
  extraction code depends on old local ELMoForManyLangs, TensorFlow v1 VGGish,
  VGGish PCA, NetVLAD, and absolute local paths that are not runnable in the
  current Python 3.12/PyTorch 2.8 server.
- Each subject is represented as a length-3 sequence ordered positive, neutral,
  negative.
- Each time step concatenates audited openSMILE eGeMAPSv02 per-valence audio
  features with train-fit Chinese char TF-IDF/SVD text embeddings.
- Depressed/positive-label training subjects are augmented with the six fixed
  emotional-task permutations; validation subjects are not duplicated.
- Use fixed 5 seeds, 220 epochs, batch size 16,
  `AdamW(lr=1e-3, weight_decay=1e-4)`, train-target standardization, and
  prediction clipping to the train-split observed SDS range.
- Do not use validation/test labels for hyperparameter selection or checkpoint
  selection. Do not write checkpoints.
- Do not write raw text, raw audio, source paths, or file names to prediction
  outputs.

Audit summary:

- 162 subjects: 83 train and 79 validation.
- 790 prediction rows: 79 validation subjects x 5 seeds x 2 runs.
- 5 seeds: 0, 1, 2, 3, 4.
- 1000 subject-bootstrap resamples.
- Sequence length: 3 emotional tasks.
- Audio feature dimension: 88; text SVD dimension: 128; fused dimension: 216.
- No train/validation subject overlap.
- No test split used.
- Prediction artifacts do not write raw inputs or source paths.
- GRU mean metrics: CCC 0.0469, MAE 10.0271, RMSE 12.1576, Spearman 0.0289.
- BiLSTM mean metrics: CCC -0.0087, MAE 9.4927, RMSE 11.6008, Spearman
  -0.0785.

PDCH official split layer and public text-only wrapper:

```bash
python scripts/phase2_build_subject_splits.py
python scripts/phase2_run_pdch_public_llm.py --model-name /root/autodl-tmp/cache/modelscope/Qwen-Qwen2.5-7B-Instruct --local-files-only
python scripts/phase2_baseline_matrix.py --strict
```

Completed run:

- `pdch_public_text_only`

Protocol:

- Public source: `https://github.com/Miraclemarvel55/PDCH`, commit
  `01f429e0ca64482f684576d5ad22a106412898cc`.
- Paper/source page: `https://pmc.ncbi.nlm.nih.gov/articles/PMC12480040/`.
- The split layer now materializes the official PDCH
  `generate_sft_conversation.py` seed-0 bucket logic from `data_meta.json`.
- Four official subject-CV protocols are available:
  `pdch_hamd17_official_word_count_small_cv`,
  `pdch_hamd17_official_word_count_big_cv`,
  `pdch_hamd17_official_imbalance_small_cv`, and
  `pdch_hamd17_official_imbalance_big_cv`.
- Each protocol writes only subject/fold/role metadata; no labels, paths, raw
  text, raw audio, or model outputs are written to the split artifact.
- The public text-only wrapper preserves the official HAMD-17 prompt and
  parsing contract, reads local `*_correction_timestamp_emotion.txt`
  transcripts, and writes only parsed factor scores plus total-score
  predictions.
- Default evaluation uses the official imbalance small+big validation folds,
  covering all 99 HAMD-labeled PDCH subjects exactly once per Phase 2 seed.
- Missing parsed HAMD item scores are treated as 0 in the total-score sum,
  matching the official evaluator's missing-score convention.
- The official deterministic generation behavior (`do_sample=False`) is kept by
  default; deterministic seed reuse is recorded when one generation is reused
  across the five Phase 2 seed slots.
- Raw transcript text, raw prompts, source paths, audio files, and raw model
  responses are not written to prediction artifacts.
- The completed run uses a local ModelScope/魔塔 snapshot of
  `Qwen/Qwen2.5-7B-Instruct` under
  `/root/autodl-tmp/cache/modelscope/Qwen-Qwen2.5-7B-Instruct`, loaded with
  `--local-files-only`.

Current status:

- Official split protocols are materialized and matrix validation recognizes
  `official_cv_available` for PDCH public rows.
- `pdch_public_text_only` is completed: 99 HAMD-labeled validation subjects,
  99 parsed factor rows, 495 five-seed prediction rows, 1000
  subject-bootstrap resamples, deterministic seed reuse from generation seed 0,
  and all 99 responses parsed all 17 HAMD factors.
- Mean text-only metrics: CCC 0.3340, MAE 6.2121, RMSE 7.8964, Spearman
  0.4078.
- `pdch_public_audio_text` is completed with the local ModelScope
  `Qwen/Qwen2-Audio-7B-Instruct` snapshot, official imbalance validation
  protocols, 3-minute context windows, 25-second clips, deterministic
  generation, and 1000 subject-bootstrap resamples.
- Mean audio-text metrics: CCC -0.0010, MAE 31.0707, RMSE 32.4106, Spearman
  -0.0828. This is a weak public reproduction baseline because only 46/99
  factor rows parsed all 17 HAMD factors.
- Prediction artifacts do not write raw transcript text, raw prompts, source
  paths, audio files, or raw model responses.

CMDC/PDCH text TF-IDF:

```bash
python scripts/phase2_run_cmdc_pdch_text_tfidf.py
python scripts/phase2_baseline_matrix.py --strict
```

Completed runs:

- `cmdc_text_binary_tfidf_logistic`
- `cmdc_text_phq9_tfidf_ridge`
- `pdch_text_hamd17_tfidf_ridge`

Protocol:

- Use manifest-resolved valid text paths and
  `datasets/splits/phase2_subject_splits.csv`.
- Aggregate valid text segments to one subject row in natural segment order.
- Evaluate generated subject-level CV protocols with 5 seeds.
- Use fixed baseline hyperparameters; do not tune on validation or test labels.
- Do not write raw text, source paths, or file names.

Audit summary:

- CMDC binary classification: 77 subjects.
- CMDC PHQ-9 regression: 77 subjects.
- PDCH HAMD-17 regression: 99 subjects.
- 5 seeds: 0, 1, 2, 3, 4.
- 1000 subject-bootstrap resamples.
- No train/validation subject overlap.
- No test split used.
- Prediction artifacts do not write raw text or source paths.

CMDC/PDCH frozen text encoder MLP:

```bash
python scripts/phase2_run_cmdc_pdch_text_encoder_mlp.py --local-files-only
python scripts/phase2_baseline_matrix.py --strict
```

Completed runs:

- `cmdc_text_phq9_encoder_mlp`
- `pdch_text_hamd17_encoder_mlp`

Protocol:

- Use manifest-resolved valid text paths and generated subject-level split
  protocols.
- Encoder: frozen `BAAI/bge-small-zh-v1.5`; no encoder parameters are updated.
- Segment embedding: extract normalized CLS embeddings per text segment. Long
  segments are split into 512-token windows and token-count-weighted averaged.
- Subject embedding: average valid segment embeddings per subject.
- Regression head: fixed MLPRegressor with one hidden layer of 64 units,
  `alpha=0.01`, `solver=lbfgs`, and `max_iter=2000`.
- Regression outputs are clipped to the train-split observed target range.
- Do not use validation/test labels for encoder extraction or hyperparameter
  selection.
- Do not use a test split.
- Do not write raw text, source paths, or file names.

Audit summary:

- CMDC PHQ-9 regression: 77 subjects, 908 text segments, 512 embedding
  features, 385 prediction rows.
- PDCH HAMD-17 regression: 99 subjects, 165 text segments, 512 embedding
  features, 495 prediction rows.
- 5 seeds: 0, 1, 2, 3, 4.
- 1000 subject-bootstrap resamples.
- CMDC mean metrics: CCC 0.6868, MAE 3.8749, RMSE 5.3764, Spearman 0.5538.
- PDCH mean metrics: CCC 0.1200, MAE 6.8836, RMSE 9.0526, Spearman 0.1900.
- Prediction and feature artifacts do not write raw text or source paths.

CMDC audio eGeMAPS:

```bash
python scripts/phase2_run_cmdc_pdch_audio_egemaps.py --run-id cmdc_audio_binary_egemaps_svm
python scripts/phase2_baseline_matrix.py --strict
```

Completed run:

- `cmdc_audio_binary_egemaps_svm`

Protocol:

- Use manifest-resolved valid audio paths and
  `datasets/splits/phase2_subject_splits.csv`.
- Extract openSMILE eGeMAPSv02 functionals.
- Aggregate segment-level eGeMAPS functionals to one subject row with mean,
  std, min, and max.
- Evaluate generated subject-level CV protocols with 5 seeds.
- Use fixed SVM hyperparameters; do not tune on validation or test labels.
- Do not write raw audio, source paths, or file names.

Audit summary:

- CMDC binary classification: 77 subjects and 908 valid audio segments.
- 352 aggregate eGeMAPS feature columns plus subject metadata.
- 5 seeds: 0, 1, 2, 3, 4.
- 1000 subject-bootstrap resamples.
- No train/validation subject overlap.
- No test split used.
- Prediction and feature artifacts do not write raw audio or source paths.

CMDC frozen audio encoders:

```bash
python scripts/phase2_run_cmdc_audio_frozen_encoders.py --local-files-only
python scripts/phase2_baseline_matrix.py --strict
```

Completed runs:

- `cmdc_audio_binary_wavlm_linear`
- `cmdc_audio_binary_wav2vec2_linear`

Protocol:

- Use manifest-resolved valid CMDC audio paths and
  `cmdc_binary_subject_cv`.
- Encoders: frozen `microsoft/wavlm-base-plus` and frozen
  `facebook/wav2vec2-base`; no encoder parameters are updated.
- Segment embedding: split audio into fixed-duration chunks, mean-pool last
  hidden states, and duration-weight chunk embeddings per segment.
- Very short tail chunks created by fixed 20-second splitting are zero-padded
  to a 1-second minimum before encoder inference; duration weighting still uses
  the original unpadded duration.
- Subject embedding: average valid question-level segment embeddings per
  subject.
- Linear head: fixed LogisticRegression with balanced class weights.
- Evaluate generated subject-level CV with 5 seeds.
- Do not use validation/test labels for encoder extraction or hyperparameter
  selection.
- Do not use a test split.
- Do not write raw audio, source paths, or file names.

Audit summary:

- 77 split subjects and 908 valid audio segments.
- 908 segment embedding rows and 77 subject feature rows per encoder.
- 768 feature columns per encoder.
- 770 prediction rows total: 385 rows per run.
- 5 seeds: 0, 1, 2, 3, 4.
- 1000 subject-bootstrap resamples.
- WavLM mean metrics: Macro-F1 1.0000, Balanced Accuracy 1.0000, AUROC
  1.0000, AUPRC 1.0000, ECE 0.0120, Brier Score 0.0018.
- wav2vec2 mean metrics: Macro-F1 0.9704, Balanced Accuracy 0.9704, AUROC
  0.9962, AUPRC 0.9933, ECE 0.0250, Brier Score 0.0238.
- These very high CMDC audio scores should be treated as an RQ2 shortcut-risk
  signal until interviewer-question, question-position, and protocol controls
  are run.
- Prediction and feature artifacts do not write raw audio or source paths.

PDCH frozen WavLM audio:

```bash
python scripts/phase2_run_pdch_audio_wavlm.py --local-files-only
python scripts/phase2_baseline_matrix.py --strict
```

Completed run:

- `pdch_audio_hamd17_wavlm_linear`

Protocol:

- Use manifest-resolved valid PDCH audio paths and
  `pdch_hamd17_subject_cv_fallback`.
- Encoder: frozen `microsoft/wavlm-base-plus`; no WavLM parameters are updated.
- Segment embedding: split audio into fixed-duration chunks, mean-pool WavLM
  last hidden states, and duration-weight chunk embeddings per segment.
- Very short tail chunks are zero-padded to a 1-second minimum before encoder
  inference; duration weighting still uses the original unpadded duration.
- Subject embedding: average valid segment embeddings per subject.
- Linear head: Ridge regression with alpha selected only inside the train split
  by inner 5-fold OOF MAE.
- Regression outputs are clipped to the train-split observed target range.
- Do not use validation/test labels for encoder extraction or hyperparameter
  selection.
- Do not use a test split.
- Do not write raw audio, source paths, or file names.

Audit summary:

- 99 subjects and 165 valid audio segments.
- 49.3666 audio hours, 8938 WavLM chunks, and 11 padded short tail chunks.
- 165 segment embedding rows and 99 subject feature rows.
- 768 WavLM feature columns.
- 495 prediction rows: 99 subjects per seed over 5 seeds.
- 1000 subject-bootstrap resamples.
- Mean metrics: CCC 0.0575, MAE 6.3263, RMSE 7.9023, Spearman 0.1730.
- Prediction and feature artifacts do not write raw audio or source paths.

PDCH audio/text late fusion:

```bash
python scripts/phase2_run_pdch_audio_text_late_fusion.py
python scripts/phase2_baseline_matrix.py --strict
```

Completed run:

- `pdch_audio_text_hamd17_late_fusion`

Protocol:

- Use audited out-of-fold predictions from `pdch_text_hamd17_tfidf_ridge` and
  `pdch_audio_hamd17_wavlm_linear`.
- Fusion rule: unweighted average of text and audio HAMD-17 predictions.
- Evaluate the already-aligned generated subject-level CV protocols with 5
  seeds.
- Do not learn fusion weights, tune on validation/test labels, or use a test
  split.
- Do not read or write raw text, raw audio, source paths, or file names.

Audit summary:

- PDCH HAMD-17 regression: 99 subjects.
- Text/audio prediction key alignment is complete over 495 rows.
- Label mismatches: 0.
- 5 seeds: 0, 1, 2, 3, 4.
- 1000 subject-bootstrap resamples.
- Mean metrics: CCC 0.0479, MAE 6.1000, RMSE 7.5281, Spearman 0.2292.
- Prediction artifacts do not write raw inputs or source paths.

PDCH audio eGeMAPS:

```bash
python scripts/phase2_run_cmdc_pdch_audio_egemaps.py
python scripts/phase2_baseline_matrix.py --strict
```

Completed run:

- `pdch_audio_hamd17_egemaps_svr`

Protocol:

- Use manifest-resolved valid PDCH audio paths and
  `pdch_hamd17_subject_cv_fallback`.
- Extract openSMILE eGeMAPSv02 functionals.
- Aggregate segment-level eGeMAPS functionals to one subject row with mean,
  std, min, and max.
- Evaluate generated subject-level CV protocols with 5 seeds.
- Use fixed linear SVR hyperparameters; regression outputs are clipped to the
  train-fold observed HAMD-17 target range.
- Do not tune on validation or test labels.
- Do not use a test split.
- Do not write raw audio, source paths, or file names.

Audit summary:

- 99 subjects and 165 valid audio segments totaling about 49.37 hours.
- 352 aggregate eGeMAPS feature columns plus subject metadata.
- 495 prediction rows: 99 subjects per seed over 5 seeds.
- 1000 subject-bootstrap resamples.
- Mean metrics: CCC 0.1688, MAE 8.6755, RMSE 11.1108, Spearman 0.1742.
- Prediction and feature artifacts do not write raw audio or source paths.

MODMA audio eGeMAPS:

```bash
python scripts/phase2_run_modma_audio_egemaps.py
python scripts/phase2_baseline_matrix.py --strict
```

Completed run:

- `modma_audio_binary_egemaps_svm`

Protocol:

- Use manifest-resolved valid MODMA audio paths and
  `datasets/splits/phase2_subject_splits.csv`.
- Exclude the 5 manifest rows already marked invalid by audio decoding.
- Extract openSMILE eGeMAPSv02 functionals.
- Aggregate all valid task segments per subject with mean, std, min, and max.
- Evaluate `modma_binary_subject_cv` with 5 seeds and subject-level outer CV.
- Use fixed linear SVM hyperparameters with balanced class weights.
- Do not tune on validation or test labels.
- Do not use a test split.
- Do not write raw audio, source paths, or file names.

Audit summary:

- 52 subjects and 1503 valid audio segments.
- 5 invalid audio rows excluded.
- 352 aggregate eGeMAPS feature columns.
- 260 prediction rows: 52 subjects per seed over 5 seeds.
- 5 subject-level folds and zero subject-overlap violations.
- 1000 subject-bootstrap resamples.
- Prediction and feature artifacts do not write raw audio or source paths.

MODMA frozen WavLM:

```bash
python scripts/phase2_run_modma_audio_wavlm.py --local-files-only
python scripts/phase2_baseline_matrix.py --strict
```

Completed runs:

- `modma_audio_binary_wavlm_linear`
- `modma_audio_phq9_wavlm_linear`
- `modma_audio_binary_task_specific_wavlm`
- `modma_audio_binary_cross_task_wavlm`

Protocol:

- Use manifest-resolved valid MODMA audio paths and generated subject-level
  split protocols.
- Encoder: frozen `microsoft/wavlm-base-plus`; no WavLM parameters are updated.
- Segment embedding: split audio into fixed-duration chunks, mean-pool WavLM
  last hidden states, and duration-weight chunk embeddings per segment.
- Subject embedding: average valid segment embeddings per subject.
- Subject-task embedding: average valid segment embeddings per subject and
  task.
- Linear heads: LogisticRegression for binary tasks and Ridge regression for
  PHQ-9 regression.
- PHQ-9 Ridge alpha is selected only inside the train split by inner 5-fold OOF
  MAE over a fixed grid.
- Regression outputs are clipped to the train-split observed target range.
- Evaluate subject CV, task-specific, and cross-task protocols with 5 seeds.
- Do not use validation/test labels for encoder extraction or hyperparameter
  selection.
- Do not use a test split.
- Do not write raw audio, source paths, or file names.

Audit summary:

- 52 subjects and 1503 valid audio segments.
- 1503 segment embedding rows, 52 subject feature rows, and 208 subject-task
  feature rows.
- 768 WavLM feature columns.
- 4680 prediction rows across 4 completed runs.
- Protocol coverage: 1 binary subject-CV protocol, 1 PHQ-9 subject-CV protocol,
  4 task-specific protocols, and 12 cross-task protocols.
- 5 seeds: 0, 1, 2, 3, 4.
- 1000 subject-bootstrap resamples.
- No test split used.
- Prediction and feature artifacts do not write raw audio or source paths.

MODMA frozen wav2vec2:

```bash
python scripts/phase2_run_modma_audio_wav2vec2.py --local-files-only
python scripts/phase2_baseline_matrix.py --strict
```

Completed run:

- `modma_audio_binary_wav2vec2_linear`

Protocol:

- Use manifest-resolved valid MODMA audio paths and
  `modma_binary_subject_cv`.
- Encoder: frozen `facebook/wav2vec2-base`; no encoder parameters are updated.
- Segment embedding: split audio into fixed-duration chunks, mean-pool last
  hidden states, and duration-weight chunk embeddings per segment.
- Subject embedding: average valid segment embeddings per subject.
- Linear head: fixed LogisticRegression with balanced class weights.
- Evaluate generated subject-level CV with 5 seeds.
- Do not use validation/test labels for encoder extraction or hyperparameter
  selection.
- Do not use a test split.
- Do not write raw audio, source paths, or file names.

Audit summary:

- 52 subjects and 1503 valid audio segments.
- 5 invalid audio rows excluded.
- 1503 segment embedding rows and 52 subject feature rows.
- 768 wav2vec2 feature columns.
- 260 prediction rows: 52 subjects per seed over 5 seeds.
- 1000 subject-bootstrap resamples.
- Mean metrics: Macro-F1 0.7242, Balanced Accuracy 0.7226, AUROC 0.7901,
  AUPRC 0.8355, ECE 0.2111, Brier Score 0.2067.
- Prediction and feature artifacts do not write raw audio or source paths.

CMDC video feature baselines:

```bash
python scripts/phase2_run_cmdc_video_features.py
python scripts/phase2_baseline_matrix.py --strict
```

Completed runs:

- `cmdc_video_binary_openface_mlp`
- `cmdc_video_binary_temporal_pooling`

Protocol:

- Use manifest-resolved CMDC video feature paths and
  `cmdc_binary_subject_cv`.
- OpenFace row: summarize frame-level `Q*.csv` OpenFace features per segment,
  average segment statistics per subject, then fit a fixed MLP classifier.
- Official visual row: load `Q*.npy` TimeSformer/Kinetics visual
  representations, pool question-level vectors per subject with mean, std,
  min, and max, then fit a fixed logistic head.
- Evaluate the generated subject-level CV protocols with 5 seeds, filtering
  each fold to subjects with `file_valid=true` video features.
- Do not use validation/test labels for hyperparameter selection.
- Do not use a test split.
- Do not write raw video, feature paths, source paths, or file names.

Audit summary:

- 44 valid video subjects and 519 valid video-question segments.
- OpenFace subject features: 2844 columns.
- Official visual temporal-pooling subject features: 3072 columns.
- 220 prediction rows per completed run: 44 subjects per seed over 5 seeds.
- 1000 subject-bootstrap resamples.
- OpenFace MLP mean metrics: Macro-F1 0.7536, Balanced Accuracy 0.7521,
  AUROC 0.7919, AUPRC 0.7971, ECE 0.2261, Brier Score 0.2069.
- Official visual temporal-pooling mean metrics: Macro-F1 0.9763, Balanced
  Accuracy 0.9722, AUROC 0.9936, AUPRC 0.9921, ECE 0.0317, Brier Score
  0.0251.
- The very high official visual score should be treated as an RQ2
  protocol/content shortcut-risk signal until question-position and
  interviewer-protocol controls are run.
- Prediction and feature artifacts do not write raw video or source paths.

CMDC audio/text late fusion:

```bash
python scripts/phase2_run_cmdc_audio_text_late_fusion.py
python scripts/phase2_baseline_matrix.py --strict
```

Completed run:

- `cmdc_audio_text_binary_late_fusion`

Protocol:

- Use audited out-of-fold predictions from `cmdc_text_binary_tfidf_logistic`
  and `cmdc_audio_binary_egemaps_svm`.
- Fuse by unweighted averaging of text and audio positive-class probabilities.
- Use threshold 0.5 for class labels.
- Evaluate the already-aligned generated subject-level CV protocols with 5
  seeds.
- Do not learn fusion weights, tune on validation/test labels, or use a test
  split.
- Do not read or write raw text, raw audio, source paths, or file names.

Audit summary:

- CMDC binary classification: 77 subjects.
- Text/audio prediction key alignment is complete over 385 rows.
- Label mismatches: 0.
- 5 seeds: 0, 1, 2, 3, 4.
- 1000 subject-bootstrap resamples.
- Prediction artifacts do not write raw inputs or source paths.

CMDC HAMD-17 audio/text late fusion:

```bash
python scripts/phase2_run_cmdc_audio_text_hamd17_late_fusion.py
python scripts/phase2_baseline_matrix.py --strict
```

Completed run:

- `cmdc_audio_text_hamd17_late_fusion`

Protocol:

- Use manifest-resolved CMDC text, cached subject-level eGeMAPS features, and
  `cmdc_hamd17_subject_cv`.
- Train fold-local internal components for audit: char 2-3 TF-IDF plus fixed
  Ridge regression for text, and cached eGeMAPSv02 subject features plus fixed
  linear SVR for audio.
- Fuse by unweighted averaging of text and audio HAMD-17 predictions.
- Clip regression outputs to the train-fold observed HAMD-17 target range.
- Do not learn fusion weights, tune on validation/test labels, or use a test
  split.
- Do not write raw text, raw audio, feature paths, source paths, or file names.

Audit summary:

- CMDC HAMD-17 regression: 25 subjects.
- 125 fusion prediction rows: 25 subjects per seed over 5 seeds.
- 250 internal component prediction rows for audit.
- 352 cached aggregate eGeMAPS feature columns.
- Text segment count range: 9 to 12; audio segment count range: 9 to 12.
- Text prediction clip count: 0; audio prediction clip count: 30.
- 1000 subject-bootstrap resamples.
- Mean metrics: CCC -0.2554, MAE 4.4314, RMSE 5.2512, Spearman -0.3571.
- Prediction artifacts do not write raw inputs or source paths.

CMDC audio/text early and gated fusion:

```bash
python scripts/phase2_run_cmdc_audio_text_simple_fusion.py
python scripts/phase2_baseline_matrix.py --strict
```

Completed runs:

- `cmdc_audio_text_binary_early_fusion`
- `cmdc_audio_text_binary_gated_fusion`

Protocol:

- Early Fusion uses manifest-resolved valid text and cached subject-level
  eGeMAPS features.
- Early Fusion fits fixed-hyperparameter logistic regression over concatenated
  train-fold TF-IDF and eGeMAPS features.
- Gated Fusion uses audited out-of-fold probabilities from
  `cmdc_text_binary_tfidf_logistic` and `cmdc_audio_binary_egemaps_svm`.
- Gated Fusion uses a fixed confidence-weighted probability average; no labels
  are used to learn fusion weights.
- Evaluate generated subject-level CV protocols with 5 seeds.
- Do not use a test split.
- Do not write raw text, raw audio, source paths, or file names.

Audit summary:

- CMDC binary classification: 77 subjects.
- Early/Gated prediction rows: 770 total, 385 per run.
- Gated text/audio prediction key alignment is complete.
- Gated label mismatches: 0.
- 5 seeds: 0, 1, 2, 3, 4.
- 1000 subject-bootstrap resamples.
- Prediction artifacts do not write raw inputs or source paths.

MPDD gait statistics:

```bash
python scripts/phase2_run_mpdd_gait_stats.py
python scripts/phase2_baseline_matrix.py --strict
```

Completed runs:

- `mpdd_gait_binary_stats_logistic`
- `mpdd_gait_binary_stats_xgboost`

Protocol:

- Use only manifest-resolved labeled train subjects with gait paths.
- Ignore unlabeled MPDD test rows.
- Evaluate with five repeated stratified 5-fold subject-level out-of-fold runs.
- Use fixed hyperparameters; do not tune on test.
- Do not write raw IMU arrays.

Audit summary:

- 175 labeled train subjects.
- 5 repeated stratified 5-fold subject-level out-of-fold runs.
- 1000 subject-bootstrap resamples.
- No test split used.
- Prediction artifacts do not write raw IMU arrays or source paths.

MPDD IMU temporal encoder:

```bash
python scripts/phase2_run_mpdd_imu_temporal.py
python scripts/phase2_baseline_matrix.py --strict
```

Completed run:

- `mpdd_gait_severity_imu_temporal_mlp`

Protocol:

- Use only manifest-resolved labeled train subjects with gait paths.
- Ignore unlabeled MPDD test rows.
- Evaluate with five repeated stratified 5-fold subject-level out-of-fold runs.
- Use a shallow Conv1d temporal encoder plus MLP ordinal classifier.
- Use fixed hyperparameters; do not tune on test.
- Do not write checkpoints or raw IMU arrays.

Audit summary:

- 175 labeled train subjects.
- 5 repeated stratified 5-fold subject-level out-of-fold runs.
- 1000 subject-bootstrap resamples.
- No test split used.
- No checkpoints written.
- Prediction artifacts do not write raw IMU arrays or source paths.

MPDD frozen WavLM audio:

```bash
python scripts/phase2_run_mpdd_audio_wavlm.py --local-files-only
python scripts/phase2_baseline_matrix.py --strict
```

Completed runs:

- `mpdd_audio_phq9_wavlm_linear`
- `mpdd_audio_severity_wavlm_mlp`

Protocol:

- Use only manifest-resolved labeled MPDD train audio subjects.
- Ignore unlabeled MPDD test rows.
- Encoder: frozen `microsoft/wavlm-base-plus`; no WavLM parameters are
  updated.
- Segment embedding: split audio into fixed-duration chunks, mean-pool WavLM
  last hidden states, and duration-weight chunk embeddings per segment.
- Subject embedding: average valid audio-task segment embeddings per subject.
- PHQ-9 row: Ridge regression with alpha selected only inside each train fold
  by inner 5-fold OOF MAE.
- Severity row: fixed one-hidden-layer MLP classifier over frozen subject
  embeddings.
- Evaluate with five repeated stratified 5-fold subject-level out-of-fold
  runs.
- Clip PHQ-9 regression outputs to the train-fold observed target range.
- Do not use validation/test labels for encoder extraction or hyperparameter
  selection.
- Do not write raw audio, source paths, or checkpoints.

Audit summary:

- 175 labeled audio subjects: 87 elder and 88 young.
- Severity labels: 104 class 0, 50 class 1, and 21 class 2 subjects.
- 602 valid audio segments totaling 7.8738 hours.
- 1710 WavLM chunks and 16 padded short chunks.
- 768 WavLM feature columns.
- 875 prediction rows per completed run: 175 subjects per seed over 5 seeds.
- 1000 subject-bootstrap resamples.
- PHQ-9 clip count: 7.
- PHQ-9 mean metrics: CCC 0.0597, MAE 3.1409, RMSE 4.2220, Spearman 0.1430.
- Severity mean metrics: QWK 0.0882, Ordinal MAE 0.6069, Macro-F1 0.3703,
  ECE 0.4463, Brier Score 0.9217.
- Prediction and feature artifacts do not write raw audio or source paths, and
  no checkpoints are written.
