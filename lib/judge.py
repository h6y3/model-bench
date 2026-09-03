"""Optional rubric judge. Stdlib only."""
from .checks import extract_json

JUDGE_SYSTEM = (
    "You are a strict grader. Reply with ONLY a JSON object: "
    '{"score": <integer 1-5>, "verdict": "<=25 words"}. '
    "Rubric: correctness 0-2, completeness 0-2, followed instructions 0-1. "
    "Do not grade writing style unless the task is about writing."
)


def build_judge_prompt(task, answer):
    return (f"TASK:\n{task['prompt']}\n\nMODEL ANSWER:\n{answer}\n\n"
            "Grade the answer against the task. Reply with only the JSON object.")


def parse_judge(raw):
    obj = extract_json(raw or "")
    if isinstance(obj, dict) and "score" in obj:
        try:
            score = int(obj["score"])
        except (TypeError, ValueError):
            score = None
        if score is not None:
            score = max(1, min(5, score))
        verdict = str(obj.get("verdict", ""))[:200]
        return {"score": score, "verdict": verdict}
    return {"score": None, "verdict": f"unparseable: {(raw or '')[:100]}"}


def judge_task(client, judge_model, task, answer):
    """client signature: client(model, messages, **kw) -> chat result dict."""
    try:
        resp = client(judge_model, [
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": build_judge_prompt(task, answer)},
        ], max_tokens=200, timeout_s=120)
        result = parse_judge(resp["content"])
        result["error"] = None
        return result
    except Exception as e:  # ClientError or anything else — never crash run
        return {"score": None, "verdict": "", "error": f"{type(e).__name__}: {e}"}