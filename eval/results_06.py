"""Generate one tracker-grounded result per finished measured run."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __package__ in ("", None):
    sys.path.insert(0, str(ROOT))

from checks.check_06 import Remote, load_runs
from eval.check_task import check_task
from harness.tasks import load_tasks


def main():
    tasks = {t.id: t for t in load_tasks("fixtures/tasks6")}
    runs, _ = load_runs(set(tasks))
    tracker = Remote()
    rows = []
    for run in runs:
        if run.arm and run.finished:
            verdict = check_task(run.run_id, tasks[run.task], tracker)
            rows.append(dict(run_id=run.run_id, arm=run.arm, way=run.way, task=run.task,
                             kind=run.kind, sweep=run.sweep, passed=verdict["passed"],
                             parts=verdict["parts"], tokens=run.tokens, wall_s=run.wall_s))
    output = ROOT / "results/runs_06.jsonl"
    output.parent.mkdir(exist_ok=True)
    temporary = output.with_suffix(".tmp")
    temporary.write_text("".join(json.dumps(row) + "\n" for row in rows))
    temporary.replace(output)
    print(f"Wrote {len(rows)} run outcomes.")


if __name__ == "__main__":
    main()
