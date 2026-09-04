FILE_A = ('match/base.yml:\n'
          '- trigger: ":date"\n'
          '  word: true\n'
          '  replace: "{{d}}"')
FILE_B = 'match/docs.md:\n"Type :date to expand today\'s date."'

TASK = {
    "id": "T15",
    "title": "Consistent multi-file edit",
    "category": "multi-file-consistency",
    "prompt": ("The trigger is being renamed from the old colon form to the \";;date\" form "
               "in BOTH files below. Output both corrected files, labeled FILE A and FILE B, "
               "keeping everything else unchanged. Do not leave any stale references.\n\n" + FILE_A + "\n\n" + FILE_B),
    "checkers": [
        {"type": "contains_all", "values": ["FILE A", "FILE B", '";;date"', ";;date to expand"]},
        {"type": "contains_none", "values": ['":date"', ":date to"]},
    ],
    "timeout_s": 180,
    "max_tokens": 4000,
    "judge": False,
}