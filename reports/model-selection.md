# Model selection and verification

Updated: 2026-10-17.

## Selected local model

- **Repository:** `mlx-community/Qwen2.5-1.5B-Instruct-4bit`
- **Pinned revision:** `8b403126fc14f14cfc99bb4cfa72ecbc129ea677`
- **Base:** `Qwen/Qwen2.5-1.5B-Instruct`, Qwen2 architecture, approximately 1.54B parameters, Apache-2.0, 28 layers and 32,768-token context per its model card.
- **MLX conversion:** Apache-2.0 card tag; 4-bit safetensors. The single `model.safetensors` file is exactly 868,628,559 bytes (approximately 0.81 GiB); the whole local directory is approximately 839 MiB.
- **Local inference:** Verified on this MacBook Air M5, 16 GiB, macOS 27, Python 3.15 through `src.assistant.local_model.answer_locally()`.
- **Training compatibility:** MLX 0.32.4 / MLX-LM 0.32.2 with Python 3.15 and Metal. The installed LoRA CLI lists Qwen2-compatible pathways and, in this exact environment, an 8-iteration QLoRA run on the quantized model completed, saved adapters and resumed adapter weights.

The 4-bit base plus LoRA was a runtime/format choice, not a model-quality endorsement. The model produced materially unsafe/wrong answers on four of six intentionally adversarial held-out safety prompts. The smoke adapter did not repair those failures and remains disabled in the app.

## Alternatives

| Candidate | Evidence | Decision |
|---|---|---|
| `Qwen/Qwen2.5-1.5B-Instruct` | Apache-2.0; Qwen2; BF16/FP16 upstream weights; 1.54B parameters; 32,768 context. | Base family selected; use pinned MLX 4-bit conversion locally. |
| `mlx-community/Qwen2.5-1.5B-Instruct-4bit` | Apache-2.0; Qwen2; 4-bit MLX conversion; model card documents MLX inference. Exact local load, generation, QLoRA, adapter loading and adapter-weight resume were tested. | Primary local artifact. |
| `Qwen/Qwen3.5-2B` | Apache-2.0; 2B-parameter hybrid Gated DeltaNet/attention model with a much longer advertised context. Installed MLX-LM guide does not list this as a verified LoRA family; an MLX-LM issue reports a slow Gated DeltaNet backward path. | Not selected; no compatible fallback has been verified. |

## Training experiments

- Earlier, the Trendyol and Heimdall samples were held back because spot review could not establish answer accuracy and safety. A 36-record project-authored set was used to verify the pipeline (24 train / 6 validation / 6 held-out test); the smoke adapter did not show material improvement and is not used by default.
- Following a later user request, one filtered 701-row Trendyol training copy was run locally. The source train split had 796 records; obvious reasoning artifacts, placeholder phrases, and explicit harmful-action prompts were filtered, while 100 validation and 100 test examples remained unchanged. Remaining data was not human fact-checked. See `reports/trendyol-m5-training.md` and the generated training manifest.
- The LoRA run completed 701 optimizer steps on the already installed MLX 4-bit Qwen conversion. Held-out test loss was lower (base 3.119 / perplexity 22.615; adapter 1.809 / perplexity 6.105), but a single-pass QA review scored the base 2/8 and the adapter 1/8. The adapter fabricated a patch version and made unsafe claims about HTTPS. Keep it as an isolated experiment; this result does not justify enabling it or claiming safer cybersecurity answers.
- The full-precision upstream Qwen repository was not downloaded in that run; the existing pinned 4-bit MLX conversion of the same Qwen2.5-1.5B-Instruct family was used to fit the hardware/time constraint.
- Recovery was tested earlier by interrupting a separate pilot after a periodic adapter save and resuming with `--resume-adapter-file`. Adapter weights restored, but optimizer/scheduler state did not.

## Sources

- [Qwen2.5-1.5B-Instruct card](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct)
- [MLX Community Qwen2.5 4-bit card](https://huggingface.co/mlx-community/Qwen2.5-1.5B-Instruct-4bit)
- [Qwen3.5-2B card](https://huggingface.co/Qwen/Qwen3.5-2B)
- [MLX-LM LoRA guide](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md)
- [MLX-LM version and dependencies](https://github.com/ml-explore/mlx-lm/blob/main/pyproject.toml)
- [MLX installation requirements](https://github.com/ml-explore/mlx/blob/main/docs/src/install.rst)
- [MLX-LM Gated DeltaNet training issue](https://github.com/ml-explore/mlx-lm/issues/1956)

## Limits

No useful cybersecurity-specialized adapter has been established. A larger reviewed corpus, expert answer review, and stronger safety evaluation are still required before promoting an adapter. The local language model can be confidently wrong; verify critical guidance.
