"""Task loader for model-bench."""
import importlib.util
from pathlib import Path

REQUIRED_KEYS = {"id", "title", "category", "prompt", "checkers",
                 "timeout_s", "max_tokens", "judge"}


def load_tasks(task_dir=None):
    task_dir = Path(task_dir or Path(__file__).parent)
    tasks = []
    for path in sorted(task_dir.glob("t*.py")):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        task = getattr(mod, "TASK", None)
        missing = REQUIRED_KEYS - set(task or {})
        if missing:
            raise ValueError(f"{path.name}: TASK missing {missing}")
        if not task["prompt"] or not task["checkers"]:
            raise ValueError(f"{path.name}: empty prompt/checkers")
        tasks.append(task)
    tasks.sort(key=lambda t: t["id"])
    return tasks