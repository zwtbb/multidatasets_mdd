# Phase 2 统一基线中文复现说明

本文档用于复现 `/root/autodl-tmp` 中的多模态抑郁检测 Phase 2 统一基线实验。它面向两种场景：

- 在当前服务器上核验已有产物是否满足论文复现实验契约。
- 在同样数据、同样模型缓存、同样脚本版本下，从头重新生成审计、split、基线结果和统一矩阵。

当前文档快照日期：2026-07-30 UTC。当前统一矩阵状态为 67 个计划 run，其中 65 个已完成，2 个仍由明确前置条件阻塞。

## 1. 复现范围

Phase 2 的目标不是提出新结构，而是在进入方法设计前冻结并填充一个可信、可重复、可比较的统一 baseline matrix。

核心研究约束如下：

- 所有实验必须以 subject-level split 为单位，不能把同一被试的 segment、task、session 或 modality 分到不同集合。
- 训练入口必须来自 `datasets/registry.yaml` 和 `datasets/manifests/*_subjects.csv|parquet`，不能临时扫描原始目录直接训练。
- 至少使用 5 个随机种子：`0, 1, 2, 3, 4`。
- 使用 1000 次 subject bootstrap 估计 95% 置信区间。
- 不允许用 test label 做调参、模型选择或融合权重选择。
- 预训练 text/audio encoder 在 Phase 2 默认冻结。
- Phase 2 禁止引入 hypergraph、causal module、LLM summary、contrastive learning、personality gating、weak summary supervision，以及默认全量微调大编码器。

统一指标：

- 二分类：Macro-F1、Balanced Accuracy、AUROC、AUPRC、ECE、Brier Score。
- 严重程度回归：CCC、MAE、RMSE、Spearman。
- 有序等级预测：QWK、Ordinal MAE、Macro-F1、ECE、Brier Score。

## 2. 目录约定

在所有命令中，默认工作目录都是：

```bash
cd /root/autodl-tmp
```

关键路径：

| 路径 | 作用 |
| --- | --- |
| `MEMORY.md` | 跨会话实验记忆和最新状态摘要。新会话开始前必须完整阅读。 |
| `datasets/registry.yaml` | 数据集路径、角色、标签、协议、模态和状态的单一事实源。 |
| `datasets/manifests/` | 训练和审计脚本读取的 subject/segment 级 manifest。 |
| `datasets/audit/` | 数据审计输出，包括 inventory、label distribution、file integrity、leakage check。 |
| `datasets/splits/phase2_subject_splits.csv` | CMDC、PDCH、MODMA 等生成式 subject split 层。 |
| `baselines/phase2_baseline_matrix.yaml` | Phase 2 计划 run、指标、策略和 blocker 的机器可读契约。 |
| `analysis/phase2_baselines/` | 各 baseline 的预测、metric-by-seed、metric-summary、run-summary 和报告。 |
| `cache/official_baselines/` | 官方 baseline 仓库缓存。 |
| `cache/huggingface/` | Hugging Face 模型缓存。 |
| `cache/modelscope/` | ModelScope/魔塔模型缓存，尤其是 Qwen 系列。 |

当前本地大目录规模约为：

- `datasets/`：约 277 GB。
- `analysis/`：约 60 GB。
- `cache/`：约 38 GB。

原始数据、音频、视频、大特征、模型权重和运行缓存不应进入 Git。

## 3. 数据准备

本仓库不把原始临床数据和大模型权重纳入 Git。因此从零复现前，需要先获得相应数据集授权，并按当前 registry 所期望的布局放到本地。

当前审计识别的数据集如下：

| Dataset | 角色 | 状态 | Subjects | Segments | Valid rows | 主标签 | 协议 |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| E-DAIC | primary development | uploaded_official | 275 | 275 | 275 | PHQ-8 | virtual interview |
| CMDC | Chinese cross-protocol validation | uploaded_official | 78 | 936 | 908 | PHQ-9 / HAMD-17 | clinical interview |
| PDCH | hospital HAMD validation | uploaded_extracted | 100 | 167 | 165 | HAMD-17 | face-to-face consultation |
| MODMA | controlled speech-task stress test | uploaded_official_with_invalid_files | 52 | 1508 | 1503 | diagnosis / PHQ-9 | interview / reading / picture |
| EATD-Corpus | Chinese valence stress test | uploaded_official | 162 | 486 | 486 | SDS | positive / neutral / negative tasks |
| MPDD-AVG-2026 | individual-difference and gait validation | uploaded_official_with_label_gaps | 224 | 772 | 602 | PHQ-9 | age / personality / gait / multimodal |

重要数据质量说明：

- E-DAIC 是主开发集，官方 split 为 163 train、56 dev、56 test；Phase 2 只用 train/dev，不用 test。
- E-DAIC subject `657` 缺少 `657_CNN_VGG.mat` 是官方 AVEC/E-DAIC feature release 的已知遗漏，不要伪造或用本地修复替代。
- CMDC `MDD21` 在部分二分类 split 中因 `file_valid=false` 被排除。
- PDCH subject `034A` 有音频/文本但无 HAMD 标注，标为 `missing_label`。
- MODMA 有 5 个不可解码 WAV：`02010004/24.wav` 至 `02010004/28.wav`。
- MPDD-AVG-2026 的 young/elder 数字 ID 有重叠，manifest 使用 `young_*` 和 `elder_*` 前缀避免被误判为同一 subject。

## 4. 环境准备

当前已验证环境：

| 项 | 当前值 |
| --- | --- |
| OS | Ubuntu 22.04 风格服务器环境 |
| Python | 3.12.3 |
| GPU | NVIDIA GeForce RTX 4080 SUPER, 32760 MiB |
| Driver | 580.76.05 |
| PyTorch | 2.8.0+cu128 |
| Transformers | 5.3.0 |
| NumPy | 2.3.2 |
| pandas | 3.0.5 |
| scikit-learn | 1.8.0 |
| SciPy | 1.17.1 |
| pyarrow | 25.0.0 |
| opensmile | 2.6.0 |
| librosa | 0.11.0 |
| soundfile | 0.13.1 |
| xgboost | 3.2.0 |
| openpyxl | 3.1.5 |

本仓库当前没有锁定的 `requirements.txt` 或 `pyproject.toml`。如果需要在新环境中配置，建议先使用带 CUDA 的 PyTorch 镜像，再安装脚本实际依赖：

```bash
python -m pip install -U pip
python -m pip install numpy pandas pyarrow pyyaml scikit-learn scipy soundfile librosa opensmile xgboost openpyxl transformers accelerate sentencepiece protobuf
```

如果当前镜像没有 GPU 版 PyTorch，请按目标 CUDA 版本安装对应 PyTorch。不要随意更换 major 版本后直接宣称可复现；至少要重新运行第 9 节的核验步骤。

建议统一设置缓存和线程环境：

```bash
export PYTHONPATH=/root/autodl-tmp/scripts:${PYTHONPATH:-}
export HF_HOME=/root/autodl-tmp/cache/huggingface
export TRANSFORMERS_CACHE=/root/autodl-tmp/cache/huggingface
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
```

Qwen 系列建议优先使用 ModelScope/魔塔本地缓存：

- 文本模型：`/root/autodl-tmp/cache/modelscope/Qwen-Qwen2.5-7B-Instruct`
- 音频文本模型：`/root/autodl-tmp/cache/modelscope/Qwen-Qwen2-Audio-7B-Instruct`

冻结 encoder 可通过 Hugging Face 缓存或在线下载：

- `microsoft/wavlm-base-plus`
- `facebook/wav2vec2-base`
- `microsoft/deberta-v3-base`
- `answerdotai/ModernBERT-base`
- `sentence-transformers/all-MiniLM-L6-v2`
- `sentence-transformers/all-distilroberta-v1`
- `BAAI/bge-small-zh-v1.5`

在正式复现实验中，如果模型已缓存，优先使用 `--local-files-only` 固定模型来源；如果首次下载，可先去掉该参数完成缓存，再记录模型来源和 revision。

## 5. 快速核验已有产物

如果只是确认当前 workspace 的可复现状态，不需要重新训练所有模型，运行：

```bash
python scripts/phase2_metrics.py --self-test
python scripts/phase2_build_subject_splits.py
python scripts/phase2_baseline_matrix.py --strict
```

可选的快速数据审计：

```bash
python scripts/audit_datasets.py --skip-audio-decode
```

完整数据审计会读取音频可用性，耗时更长：

```bash
python scripts/audit_datasets.py
```

核验成功后重点查看：

```bash
sed -n '1,120p' analysis/phase2_baselines/baseline_matrix_summary.md
sed -n '1,120p' analysis/phase2_baselines/phase2_subject_splits_report.md
sed -n '1,120p' datasets/audit/dataset_inventory.md
```

当前期望结果：

- `phase2_metrics.py --self-test` 通过。
- `phase2_build_subject_splits.py` 生成 11220 行 split，42 个 protocol，subject overlap violations 为 0。
- `phase2_baseline_matrix.py --strict` 通过 config validation。
- 统一矩阵 planned runs 为 67，completed 为 66，not_applicable 为 1，blocked 为 0。
- 已加载 completed metric rows 为 313；P3HF 的 5 个 metric rows 作为条件性排除保留在 audit 表里，不进入核心结果表。

当前条件性排除：

| run_id | 原因 |
| --- | --- |
| `mpdd_public_p3hf` | `compatibility_gate_not_applicable`：P3HF packaged Young-only split/features/evaluation contract 与当前 175-subject MPDD Phase 2 matrix 不匹配 |

## 6. 从零复现的总顺序

正式复现建议按以下顺序执行。每完成一个 block 后都运行一次矩阵严格校验，尽早发现缺失 metric、seed 或 bootstrap 设置。

```bash
python scripts/audit_datasets.py
python scripts/phase2_build_subject_splits.py
python scripts/phase2_metrics.py --self-test
python scripts/phase2_baseline_matrix.py --strict
```

然后依次跑各数据集 baseline：

1. E-DAIC 单模态和融合。
2. E-DAIC 公开复现：AVEC DDS、QuestMF。
3. EATD 单模态、融合、公开 GRU/BiLSTM 风格复现。
4. CMDC/PDCH 的 text/audio/video/simple fusion 和 PDCH 公开复现。
5. MODMA task-specific 与 cross-task 音频 baseline。
6. MPDD audio/video/gait/AVP baseline。
7. 最后再次运行 `python scripts/phase2_baseline_matrix.py --strict`，确认矩阵状态。

## 7. 数据审计与 split 复现

生成 manifest 和审计产物：

```bash
python scripts/audit_datasets.py
```

输出文件：

- `datasets/manifests/edaic_subjects.csv`
- `datasets/manifests/cmdc_subjects.csv`
- `datasets/manifests/pdch_subjects.csv`
- `datasets/manifests/modma_subjects.csv`
- `datasets/manifests/eatd_subjects.csv`
- `datasets/manifests/mpdd_avg_2026_subjects.csv`
- 同名 `.parquet`
- `datasets/audit/dataset_inventory.md`
- `datasets/audit/label_distribution.csv`
- `datasets/audit/file_integrity.csv`
- `datasets/audit/file_integrity_summary.csv`
- `datasets/audit/leakage_check.md`

生成 Phase 2 subject split 层：

```bash
python scripts/phase2_build_subject_splits.py
```

输出文件：

- `datasets/splits/phase2_subject_splits.csv`
- `analysis/phase2_baselines/phase2_subject_splits_summary.json`
- `analysis/phase2_baselines/phase2_subject_splits_report.md`

严格校验 baseline matrix：

```bash
python scripts/phase2_baseline_matrix.py --strict
```

输出文件：

- `analysis/phase2_baselines/baseline_matrix_template.csv`
- `analysis/phase2_baselines/baseline_matrix_status.csv`
- `analysis/phase2_baselines/baseline_matrix_manifest_summary.json`
- `analysis/phase2_baselines/baseline_matrix_summary.md`

## 8. Baseline 复现命令

### 8.1 E-DAIC

E-DAIC text TF-IDF：

```bash
python scripts/phase2_run_edaic_text_tfidf.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `edaic_text_phq8_tfidf_ridge`
- `edaic_text_binary_tfidf_logistic`

E-DAIC frozen text encoder：

```bash
python scripts/phase2_run_edaic_text_encoders.py --chunk-batch-size 16
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `edaic_text_phq8_deberta_mlp`
- `edaic_text_phq8_modernbert_mlp`

E-DAIC sentence attention text：

```bash
python scripts/phase2_run_edaic_text_sentence_attention.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `edaic_text_phq8_sentence_attention`

E-DAIC audio eGeMAPS：

```bash
python scripts/phase2_run_edaic_audio_egemaps.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `edaic_audio_phq8_egemaps_svr`
- `edaic_audio_binary_egemaps_svm`

E-DAIC frozen audio encoders：

```bash
python scripts/phase2_run_edaic_audio_frozen_encoders.py --local-files-only --chunk-batch-size 8
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `edaic_audio_phq8_wavlm_linear`
- `edaic_audio_phq8_wavlm_mlp`
- `edaic_audio_phq8_wav2vec2_linear`
- `edaic_audio_phq8_wav2vec2_mlp`

E-DAIC video features：

```bash
python scripts/phase2_run_edaic_video_features.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `edaic_video_phq8_openface_mlp`
- `edaic_video_phq8_official_temporal_pooling`

E-DAIC audio/video/text fusion：

```bash
python scripts/phase2_run_edaic_av_fusion.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `edaic_av_phq8_early_fusion`
- `edaic_av_phq8_late_fusion`
- `edaic_av_phq8_gated_fusion`

注意：fusion 依赖前面已审计的 text/audio/video 预测或缓存。Late Fusion 使用已完成的 dev predictions；Gated Fusion 的权重来自 train-only OOF inverse MAE，不用 dev/test label 学权重。

E-DAIC existing local baselines：

```bash
python scripts/phase2_run_edaic_existing_baselines.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `edaic_existing_text_baseline`
- `edaic_existing_audio_baseline`
- `edaic_existing_late_fusion`

注意：该 block 注册的是当前 Phase 2 已审计本地组件，不是另一个外部 legacy 预测文件。

E-DAIC AVEC 2019 DDS public reproduction：

```bash
python scripts/phase2_run_edaic_public_avec.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `edaic_public_avec_official`

正式填矩阵条件：

- 10 个 DDS feature set 全部完成：`eGeMAPS`, `mfcc`, `AUpose`, `BoW_AUpose`, `BoW_eGeMAPS`, `BoW_mfcc`, `DS_VGG`, `DS_densenet`, `ResNet`, `VGG`。
- seeds 为 `0 1 2 3 4`。
- epochs 为 30。
- batch size 为 15。
- bootstrap resamples 至少为 1000。

中断恢复默认启用 progress resume。如需单 feature 恢复：

```bash
python scripts/phase2_run_edaic_public_avec.py --feature-type mfcc --seeds 0 1 2 3 4 --long-sequence-mode native_packed
```

烟测命令不会填充正式矩阵：

```bash
python scripts/phase2_run_edaic_public_avec.py --out-dir /tmp/edaic_avec_smoke --feature-type DS_densenet --seeds 0 --epochs 1 --workers 0 --bootstrap-resamples 10 --log-every 1
```

E-DAIC QuestMF public reproduction：

```bash
python scripts/phase2_run_edaic_public_questmf.py --local-files-only
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `edaic_public_questmf`

正式设置为 8 个 PHQ-8 item、5 个 seed、10 个 unimodal epoch、20 个 fusion epoch、1000 bootstrap resamples。输出 item-level ordinal predictions，不写 raw transcript、audio、video frame、source path 或 checkpoint。

### 8.2 EATD-Corpus

EATD text TF-IDF：

```bash
python scripts/phase2_run_eatd_text_tfidf.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `eatd_text_sds_tfidf_ridge`
- `eatd_text_binary_tfidf_logistic`

EATD audio eGeMAPS：

```bash
python scripts/phase2_run_eatd_audio_egemaps.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `eatd_audio_sds_egemaps_svr`

EATD frozen WavLM：

```bash
python scripts/phase2_run_eatd_audio_wavlm.py --local-files-only
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `eatd_audio_binary_wavlm_linear`

EATD audio/text fusion：

```bash
python scripts/phase2_run_eatd_audio_text_fusion.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `eatd_audio_text_sds_early_fusion`
- `eatd_audio_text_sds_late_fusion`
- `eatd_audio_text_sds_gated_fusion`

EATD official GRU/BiLSTM-style public reproduction：

```bash
python scripts/phase2_run_eatd_public_gru_bilstm.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `eatd_public_gru`
- `eatd_public_bilstm`

注意：该公开复现保留官方 GRU/BiLSTM recurrent model family 和三情绪任务序列，但使用本项目审计后的 openSMILE eGeMAPSv02 与中文 char TF-IDF/SVD 特征接口，因为原官方特征栈依赖旧版本地环境和绝对路径。

### 8.3 CMDC 和 PDCH

运行 CMDC/PDCH 前必须先生成 split：

```bash
python scripts/phase2_build_subject_splits.py
```

CMDC/PDCH text TF-IDF：

```bash
python scripts/phase2_run_cmdc_pdch_text_tfidf.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `cmdc_text_binary_tfidf_logistic`
- `cmdc_text_phq9_tfidf_ridge`
- `pdch_text_hamd17_tfidf_ridge`

CMDC/PDCH frozen text encoder：

```bash
python scripts/phase2_run_cmdc_pdch_text_encoder_mlp.py --local-files-only
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `cmdc_text_phq9_encoder_mlp`
- `pdch_text_hamd17_encoder_mlp`

CMDC audio eGeMAPS：

```bash
python scripts/phase2_run_cmdc_pdch_audio_egemaps.py --run-id cmdc_audio_binary_egemaps_svm
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `cmdc_audio_binary_egemaps_svm`

PDCH audio eGeMAPS：

```bash
python scripts/phase2_run_cmdc_pdch_audio_egemaps.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `pdch_audio_hamd17_egemaps_svr`

CMDC frozen audio encoders：

```bash
python scripts/phase2_run_cmdc_audio_frozen_encoders.py --local-files-only
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `cmdc_audio_binary_wavlm_linear`
- `cmdc_audio_binary_wav2vec2_linear`

CMDC video features：

```bash
python scripts/phase2_run_cmdc_video_features.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `cmdc_video_binary_openface_mlp`
- `cmdc_video_binary_temporal_pooling`

CMDC binary audio/text late fusion：

```bash
python scripts/phase2_run_cmdc_audio_text_late_fusion.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `cmdc_audio_text_binary_late_fusion`

CMDC binary audio/text early 和 gated fusion：

```bash
python scripts/phase2_run_cmdc_audio_text_simple_fusion.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `cmdc_audio_text_binary_early_fusion`
- `cmdc_audio_text_binary_gated_fusion`

CMDC HAMD-17 audio/text late fusion：

```bash
python scripts/phase2_run_cmdc_audio_text_hamd17_late_fusion.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `cmdc_audio_text_hamd17_late_fusion`

PDCH frozen WavLM：

```bash
python scripts/phase2_run_pdch_audio_wavlm.py --local-files-only
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `pdch_audio_hamd17_wavlm_linear`

PDCH audio/text late fusion：

```bash
python scripts/phase2_run_pdch_audio_text_late_fusion.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `pdch_audio_text_hamd17_late_fusion`

PDCH public text-only LLM reproduction：

```bash
python scripts/phase2_run_pdch_public_llm.py --model-name /root/autodl-tmp/cache/modelscope/Qwen-Qwen2.5-7B-Instruct --local-files-only
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `pdch_public_text_only`

PDCH public audio/text Qwen2-Audio reproduction：

```bash
python scripts/phase2_run_pdch_public_audio_text.py --model-name /root/autodl-tmp/cache/modelscope/Qwen-Qwen2-Audio-7B-Instruct --local-files-only
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `pdch_public_audio_text`

音频文本公开复现正式填矩阵条件：

- 使用官方 imbalance validation protocols。
- context window 为 3 分钟。
- audio clip 最大 25 秒。
- 不使用 audio emotion 文本后缀。
- `do_sample=False`。
- deterministic seed reuse。
- 覆盖 99 个 HAMD-labeled subjects。
- bootstrap resamples 至少为 1000。

烟测命令不会填充正式矩阵：

```bash
python scripts/phase2_run_pdch_public_audio_text.py --model-name /root/autodl-tmp/cache/modelscope/Qwen-Qwen2-Audio-7B-Instruct --local-files-only --out-dir /tmp/pdch_public_audio_text_smoke --max-subjects 1 --max-chunks-per-subject 1 --bootstrap-resamples 10
```

PDCH audio-text 的解析 caveat：当前正式结果中只有 46/99 行解析出全部 17 个 HAMD factor，48/99 行解析 16 个 factor，5/99 行解析 15 个 factor；官方缺失因子计分约定会使总分偏高。因此该结果应作为弱公开复现 baseline，而不是 Qwen2-Audio 对 PDCH HAMD 可靠评分的证据。

### 8.4 MODMA

MODMA audio eGeMAPS：

```bash
python scripts/phase2_run_modma_audio_egemaps.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `modma_audio_binary_egemaps_svm`

MODMA frozen WavLM：

```bash
python scripts/phase2_run_modma_audio_wavlm.py --local-files-only
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `modma_audio_binary_wavlm_linear`
- `modma_audio_phq9_wavlm_linear`
- `modma_audio_binary_task_specific_wavlm`
- `modma_audio_binary_cross_task_wavlm`

如只复现单个 run，可使用：

```bash
python scripts/phase2_run_modma_audio_wavlm.py --local-files-only --run-id modma_audio_binary_cross_task_wavlm
```

MODMA frozen wav2vec2：

```bash
python scripts/phase2_run_modma_audio_wav2vec2.py --local-files-only
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `modma_audio_binary_wav2vec2_linear`

### 8.5 MPDD-AVG-2026

MPDD frozen WavLM audio：

```bash
python scripts/phase2_run_mpdd_audio_wavlm.py --local-files-only
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `mpdd_audio_phq9_wavlm_linear`
- `mpdd_audio_severity_wavlm_mlp`

MPDD ResNet video temporal pooling：

```bash
python scripts/phase2_run_mpdd_video_features.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `mpdd_video_severity_temporal_pooling`

MPDD OpenFace statistics + MLP：

```bash
python scripts/phase2_run_mpdd_video_features.py --run-id mpdd_video_severity_openface_mlp --force-features
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `mpdd_video_severity_openface_mlp`

服务器 MPDD OpenFace 已补齐：Elder train 338、Young train 264、Elder test
88、Young test 66，共 756 个 `.npy`，0 个 0 字节。Phase 2 OpenFace baseline
使用 175 个有标签 train subjects、602 个 train video events，并递归读取 Young
组 `subject/event_*/*.npy` 嵌套结构。

MPDD gait statistics：

```bash
python scripts/phase2_run_mpdd_gait_stats.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `mpdd_gait_binary_stats_logistic`
- `mpdd_gait_binary_stats_xgboost`

MPDD IMU temporal encoder：

```bash
python scripts/phase2_run_mpdd_imu_temporal.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `mpdd_gait_severity_imu_temporal_mlp`

MPDD AVP early/late/gated fusion：

```bash
python scripts/phase2_run_mpdd_avp_fusion.py
python scripts/phase2_baseline_matrix.py --strict
```

完成 run：

- `mpdd_avp_severity_early_fusion`
- `mpdd_avp_severity_late_fusion`
- `mpdd_avp_severity_gated_fusion`

MPDD 公开复现状态：

- `mpdd_public_official` 已完成，使用官方 MPDD baseline 的 A-V+P
  `bilstm_mean` 合同，并通过当前 175 个本地带标签 train subjects 的
  subject-level OOF 矩阵协议验收。
- 官方 README/代码的原始协议是 trainval workflow：从
  `split_labels_train.csv` 内部按默认 `val_ratio=0.1` 切 train/val，训练中
  按 val 指标选 checkpoint；`split_labels_test.csv` 只用于训练后的
  test-only evaluation。
- 当前 Phase 2 wrapper 为了和其他 MPDD train-only baseline 可比，将官方
  internal-val 逻辑放进每个外层 OOF train fold 内，并使用 deterministic
  inner split；外层 heldout/test label 不参与模型选择或早停。
- 本地官方代码 caveat：`train_val_split.py` 未向 sklearn splitter 传
  `random_state`，且 `train.py` 在 split 后才 `setup_seed`，所以原版
  train/val split 不由 `--seed` 固定。本地 Young train CSV 的 PHQ 列名也是
  `phq9_score`，而官方代码期待 `PHQ-9`；wrapper 通过 manifest 读取
  `phq9_total`。
- `mpdd_public_p3hf` 作为条件性排除保留在 audit 表中，不作为当前 canonical
  matrix row 复现。注意：P3HF 的 110 个 Young ID 与本地 raw Young `1..110`
  完全匹配；排除原因不是 ID 缺失，而是 P3HF 使用独立的 packaged feature、
  94/5/11 split、dev+test 合并评估和不同特征维度/环境合同，不满足“代码和
  输入特征与你的版本匹配”的前置条件。
- 官方 MPDD 当前材料已经记录 test label CSV，但本地
  `Test-MPDD-Young/split_labels_test.csv` 和
  `Test-MPDD-Elder/split_labels_test.csv` 尚未同步。若之后同步官方 gated
  release，应作为单独 test-only evaluation 协议处理，不能用 test label
  做调参或模型选择。

当前 Phase 2 已对所有适用行闭环；P3HF 只能作为单独标注的 packaged
Young-110 public reproduction 或新定义协议另行处理，不能静默填入当前
175-subject MPDD matrix。

## 9. 输出文件和验收标准

每个完成的 baseline block 一般会写出：

- `<block>_predictions.csv`：预测结果。正式产物不应含 raw text、raw audio/video、raw IMU、source path、file path 或 raw model response。
- `phase2_metrics_by_seed.csv`：每个 seed 的指标。
- `phase2_metric_summary.csv`：跨 seed 均值、标准差、bootstrap CI。
- `<block>_run_summary.json`：运行协议、样本量、seed、bootstrap、缓存和隐私审计字段。
- `<block>_report.md`：人类可读报告；不是所有 block 都一定有。

统一矩阵验收：

```bash
python scripts/phase2_baseline_matrix.py --strict
```

验收通过时：

- `analysis/phase2_baselines/baseline_matrix_summary.md` 中 `Config Validation` 为 passed。
- 已完成 run 的 `result_metric_count` 等于 `completed_metric_count`。
- 未完成 run 必须有明确 blocker，不能是 silent missing。
- `mean`, `std`, `ci95_low`, `ci95_high` 只在正式五 seed、subject bootstrap 产物存在时填写。

论文/附录用最终总表导出：

```bash
python scripts/phase2_export_final_table.py
```

验收产物：

- `analysis/phase2_baselines/final_table/phase2_final_baseline_table.csv`：核心七列 `数据集, 模态, 任务, 模型, 指标, 均值, 标准差`。
- `analysis/phase2_baselines/final_table/phase2_final_baseline_table_audit.csv`：在核心七列基础上增加 CI、seed、状态、run ID 和 blocker。
- `analysis/phase2_baselines/final_table/phase2_final_baseline_table.md`：Markdown 版本。
- `analysis/phase2_baselines/final_table/phase2_final_baseline_table_summary.json`：行数和空值审计。

Phase 2 完成度/进入方法设计 gate 审计：

```bash
python scripts/phase2_completion_audit.py
```

验收产物：

- `analysis/phase2_baselines/phase2_completion_audit/phase2_completion_audit.md`
- `analysis/phase2_baselines/phase2_completion_audit/phase2_completion_audit.json`

当前审计结论是：66/67 planned runs 已完成，1/67 为 P3HF 条件性排除，blocked runs 为 0；completed rows 均有 5 seeds 和 bootstrap CI。Phase 2 completion audit 应给出 `phase2_goal_complete=true` 和 `method_design_gate_recommendation=ready`。

subject split 验收：

```bash
python scripts/phase2_build_subject_splits.py
```

验收通过时：

- `analysis/phase2_baselines/phase2_subject_splits_report.md` 中 subject overlap violations 为 0。
- split 文件只包含 `dataset, protocol_id, protocol_type, target, fold, role, subject_id, train_task, eval_task, source`。
- split 文件不含标签列、路径列、raw 输入或模型输出。

数据审计验收：

```bash
python scripts/audit_datasets.py
```

验收通过时：

- `datasets/audit/leakage_check.md` 未报告 subject-level leakage。
- `datasets/audit/dataset_inventory.md` 中数据集 subject/segment/valid row 计数与当前快照一致，或差异能由新数据版本解释并记录。

## 10. 运行耗时和缓存建议

轻量 CPU 块：

- TF-IDF 文本 baseline。
- 已有预测的 late fusion。
- baseline matrix 校验。
- metric self-test。

中等耗时块：

- openSMILE eGeMAPS 提取。
- video feature pooling。
- MPDD gait statistics。
- EATD GRU/BiLSTM-style public reproduction。

GPU/长耗时块：

- WavLM/wav2vec2 frozen embedding 提取。
- E-DAIC text encoders。
- E-DAIC sentence attention。
- E-DAIC QuestMF。
- E-DAIC AVEC DDS，尤其是 `eGeMAPS` 和 `mfcc` 长序列 GRU。
- PDCH Qwen2.5 text-only 和 Qwen2-Audio audio/text 公开复现。

缓存策略：

- 对 frozen audio/text encoder，如果已经有完整 embedding cache，不要加 `--force-embeddings`。
- 对 feature extraction，如果只是复核矩阵，不要加 `--force-features`。
- 对 LLM 公开复现，如果已有正式 generations，不要加 `--force-generations`。
- 长任务建议先用 `/tmp/...` 或自定义 `--out-dir` 做 smoke，确认能跑通后再用默认正式输出目录。

## 11. 常见问题

### 11.1 `--local-files-only` 找不到模型

说明模型缓存不存在或路径不匹配。处理方式：

- 如果是 Hugging Face encoder，首次运行可以去掉 `--local-files-only` 让脚本下载。
- 如果是 Qwen 系列，优先从 ModelScope/魔塔下载到 `cache/modelscope/` 中的固定路径。
- 下载后重新使用 `--local-files-only` 进行正式复现，并在 run summary 或实验记录中写明模型来源。

### 11.2 AVEC 长序列 GRU CUDA 报错

使用默认 `--long-sequence-mode native_packed`。这个模式保留官方 packed-sequence GRU 语义，只在超出 cuDNN packed-sequence 限制时禁用 cuDNN，是运行兼容性处理，不是模型结构修改。

可选模式：

- `native_packed`：推荐正式设置。
- `padded`：使用 padded cuDNN 路径并取最后有效 step。
- `auto`：先尝试 padded，cuDNN 拒绝后回退 native packed。

### 11.3 重新跑后矩阵没有填充

检查对应 block 是否写出了 `phase2_metric_summary.csv`。很多公开复现脚本只有满足正式 contract 才写该文件；smoke 或 subset run 会写 partial 文件，故不会填充矩阵。

### 11.4 指标不同但脚本没报错

优先检查：

- seed 是否为 `0 1 2 3 4`。
- bootstrap resamples 是否为 1000。
- 是否使用了默认 split 或官方 split。
- 是否误加 `--force-*` 导致缓存重建且依赖版本不同。
- 是否使用 validation/test label 做了调参。
- 是否改变了模型来源、revision、chunk 长度、batch size 或 long-sequence mode。

### 11.5 CMDC audio/video 指标异常高

当前 CMDC audio-only 和 official visual temporal-pooling 分数很高，应视为 RQ2 protocol/content shortcut 风险信号。不要把它直接解释为跨协议泛化能力强；后续需要 interviewer question、question position、protocol control 等控制实验。

## 12. 最终复现报告应包含的材料

一次完整复现完成后，建议至少归档以下轻量文件：

- `datasets/audit/dataset_inventory.md`
- `datasets/audit/label_distribution.csv`
- `datasets/audit/file_integrity_summary.csv`
- `datasets/audit/leakage_check.md`
- `analysis/phase2_baselines/phase2_subject_splits_report.md`
- `analysis/phase2_baselines/baseline_matrix_summary.md`
- `analysis/phase2_baselines/baseline_matrix_status.csv`
- 每个完成 block 的 `phase2_metric_summary.csv`
- 每个完成 block 的 `phase2_metrics_by_seed.csv`
- 每个完成 block 的 `*_run_summary.json`

不要归档或提交：

- 原始临床文本、音频、视频、IMU arrays。
- 模型权重。
- 大型 embedding/feature cache。
- LLM raw prompts、raw model responses。
- 带有 source path 或 file path 的中间私有文件。

## 13. 当前快照的完成度摘要

| Dataset | 完成情况 |
| --- | --- |
| E-DAIC | 21/21 planned runs completed，包括 AVEC official 和 QuestMF。 |
| CMDC | 12/12 planned runs completed。 |
| PDCH | 7/7 planned runs completed，包括 text-only 和 audio-text public reproduction。 |
| EATD-Corpus | 9/9 planned runs completed。 |
| MODMA | 6/6 planned runs completed。 |
| MPDD-AVG-2026 | 11/12 planned runs completed；P3HF 条件性排除。 |

最终矩阵命令：

```bash
python scripts/phase2_baseline_matrix.py --strict
```

当前期望摘要：

- Planned runs: `67`
- Completed runs: `66`
- Not-applicable runs: `1`
- Planned blocked by prerequisites: `0`
- Completed metric rows loaded: `313`
- Config validation: passed

只要这四项与当前快照一致，且 split/audit 无 leakage，即可认为当前 Phase 2 复现产物与本说明匹配。
