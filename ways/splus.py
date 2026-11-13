"""One sequential searcher: fresh attempts, plurality by label and file, one write."""
from collections import Counter

from harness.formats import format_triage_comment
from harness.roles import tool_for
from split.roles import investigate, usable, writer_tools
from harness.client import ToolCall


def run(ctx):
    agent = ctx.agent("single")
    target = ctx.budget or ctx.ceiling
    for index, issue in enumerate(ctx.issues):
        remaining = max(0, target - ctx.client.total_tokens)
        share = remaining // (len(ctx.issues) - index)
        spent = 0
        answers = []
        attempt = 0
        while spent < share * .95:
            attempt += 1
            reader = ctx.agent(f"attempt-{attempt}-{issue}", parent=agent.id)
            record = lambda worker, contract, problems: agent.trace.event(
                "attempt_return", worker=worker, contract=contract, errors=problems)
            proposal = investigate(ctx, reader, issue, share - spent, record, hard_limit=False)
            tokens = reader.client.total_tokens
            spent += tokens
            if usable(proposal, issue):
                answers.append(proposal["result"])
            if not tokens:
                break
        if not answers:
            continue
        votes = Counter((a["label"], a["file"]) for a in answers)
        label, file = votes.most_common(1)[0][0]
        chosen = next(a for a in answers if (a["label"], a["file"]) == (label, file))
        ref = f"issue-{issue}"
        actions = [("apply_label", {"issue": ref, "label": label})]
        if file != "none":
            actions.append(("open_pr", {"issue": ref, "branch": f"repomind/{ref}",
                            "title": f"Triage issue {issue}", "body": f"File: {file}\n\n{chosen['evidence']}"}))
        actions.append(("comment", {"issue": ref, "body": format_triage_comment(label, file, chosen["evidence"])}))
        tools = writer_tools(ctx, issue)
        for step, (role, args) in enumerate(actions, 1):
            call = ToolCall(f"write-{issue}-{step}", tool_for(role), args)
            result = tools.call(call.name, args)
            agent.trace.tool_call(step, call, result)
            if result.is_error:
                break
    agent.trace.end("completed")
