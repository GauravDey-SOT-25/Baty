# Model selection status

Research checked: 2026-10-17. No model has been downloaded or loaded.

## Provisional choice

- **Primary candidate:** `Qwen/Qwen2.5-1.5B-Instruct` (Transformers source) with the MLX community conversion `mlx-community/Qwen2.5-1.5B-Instruct-4bit` for local inference and a potential QLoRA experiment.
- **Fallback candidate:** `Qwen/Qwen3.5-2B`, only if model architecture loading, inference, and training are verified in the exact installed MLX-LM release. At present this is not a dependable fallback for the MLX training objective.
- **Status:** provisional, with runtime compatibility confirmed. The project-local MLX stack and CLI install, but model inference and training still need a local weight load.

## Candidate evidence

| Repository | Architecture / size | License | Quantization | Context | MLX status | Decision |
|---|---|---|---|---|---|---|
| `Qwen/Qwen2.5-1.5B-Instruct` | Qwen2 causal LM, 1.54B params, 28 layers | Apache-2.0 | upstream BF16/FP16 safetensors; not a quantized repo | 32,768 per model card | Current MLX-LM LoRA guidance lists Qwen2 family; exact release and runtime smoke test still required | Preferred trainable candidate |
| `mlx-community/Qwen2.5-1.5B-Instruct-4bit` | Qwen2, same 1.54B base | Apache-2.0 tag | 4-bit MLX | inherited base context 32,768 | Card documents MLX loading; local CLI supports QLoRA for quantized models, but the weights have not been tested | Preferred local inference and pilot candidate after model load |
| `Qwen/Qwen3.5-2B` | Hybrid Gated DeltaNet + attention vision-language model, 2B params | Apache-2.0 | upstream safetensors | 262,144 stated by card | Not listed among documented LoRA families in current MLX-LM LoRA guide. A recent MLX-LM issue reports a slow Python-loop backward path for Gated DeltaNet training. | Do not choose for initial training |

Hugging Face API metadata reports the selected 4-bit `model.safetensors` at 868,628,559 bytes (about 0.81 GiB), revision `8b403126fc14f14cfc99bb4cfa72ecbc129ea677`. No model was downloaded, and no memory benchmark is claimed.

## Runtime and training compatibility

The MLX-LM project declares Python `>=3.11`, MLX `>=0.32.2` on macOS, and Transformers `>=5.7.0`; its classifiers list 3.11–3.13. PyPI has native arm64 CPython 3.15 wheels for MLX 0.32.4 on macOS 26, so the current macOS 27 / Python 3.15 host is supported by an available wheel. The project-local stack installs and MLX imports successfully.

Installed MLX-LM 0.32.2 `lora --help` succeeds and exposes `--batch-size`, `--max-seq-length`, `--num-layers`, `--save-every`, `--resume-adapter-file`, `--grad-checkpoint`, and `--mask-prompt`. Current upstream guidance lists Qwen2 as a supported LoRA family, says quantized weights use QLoRA, and documents the prepared `messages` JSONL chat format. These support a proposed pilot but do not replace loading the actual weights. Adapter-weight resume is documented; optimizer/scheduler-state recovery is not established by the guide.

## Sources

- [Qwen2.5-1.5B-Instruct model card](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct)
- [MLX Community Qwen2.5 4-bit model card](https://huggingface.co/mlx-community/Qwen2.5-1.5B-Instruct-4bit)
- [Qwen3.5-2B model card](https://huggingface.co/Qwen/Qwen3.5-2B)
- [MLX-LM LoRA guide](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md)
- [MLX-LM pyproject.toml](https://github.com/ml-explore/mlx-lm/blob/main/pyproject.toml)
- [MLX installation requirements](https://github.com/ml-explore/mlx/blob/main/docs/src/install.rst)
- [MLX-LM Qwen3.5 Gated DeltaNet training performance issue](https://github.com/ml-explore/mlx-lm/issues/1956)

## Updated runtime result

Local install now succeeds with MLX 0.32.4 / MLX-LM 0.32.2 in Python 3.15. The CLI help runs and confirms the intended small-run controls. Hugging Face API metadata identifies the 4-bit Qwen2.5 MLX weight file as 868,628,559 bytes at revision `8b403126fc14f14cfc99bb4cfa72ecbc129ea677`. It has not been fetched or loaded, so actual inference and training remain unverified.


## Download and local inference verification (2026-10-17)

- User approved the previously described approximately 0.81 GiB model download. Retrieved the pinned snapshot `mlx-community/Qwen2.5-1.5B-Instruct-4bit@8b403126fc14f14cfc99bb4cfa72ecbc129ea677` into the ignored local `models/` directory.
- `model.safetensors` is exactly 868,628,559 bytes and matches the snapshot index. The directory is approximately 839 MiB on disk.
- MLX reports the GPU/Metal device available on Apple M5. `src.assistant.local_model.answer_locally()` successfully loaded the local model and produced a response to a benign attachment-safety question. The app loader uses only the local path; it did not fetch anything.
- No adapter training has run. A spot review of six training examples found apparent technical errors, inconsistent terminology (including PtT/PtH confusion), and a response written in internal chain-of-thought style (“the user wants to know…”). These findings are enough to reject this sample for adapter training pending a broader factuality/safety review and curation. Keyword counts do not establish dataset quality.
