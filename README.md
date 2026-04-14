# The Clean Code Bot

A small Python CLI that sends your source file through a **chain-of-thought (CoT) style** prompt, then returns a refactored version with stronger structure and documentation. It targets **SOLID**-friendly improvements while asking the model to **preserve behavior**.

## Principles baked in

- **Structured reasoning first**: the prompt forces analyze → SOLID review → plan → execute → document before emitting code.
- **Defense in depth for prompt injection**: size limits, delimiter framing, explicit “user code is data” system instructions, and heuristic rejection of common injection phrases embedded in files.
- **Boring, testable Python**: thin orchestration, explicit validation layer, OpenAI-compatible API (OpenAI or Groq).

## Setup

```bash
cd clean-code-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
# edit .env with your key(s)
```

## Configuration

| Variable | Meaning |
| --- | --- |
| `OPENAI_API_KEY` | Required when using OpenAI (default provider). |
| `GROQ_API_KEY` | Required when `CLEAN_CODE_BOT_PROVIDER=groq`. |
| `CLEAN_CODE_BOT_PROVIDER` | `openai` (default) or `groq`. |
| `CLEAN_CODE_BOT_MODEL` | Override model id (defaults: `gpt-4o-mini` / `llama-3.3-70b-versatile`). |

## Usage

```bash
clean-code-bot refactor path/to/dirty.py -o path/to/clean.py
cat path/to/dirty.py | clean-code-bot refactor --stdin -o out.py
python -m clean_code_bot refactor examples/order_service_before.py
```

## Examples

See `examples/` for **before** snapshots and an **illustrative after** sample. Live model output will differ; treat the “after” file as a style reference, not a golden master.

## Publishing to GitHub (SSH, personal account)

After you create the empty repository:

```bash
git init
git add .
git commit -m "Initial import: Clean Code Bot CLI"
git branch -M main
git remote add origin git@github.com-personal:YOUR_USER/clean-code-bot.git
git push -u origin main
```

Replace `github.com-personal` with the host alias you use for your personal SSH key.

## Security note

This tool reduces risk but **cannot** guarantee safety against a determined adversary stuffing instructions into source. Review diffs before merging, especially for third-party code.
