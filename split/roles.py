"""Issue-scoped tool surfaces and a structured read-only investigation."""
import json
import time
from pathlib import Path

from agent.loop import load_bounds
from harness.client import tool_result
from harness.formats import format_triage_comment
from harness.roles import arg, role_of, tool_for
from harness.schema import errors
from tools import ToolResult
from ways.agent import Disclosing, disclosure_line

CONTRACT = json.loads(Path(__file__).with_name("contract.schema.json").read_text())
FIELDS = ("result", "status", "could_not_determine")
RETURN = {"name": "return_finding", "description": "Submit the finding and outstanding questions.",
          "strict": True, "input_schema": {"type": "object", "additionalProperties": False,
          "properties": {k: CONTRACT["properties"][k] for k in FIELDS}, "required": list(FIELDS)}}
READS = ("read_issue", "search", "read_file", "run_tests")
WRITES = ("apply_label", "open_pr", "comment")


class Surface:
    def __init__(self, registry, roles, issue):
        self.registry = registry
        self.issue = issue
        self.names = {tool_for(r) for r in roles}
        self.schemas = [s for s in registry.schemas if s["name"] in self.names]

    def call(self, name, args):
        if name not in self.names:
            return ToolResult("Tool unavailable in this role", True, 0)
        role = role_of(name)
        if role in (*WRITES, "read_issue") and args.get(arg(role, "number")) != f"issue-{self.issue}":
            return ToolResult("This issue is outside your assignment", True, 0)
        return self.registry.call(name, args)


def investigate(ctx, agent, issue, allowance, receive, *, hard_limit=True):
    surface = Surface(ctx.tools, READS, issue)
    schemas = surface.schemas + [RETURN]
    system = ctx.prompt("investigate.md")
    messages = [{"role": "user", "content": f"Investigate issue #{issue}."}]
    bounds = load_bounds()
    started = time.monotonic()
    searched, opened, mentioned = [], set(), set()
    count = 0
    reason = "turn_limit"

    def deliver(proposal):
        if isinstance(proposal, dict):
            proposal = {**proposal, "calls_used": count, "searched": searched.copy(),
                        "not_searched": sorted(mentioned - opened)}
        problems = errors(proposal, CONTRACT)
        receive(agent.id, proposal, problems)
        return problems

    for step in range(1, bounds.max_steps + 1):
        # Reserve room for the response under the hard share; matched-budget
        # attempts use a soft target and the runner's separate hard ceiling.
        request_bytes = len(json.dumps([messages, schemas, system]).encode())
        reserve = request_bytes + ctx.settings.max_tokens if hard_limit else request_bytes // 4
        if agent.client.total_tokens + reserve > allowance:
            reason = "token_budget"
            break
        if time.monotonic() - started >= bounds.wall_clock_s:
            reason = "wall_clock"
            break
        reply = agent.client.create(messages=messages, system=system, tools=schemas)
        agent.trace.model_call(step, reply)
        messages.append(reply.assistant_message())
        results = []
        for call in reply.tool_calls:
            if call.name == RETURN["name"]:
                problems = deliver(call.input)
                result = ToolResult("; ".join(problems) or "Accepted", bool(problems), 0)
                agent.trace.tool_call(step, call, result)
                if not problems:
                    agent.trace.end("completed")
                    return call.input
            else:
                result = surface.call(call.name, call.input)
                agent.trace.tool_call(step, call, result)
                role = role_of(call.name)
                if role:
                    count += 1
                if role in ("read_file", "search"):
                    key = "path" if role == "read_file" else "query"
                    value = call.input.get(arg(role, key))
                    if value is not None and str(value) not in searched:
                        searched.append(str(value))
                    if not result.is_error:
                        if role == "read_file":
                            opened.add(value)
                        else:
                            from harness.formats import result_paths
                            mentioned.update(result_paths(call.name, call.input, result.content, False))
            results.append(tool_result(call, result.content, result.is_error))
        if results:
            messages.append({"role": "user", "content": results})
        else:
            messages.append({"role": "user", "content": "Use return_finding to submit your conclusion."})
    empty = {"result": {"issue": issue, "label": None, "file": None, "evidence": ""},
             "status": "out_of_budget", "could_not_determine": ["No validated finding within the investigation bounds."]}
    deliver(empty)
    agent.trace.end(reason)
    return empty


def usable(proposal, issue):
    finding = proposal["result"]
    return (proposal["status"] != "out_of_budget" and finding["issue"] == issue
            and bool(finding["label"]) and bool(finding["file"]))


def writer_tools(ctx, issue):
    return Surface(Disclosing(ctx.tools, disclosure_line()), WRITES, issue)


def writer_message(issue, finding):
    return f"Write the triage for issue #{issue}.\n" + format_triage_comment(
        finding["label"], finding["file"], finding["evidence"])
