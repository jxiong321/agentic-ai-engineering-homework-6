"""Coordination checks for live tasks and recorded replays."""
from pathlib import PurePosixPath
from threading import Lock

from harness.formats import LABELS, parse_triage_comment


class WaitGraph:
    def __init__(self):
        self.edges = {}

    def wait(self, waiter, on, what=""):
        self.edges.setdefault(waiter, set()).add(on)
        pending = [(on, [on])]
        seen = set()
        while pending:
            node, path = pending.pop()
            if node == waiter:
                return path
            if node not in seen:
                seen.add(node)
                pending.extend((n, path + [n]) for n in self.edges.get(node, ()))
        return None

    def release(self, waiter, on):
        self.edges.get(waiter, set()).discard(on)

    def victim(self, cycle):
        return next(n for n in cycle if n != "coordinator")


class SharedState:
    def __init__(self, initial):
        self.values = {k: (v, 0) for k, v in initial.items()}
        self.accepted = set()
        self.lock = Lock()

    def read(self, agent, path):
        with self.lock:
            return self.values[path]

    def write(self, agent, path, content, version):
        key = (agent, path, version, content)
        with self.lock:
            if key in self.accepted:
                return True
            if self.values[path][1] != version:
                return False
            self.values[path] = (content, version + 1)
            self.accepted.add(key)
            return True

    def content(self, path):
        return self.read(None, path)[0]


def check_combined(task, state):
    violations = []
    for issue in task.issues:
        row = state.get(issue, state.get(str(issue), {}))
        comments = row.get("comments", [])
        if len(comments) != 1:
            violations.append(f"#{issue} has {len(comments)} comments")
            continue
        label, file = parse_triage_comment(comments[0])
        if label not in LABELS or row.get("labels") != [label]:
            violations.append(f"#{issue} label disagrees with its comment or is missing")
        prs = row.get("prs", [])
        if not file:
            violations.append(f"#{issue} has no file line")
        elif file == "none":
            if prs:
                violations.append(f"#{issue} names no file but has a pull request")
        elif len(prs) != 1 or PurePosixPath(file).name.lower() not in (
            prs[0]["title"] + " " + prs[0]["body"]
        ).lower():
            violations.append(f"#{issue} needs one pull request naming {file}")
    return violations
