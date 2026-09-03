DATA = ('```json\n[{"ts": "2026-09-01T03:12:00Z", "level": "error", "msg": "disk write failed"},\n'
        '{"ts": "2026-09-01T11:00:00Z", "level": "info", "msg": "backup started"},\n'
        '{"ts": "2026-09-02T09:44:00Z", "level": "error", "msg": "handshake timeout"},\n'
        '{"ts": "2026-09-02T10:00:00Z", "level": "info", "msg": "reconnect ok"}]\n```')

TASK = {
    "id": "T05",
    "title": "JSON data transform",
    "category": "data-transform",
    "prompt": ("Given this JSON array of log entries, return ONLY a JSON object of the form "
               '{"errors": [sorted ts values where level=="error"], "total": <number of entries>}. '
               "No prose.\n\n" + DATA),
    "checkers": [
        {"type": "json_asserts", "asserts": [
            {"path": "errors", "op": "eq", "value": ["2026-09-01T03:12:00Z", "2026-09-02T09:44:00Z"]},
            {"path": "total", "op": "eq", "value": 4},
        ]},
    ],
    "timeout_s": 120,
    "max_tokens": 4000,
    "judge": False,
}