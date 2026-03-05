## Description

### **Spanish Language Tutor**

- **ReAct / Self-Reflection agents**: An agent that helps users learn Spanish (as a representative domain). The agent follows a structured reasoning loop. It thinks about what to do, takes an action using domain tools (vocabulary lookup, grammar explanations, quizzes, note-taking), observes the result. The self-reflection step catches mistakes, avoids redundant actions and improves the quality of the final answer.
- **Prompt Debugging & Optimization**, **Meta-prompting**: A three-stage pipeline that takes a poorly performing prompt and systematically improves it:
    - Stage 1 (v1): A deliberately vague prompt: "Act as a language tutor. Help me learn Spanish." -- produces generic, unfocused output.
    - Stage 2 (v2): An LLM analyses the weaknesses of v1 (missing context, ambiguity, lack of specificity) and produces a refined prompt with clear goals, timeframes, and structure.
    - Stage 3 (v3): A meta-prompting step where the LLM further refines v2 into the most structured and actionable version, adding pedagogical best practices, output format instructions, and quality constraints.

## Getting started

### Prerequisites

- **Python 3.11** (required)
- **UV** package manager (recommended; `pip` also works)

### Installation

```bash
git clone <repo-url> ai-architect_prompt_engineering
cd ai-architect_prompt_engineering

# Option A — UV (recommended)
uv venv --python 3.11
uv pip install -e .

# Option B — pip
python3.11 -m venv .venv
source .venv/bin/activate   # Unix / macOS
# .venv\Scripts\activate    # Windows
pip install -e .
```

### Environment setup

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | API key for the EPAM AI Proxy |
| `ENDPOINT_URL` | Proxy base URL (default: `https://ai-proxy.lab.epam.com/`) |
| `DEPLOYMENT_NAME` | Model deployment (default: `gpt-4o-mini-2024-07-18`) |
| `API_VERSION` | API version (default: `2025-01-01-preview`) |

---

## Usage

### CLI commands

Activate the virtual environment first, then use the `prompt-engineering` CLI:

```bash
# Activate (pick one)
source .venv/bin/activate   # Unix / macOS
# .venv\Scripts\activate    # Windows

prompt-engineering run --query "Teach me Spanish greetings for travel" --profile default --prompt-version v3
prompt-engineering evaluate --versions v1,v2,v3
prompt-engineering optimize --from v1
prompt-engineering benchmark --label baseline
prompt-engineering batch --queries "Teach me greetings,Explain verb conjugation,Help with numbers" --concurrency 5
```

### Example scripts

```bash
python examples/step1_initial_prompt.py       # v1: vague prompt
python examples/step2_refined_prompt.py        # v2: refined prompt
python examples/step3_meta_prompting.py        # v3: LLM-refined
python examples/step4_react_self_reflection.py # Full ReAct agent
```

---

## Prompt evolution pipeline

| Stage | File | Description |
|-------|------|-------------|
| **v1** | `tutor_v1_initial.md` | Deliberately vague: *"Act as a language tutor. Help me learn Spanish."* |
| **v2** | `tutor_v2_refined.md` | Manually refined with level, goals, timeframe, focus areas |
| **v3** | `tutor_v3_meta.md` | LLM-refined via meta-prompting -- most structured and actionable |

---

## ReAct + Self-Reflection

The agent follows a **Thought -> Action -> Observation** loop (ReAct). After each tool observation, an optional **self-reflection** step asks the agent to evaluate its own performance:

1. Is my last action aligned with the user's goal?
2. Did I make a mistake?
3. Should I adjust my approach?
4. Am I within budget?

---

## Evaluation metrics

| Metric | Type | Description |
|--------|------|-------------|
| Relevance | 0-10 | Does the response address learning goals? |
| Coherence | 0-10 | Is the plan logically structured? |
| Completeness | 0-10 | Covers vocabulary, grammar, dialogues, exercises? |
| Actionability | 0-10 | Can the learner follow without extra guidance? |
| Safety | pass/fail | Free of harmful content, PII, prompt injection? |
| Latency | ms | Response time |
| Token efficiency | count | Tokens used vs. information density |

---

## Security

- **API keys**: Stored as environment variables, loaded via Pydantic.
- **Prompt-injection detection**: 13 input-side + 5 output-side regex patterns.
- **Input sanitisation**: Control-character stripping, length limiting, injection blocking.
- **Output filtering**: PII redaction (email) and indirect-injection stripping.

---

## Project structure

```
ai-architect_prompt_engineering/
├── src/prompt_engineering/
│   ├── main.py              # CLI entry point (Typer)
│   ├── config.py            # Settings, profiles, logging, constants
│   ├── agents/              # ReAct agent + self-reflection
│   │   ├── __init__.py
│   │   └── react_agent.py
│   ├── tools/               # Domain tools for the agent
│   │   ├── __init__.py
│   │   ├── base.py          # BaseTool ABC
│   │   ├── vocabulary.py
│   │   ├── grammar.py
│   │   ├── quiz.py
│   │   └── notes.py
│   ├── eval/                # Evaluation metrics & benchmark
│   │   ├── __init__.py
│   │   ├── metrics.py       # EvaluationScores, MetricEvaluator
│   │   ├── evaluator.py     # PromptEvaluator, ComparisonReport
│   │   └── benchmark.py     # BenchmarkRunner (JSON persistence)
│   ├── optimization/        # Prompt debugging & meta-prompting
│   │   ├── __init__.py
│   │   ├── debugger.py      # PromptDebugger, PromptAnalysis
│   │   └── meta_prompter.py # MetaPrompter, MetaPromptResult
│   ├── services/            # LLM transport layer
│   │   ├── __init__.py
│   │   ├── llm_client.py    # Async LLM client
│   │   └── batch_processor.py # Concurrent batch execution
│   ├── security/            # Input/output sanitisation
│   │   ├── __init__.py
│   │   ├── sanitiser.py     # Prompt-injection detection
│   │   └── output_filter.py # PII redaction, indirect injection
│   └── prompts/             # Versioned prompt files (v1/v2/v3)
│       ├── loader.py
│       ├── meta_prompts/
│       └── react_prompts/
├── profiles/                # YAML agent profiles
├── pyproject.toml           # Project config
└── config.example.yaml      # Runtime config template
```
---