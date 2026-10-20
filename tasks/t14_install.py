README = ('PLUGIN README (excerpt):\n'
          '"Requires omarchy-plugin >= 2.0.\n'
          'Install:  omarchy-plugin add <git-url> --enable\n'
          'Note: the legacy `omarchy-plugin install` command was removed in 2.0."')

TASK = {
    "id": "T14",
    "title": "Correct install command",
    "category": "install-guidance",
    "prompt": ("A user typed `omarchy-plugin install https://github.com/example/widget.git` and "
               "got 'unknown command'. Using ONLY the README excerpt, give the exact command "
               "they should run and why theirs failed. At most 60 words.\n\n" + README),
    # Positive assertions only. This used to ban "omarchy-plugin install", but
    # the prompt asks why the user's command failed, so a correct answer quotes
    # it: the ban graded phrasing, failing every model that quoted it
    # (2026-10-20). Requiring the full corrected command plus the reason does
    # the ban's job -- an answer recommending `install` lacks the `add` line.
    "checkers": [
        {"type": "contains_all", "values": [
            "omarchy-plugin add https://github.com/example/widget.git --enable",
            "removed"]},
        {"type": "length_max", "words": 80},
    ],
    "timeout_s": 120,
    "max_tokens": 4000,
    "judge": False,
}