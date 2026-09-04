LOGS = (
    "SNIPPET 1 (omarchy agent hook):\n"
    "if [ -n \"$DISPLAY\" ]; then notify-send 'agent done' \"$TASK_TITLE\"; else echo 'no display' >> ~/agent-notify.log; fi\n\n"
    "SNIPPET 2 (pi agent service environment):\n"
    "systemctl --user show pi-agent | grep -E 'Environment'(DISPLAY|WAYLAND_DISPLAY): (empty)\n\n"
    "SNIPPET 3 (manual test in a terminal):\n"
    "notify-send 'test' works and dunst shows it immediately."
)

TASK = {
    "id": "T16",
    "title": "Correlate notification failure",
    "category": "log-correlation",
    "prompt": ("Agent-completion notifications never appear, but manual notify-send works. "
               "Given the three snippets, name the root cause and the fix in at most 100 words. "
               "Manual dunst restarts are NOT the fix.\n\n" + LOGS),
    "checkers": [
        {"type": "contains_all", "values": ["display"]},
        {"type": "contains_none", "values": ["restart dunst", "reinstall dunst"]},
        {"type": "length_max", "words": 130},
    ],
    "timeout_s": 180,
    "max_tokens": 4000,
    "judge": True,
}