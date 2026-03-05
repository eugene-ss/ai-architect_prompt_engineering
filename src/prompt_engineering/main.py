"""
Commands:
    run        -- Run the ReAct agent on a query.
    evaluate   -- Compare prompt versions (v1/v2/v3) with evaluation metrics.
    optimize   -- Debug and optimize a prompt (v1 -> v2 -> v3 pipeline).
    benchmark  -- Run a full benchmark suite and persist results.
    batch      -- Process multiple queries concurrently via BatchProcessor.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.table import Table

from prompt_engineering.config import VERSION_MAP, setup_logging

app = typer.Typer(
    name="prompt-engineering",
    help="AI Architect Prompt Engineering -- ReAct agent, prompt optimization and evaluation.",
    add_completion=False,
)
console = Console()

def _load_config(config_path: str | None) -> dict:
    if config_path and Path(config_path).exists():
        return yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    return {}

def _build_client():
    from prompt_engineering.config import AppSettings
    from prompt_engineering.services import LLMClient

    settings = AppSettings()
    return LLMClient(settings), settings

@app.command()
def run(
    query: str = typer.Option(..., "--query", "-q", help="User query for the tutor agent."),
    profile: str = typer.Option("default", "--profile", "-p", help="Agent profile name."),
    prompt_version: str = typer.Option("v3", "--prompt-version", help="System prompt version (v1/v2/v3)."),
    verbose: bool = typer.Option(True, "--verbose/--quiet"),
) -> None:

    """Run the ReAct language-tutor agent."""
    setup_logging("DEBUG" if verbose else "INFO")
    asyncio.run(_run_agent(query, profile, prompt_version))

async def _run_agent(query: str, profile_name: str, prompt_version: str) -> None:
    from prompt_engineering.agents import ReActAgent
    from prompt_engineering.config import load_profile
    from prompt_engineering.prompts.loader import load_prompt
    from prompt_engineering.security import sanitise_input
    from prompt_engineering.tools import GrammarTool, NotesTool, QuizTool, VocabularyTool

    client, _ = _build_client()
    profile = load_profile(profile_name)
    query = sanitise_input(query)

    system_prompt = load_prompt(VERSION_MAP.get(prompt_version, VERSION_MAP["v3"]))
    tools = [VocabularyTool(), GrammarTool(), QuizTool(), NotesTool()]

    agent = ReActAgent(llm_client=client, profile=profile, tools=tools)
    answer = await agent.run(query, system_prompt=system_prompt)

    console.print("\n[bold green]Final Answer[/bold green]")
    console.print(answer.answer)
    console.print(
        f"\n[dim]Turns: {answer.turns_used} | Tools: {answer.tools_used}"
        f" | Latency: {answer.total_latency_ms:.0f} ms[/dim]"
    )
    await client.close()

@app.command()
def evaluate(
    queries: Optional[str] = typer.Option(None, "--queries", "-q", help="Comma-separated test queries."),
    versions: str = typer.Option("v1,v2,v3", "--versions", "-v", help="Comma-separated prompt versions."),
    config: Optional[str] = typer.Option(None, "--config", "-c"),
) -> None:

    """Compare prompt versions with evaluation metrics."""
    setup_logging("INFO")
    cfg = _load_config(config)
    test_queries = (
        [q.strip() for q in queries.split(",")]
        if queries
        else cfg.get("evaluation", {}).get("test_queries", ["Help me learn basic Spanish greetings for travel."])
    )
    asyncio.run(_evaluate(test_queries, [v.strip() for v in versions.split(",")]))


async def _evaluate(test_queries: list[str], versions: list[str]) -> None:
    from prompt_engineering.eval import PromptEvaluator

    client, _ = _build_client()
    evaluator = PromptEvaluator(client)
    report = await evaluator.compare(test_queries, versions)
    summary = report.summary()

    table = Table(title="Prompt Version Comparison")
    cols = ["Version", "Relevance", "Coherence", "Completeness", "Actionability", "Composite", "Safety %", "Latency ms"]
    for col in cols:
        table.add_column(col, style="bold" if col == "Version" else None)
    for v, s in summary.items():
        table.add_row(
            v, str(s["avg_relevance"]), str(s["avg_coherence"]), str(s["avg_completeness"]),
            str(s["avg_actionability"]), str(s["avg_composite"]), str(s["safety_pass_rate"]), str(s["avg_latency_ms"]),
        )
    console.print(table)
    await client.close()

@app.command()
def optimize(
    prompt_version: str = typer.Option("v1", "--from", "-f", help="Starting prompt version."),
    meta: bool = typer.Option(True, "--meta/--no-meta", help="Also run meta-prompting (v2->v3)."),
) -> None:

    """Debug and optimize a prompt through the refinement pipeline."""
    setup_logging("INFO")
    asyncio.run(_optimize(prompt_version, meta))

async def _optimize(prompt_version: str, meta: bool) -> None:
    from prompt_engineering.optimization import MetaPrompter, PromptDebugger
    from prompt_engineering.prompts.loader import load_prompt

    client, _ = _build_client()
    original = load_prompt(VERSION_MAP.get(prompt_version, VERSION_MAP["v1"]))
    console.print(f"[bold]Original prompt ({prompt_version}):[/bold]\n{original.strip()}\n")

    debugger = PromptDebugger(client)
    analysis, refined = await debugger.debug_and_optimize(original)

    console.print("[bold yellow]Analysis:[/bold yellow]")
    console.print(f"  Quality score: {analysis.overall_quality_score}/10")
    console.print(f"  Missing context: {analysis.missing_context}")
    console.print(f"  Ambiguity issues: {analysis.ambiguity_issues}")
    console.print(f"  Suggestions: {analysis.improvement_suggestions}")
    console.print(f"\n[bold green]Refined prompt:[/bold green]\n{refined}\n")

    if meta:
        v3 = await MetaPrompter(client).refine(refined)
        console.print(f"[bold cyan]Meta-prompted prompt (v3):[/bold cyan]\n{v3}\n")
    await client.close()

@app.command()
def benchmark(
    config: Optional[str] = typer.Option(None, "--config", "-c"),
    label: Optional[str] = typer.Option(None, "--label", "-l", help="Label for the benchmark run."),
    output_dir: str = typer.Option("outputs/benchmarks", "--output-dir", "-o"),
) -> None:

    setup_logging("INFO")
    cfg = _load_config(config)
    eval_cfg = cfg.get("evaluation", {})
    test_queries = eval_cfg.get("test_queries", ["Help me learn basic Spanish greetings for travel."])
    versions = eval_cfg.get("prompt_versions", ["v1", "v2", "v3"])
    asyncio.run(_benchmark(test_queries, versions, label, output_dir))

async def _benchmark(test_queries: list[str], versions: list[str], label: str | None, output_dir: str) -> None:
    from prompt_engineering.eval import BenchmarkRunner, PromptEvaluator

    client, _ = _build_client()
    evaluator = PromptEvaluator(client)
    runner = BenchmarkRunner(evaluator, output_dir=output_dir)
    report = await runner.run(test_queries, versions, run_label=label)

    console.print("[bold green]Benchmark complete![/bold green]")
    console.print(json.dumps(report.summary(), indent=2))
    await client.close()

@app.command()
def batch(
    queries: str = typer.Option(
        ..., "--queries", "-q",
        help="Comma-separated queries to process concurrently.",
    ),
    prompt_version: str = typer.Option(
        "v3", "--prompt-version",
        help="System prompt version (v1/v2/v3).",
    ),
    concurrency: int = typer.Option(
        10, "--concurrency", "-n",
        help="Max parallel requests.",
    ),
) -> None:

    """Process multiple queries concurrently via BatchProcessor."""
    setup_logging("INFO")
    query_list = [q.strip() for q in queries.split(",") if q.strip()]
    asyncio.run(_batch(query_list, prompt_version, concurrency))

async def _batch(
    queries: list[str], prompt_version: str, concurrency: int
) -> None:
    from prompt_engineering.prompts.loader import load_prompt
    from prompt_engineering.security import sanitise_input
    from prompt_engineering.services import BatchProcessor, ChatRequest

    client, _ = _build_client()
    system_prompt = load_prompt(
        VERSION_MAP.get(prompt_version, VERSION_MAP["v3"])
    )

    requests = [
        ChatRequest(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": sanitise_input(q)},
            ],
            metadata={"query": q},
        )
        for q in queries
    ]

    processor = BatchProcessor(client, max_concurrency=concurrency)
    results = await processor.run(requests)

    table = Table(title="Batch Results")
    table.add_column("#", style="dim")
    table.add_column("Query")
    table.add_column("Status")
    table.add_column("Latency ms")
    table.add_column("Response Preview")

    for r in results:
        query_text = r.request.metadata.get("query", "?")
        if r.ok:
            preview = r.response.content[:120].replace("\n", " ")
            table.add_row(
                str(r.index + 1),
                query_text[:60],
                "[green]OK[/green]",
                f"{r.response.latency_ms:.0f}",
                preview + ("..." if len(r.response.content) > 120 else ""),
            )
        else:
            table.add_row(
                str(r.index + 1),
                query_text[:60],
                "[red]FAIL[/red]",
                "-",
                str(r.error)[:120],
            )

    console.print(table)
    ok_count = sum(1 for r in results if r.ok)
    console.print(
        f"\n[bold]{ok_count}/{len(results)} succeeded[/bold]"
    )
    await client.close()

if __name__ == "__main__":
    app()