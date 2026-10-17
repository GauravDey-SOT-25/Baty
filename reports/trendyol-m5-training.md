# Trendyol LoRA experiment on Apple M5

Run date: 2026-10-17. Training completed locally with the existing MLX environment. The base model and existing adapters were not modified.

## Data and provenance

- Dataset: `Trendyol/Trendyol-Cybersecurity-Instruction-Tuning-Dataset`, Apache-2.0, upstream revision `357544e7576607d88eaeac9b0adb07e9fd8bb2bb`.
- The upstream card advertises 53,202 rows. This run used the already downloaded, bounded 1,000-row sample rather than downloading the full dataset. The prepared fixed splits were 796 train / 100 validation / 100 test. The original raw and split files were left unchanged.
- Filtered training copy: 701 rows retained from the 796-row train split. Excluded rows matched automated internal-reasoning markers (33), placeholder phrases (57), or an explicit harmful-action prompt pattern (10); some rows matched multiple rules, leaving 95 unique exclusions. The repeated source system prompt was replaced with a short defensive instruction. The 100 validation and 100 test rows were copied unchanged. The source train SHA-256 and excluded source IDs are in `data/processed/trendyol-m5/manifest.json`.
- The prior sample audit found factual errors in manually inspected rows; the remaining 701 examples were not human fact-checked. The placeholder filter may have excluded useful abstention examples. These are important data-quality limits.

## Model and run

- Upstream base: `Qwen/Qwen2.5-1.5B-Instruct`, Apache-2.0, 1.54B parameters. This Mac already had the pinned MLX 4-bit conversion `mlx-community/Qwen2.5-1.5B-Instruct-4bit` at `models/Qwen2.5-1.5B-Instruct-4bit`; it is the same Qwen2.5 1.5B instruct model family, not the full-precision BF16 repository. No full-precision weights were downloaded in this run.
- Hardware/runtime: Apple M5, 16 GiB unified memory, MLX 0.32.4, MLX-LM 0.32.2, Python 3.15.
- LoRA: batch 1, 2 layers, rank 8, learning rate 1e-5, 512 token cap, prompt masking, gradient checkpointing, seed 17, 701 optimizer iterations. MLX reports 0.659M trainable parameters (0.043%). Long rows were truncated at 512 tokens; see `logs/trendyol-m5-training.log`.
- Command: `.venv/bin/python -m mlx_lm lora --train --model models/Qwen2.5-1.5B-Instruct-4bit --data data/processed/trendyol-m5 --adapter-path adapters/trendyol-m5-experiment --config configs/trendyol-m5.yaml --test --test-batches 100`.
- Exit status: success. Final adapter: `adapters/trendyol-m5-experiment/adapters.safetensors`; intermediate checkpoints are preserved in that directory. A separate comparison script loaded the final adapter successfully.

## Evaluation

Both token-loss evaluations used the unchanged 100-row Trendyol test split, batch size 1, and maximum sequence length 512:

| Model | Test loss | Perplexity |
| --- | ---: | ---: |
| Base 4-bit Qwen | 3.119 | 22.615 |
| Trendyol LoRA adapter | 1.809 | 6.105 |

This is a 42.0% lower token loss on a small same-source held-out split. It measures fit to the dataset's style/content, not factuality, safety, or usefulness.

A paired direct-generation comparison on the existing 8-question project QA set is in `trendyol-m5-qa-comparison-256.json`; manual rubric notes are in `trendyol-m5-qa-review.json`. The single-pass Codex review scored the raw base model 2/8 and the adapter 1/8. These scores are subjective, not independently reviewed. The adapter produced unsafe/unsupported claims on the HTTPS trust and fictional patch-version cases and did not improve the Q&A rubric score.

## Recommendation

Training technically completed and the adapter loads, but this experiment does **not** justify deploying or enabling the adapter. Keep it isolated in the experiment directory and leave the application default adapter unchanged. Do not claim improved cybersecurity answer quality from lower same-source test loss. A separate expert should review data quality and paired generations; then evaluate on a larger, genuinely held-out, independently authored benchmark before deciding whether further LoRA work is justified.
