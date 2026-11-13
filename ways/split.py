"""Concurrent read-only investigations followed by issue-scoped writers."""
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace

from agent.loop import load_bounds, run_loop
from harness.tasks import end_state
from split.guards import SharedState, WaitGraph, check_combined
from split.roles import investigate, usable, writer_message, writer_tools


def run(ctx):
    lead = ctx.agent("coordinator")
    waits = WaitGraph()
    bounds = load_bounds()
    per_issue = (ctx.budget or ctx.ceiling or bounds.max_tokens * len(ctx.issues)) // len(ctx.issues)
    read_share = per_issue * 2 // 3
    handoffs = SharedState({issue: "" for issue in ctx.issues})

    def receive(worker, contract, problems):
        lead.trace.event("worker_return", worker=worker, contract=contract, valid=not problems, errors=problems)

    def wait(worker, turn):
        lead.trace.event("wait", waiter=lead.id, on=worker.id, what="issue result", turn=turn)
        cycle = waits.wait(lead.id, worker.id)
        if cycle:
            victim = waits.victim(cycle)
            lead.trace.event("worker_stopped", worker=victim, reason="cyclic wait")
            raise RuntimeError(f"Stopped {victim} to break wait cycle {cycle}")

    def investigate_issue(worker, issue):
        _, version = handoffs.read(worker.id, issue)
        proposal = investigate(ctx, worker, issue, read_share, receive)
        if not handoffs.write(worker.id, issue, json.dumps(proposal), version):
            raise RuntimeError(f"Stale handoff for issue {issue}")

    try:
        with ThreadPoolExecutor(max_workers=len(ctx.issues)) as pool:
            jobs = {}
            for issue in ctx.issues:
                worker = ctx.agent(f"investigator-{issue}", parent=lead.id)
                wait(worker, 1)
                jobs[pool.submit(investigate_issue, worker, issue)] = (issue, worker)
            for job in as_completed(jobs):
                issue, worker = jobs[job]
                job.result()
                waits.release(lead.id, worker.id)
                proposal = json.loads(handoffs.content(issue))
                if not usable(proposal, issue):
                    continue
                writer = ctx.agent(f"writer-{issue}", parent=lead.id)
                wait(writer, 2)
                share = per_issue - read_share
                # Reserve the final model call's output and input growth.
                budget = max(0, share - ctx.settings.max_tokens - 16000)
                run_loop(writer.client, writer_tools(ctx, issue), ctx.prompt("write.md"),
                         writer_message(issue, proposal["result"]), replace(bounds, max_tokens=budget),
                         writer.trace)
                waits.release(lead.id, writer.id)
    finally:
        problems = check_combined(ctx.task, end_state(ctx.tracker, ctx.run_id, ctx.task))
        lead.trace.event("combined_check", passed=not problems, violations=problems)
        lead.trace.end("completed" if not problems else "stopped")
