# MV25 Provenance and Controlled Corpus Identity

Generated: `2026-08-27T11:14:44+00:00`

## DAIC-WOZ / E-DAIC Role

DAIC-WOZ/E-DAIC is retained as a same-lineage PHQ-8 sanity control, not as an independent corpus. The local DAIC-WOZ materialization is symlinked into the E-DAIC extracted data tree, and the complete item-labeled DAIC-WOZ train/dev rows overlap the E-DAIC train/dev label rows.

| scope | overlap n | exact item match | mean abs item diff | paper role |
| --- | ---: | ---: | ---: | --- |
| train/dev PHQ-8 shared items | 141 | 0.993 | 0.007 | same-lineage sanity control |

## Controlled Corpus-Identity Probes

Each probe uses subject-level frozen foundation features and a fold-internal identity classifier. For controlled rows, length and/or severity are residualized inside each training fold before held-out evaluation.

| probe | view | source n | target n | raw BA | length+severity BA | drop |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| cmdc_pdch_qwen3_text_same_language_hamd | qwen3_text | 25 | 99 | 1.000 | 0.572 | 0.428 |
| cmdc_pdch_wavlm_audio_same_language_hamd | wavlm_audio | 25 | 99 | 1.000 | 0.541 | 0.459 |
| edaic_internal_openface_video_lineage | openface_video_common | 189 | 30 | 0.601 | 0.599 | 0.002 |
| edaic_internal_qwen3_text_lineage | qwen3_text | 189 | 30 | 0.840 | 0.839 | 0.001 |
| edaic_internal_wavlm_audio_lineage | wavlm_audio | 189 | 30 | 0.907 | 0.897 | 0.010 |
| edaic_cmdc_openface_video_nontext | openface_video_common | 219 | 44 | 1.000 | 0.522 | 0.478 |
| edaic_cmdc_qwen3_text_cross_language | qwen3_text | 219 | 77 | 1.000 | 0.497 | 0.503 |
| edaic_cmdc_wavlm_audio_nontext | wavlm_audio | 219 | 77 | 1.000 | 0.484 | 0.516 |

## Interpretation Handle

The cross-language E-DAIC/CMDC 1.000 identity score is no longer asked to carry the corpus-identity claim alone, because length/protocol controls explain much of that raw separability. The stronger manuscript evidence comes from the same-language lineage probes: E-DAIC remains identifiable within English PHQ-8 virtual-interview data, especially in Qwen3 and WavLM views, after fold-internal length and severity controls. This is the defensible reading: corpus identity reflects acquisition and protocol signatures, not merely an English-versus-Chinese detector.

## Design Rows

| probe | modality | feature columns | length controls | language/protocol design |
| --- | --- | ---: | --- | --- |
| edaic_cmdc_qwen3_text_cross_language | text | 1024 | log1p_length_text_segments;log1p_length_text_tokens;log1p_length_text_chunks | cross-language contrast; language is intentionally confounded, so this row is interpreted with non-text and same-language probes / protocol differs by corpus and cannot be separately identified in this cross-corpus row |
| edaic_cmdc_wavlm_audio_nontext | audio | 768 | log1p_length_audio_segments;log1p_length_audio_seconds;log1p_length_audio_chunks | non-text acoustic view; lexical transcript language is removed / protocol differs by corpus and remains part of the acquisition identity signal |
| edaic_cmdc_openface_video_nontext | video | 204 | log1p_length_video_segments | non-text facial behavior view; lexical language is removed / protocol differs by corpus and remains part of the acquisition identity signal |
| edaic_internal_qwen3_text_lineage | text | 1024 | log1p_length_text_segments;log1p_length_text_tokens;log1p_length_text_chunks;log1p_length_transcript_turns;log1p_length_non_empty_turns | held constant: English virtual-interview PHQ-8 family / lineage/protocol proxy: 300-492 DAIC-WOZ lineage versus 600-718 extended lineage |
| edaic_internal_wavlm_audio_lineage | audio | 768 | log1p_length_audio_segments;log1p_length_audio_seconds;log1p_length_audio_chunks;log1p_length_padded_short_chunks | held constant: English virtual-interview PHQ-8 family / lineage/protocol proxy: 300-492 DAIC-WOZ lineage versus 600-718 extended lineage |
| edaic_internal_openface_video_lineage | video | 204 | log1p_length_video_segments;log1p_length_openface_frames | held constant: English virtual-interview PHQ-8 family / lineage/protocol proxy: 300-492 DAIC-WOZ lineage versus 600-718 extended lineage |
| cmdc_pdch_qwen3_text_same_language_hamd | text | 1024 | log1p_length_text_segments;log1p_length_text_tokens;log1p_length_text_chunks | held constant: Chinese text / same clinical scale family but different corpus/acquisition protocols |
| cmdc_pdch_wavlm_audio_same_language_hamd | audio | 768 | log1p_length_audio_segments;log1p_length_audio_seconds;log1p_length_audio_chunks | held constant: Chinese speech / same clinical scale family but different corpus/acquisition protocols |
