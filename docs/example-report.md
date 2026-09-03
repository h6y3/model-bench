# model-bench report — 20260903-223427

Judge: `glm-5.3:cloud`

## Pass matrix

| task | glm-5.3-flash:cloud | glm-5.3:cloud | gemma4:31b:cloud |
|---|---|---|---|
| T01 Instruction precision | ✓ | ✓ | ✓ |
| T02 Crash log diagnosis | ✓ | ✓ | ✓ |
| T03 Fix broken YAML config | ✓ | ✓ | ✓ |
| T04 Write a small bash script | ✓ | ✓ | ✓ |
| T05 JSON data transform | ✓ | ✓ | ✓ |
| T06 Synthesize release research | ✓ | ✓ | ✓ |
| T07 Write a commit message | ✓ | ✓ | ✓ |
| T08 Find the bug | ✓ | ✓ | ✗ |
| T09 sed one-liner | ✓ | ✓ | ✗ |
| T10 Constrained rewrite | ✓ | ✓ | ✓ |

## Totals

| model | passed | avg latency s | tok/s | est cost $ | judge avg |
|---|---|---|---|---|---|
| glm-5.3-flash:cloud | 10/10 | 4.95 | 112.1 | $0.0028 | 5.0 |
| glm-5.3:cloud (judge=self) | 10/10 | 3.76 | 145.5 | $0.0266 | 5.0 |
| gemma4:31b:cloud | 8/10 | 0.87 | 51.7 | $0.0003 | 5.0 |

## Notable failures

- **gemma4:31b:cloud** T09: exec_code[case0] — observed: exit=0 out=''
- **gemma4:31b:cloud** T08: contains_all — observed: missing: ['range']

---
Cost rates per M tokens: `glm-5.3-flash:cloud` $0.15/$0.5, `glm-5.3:cloud` $1.4/$4.4, `gemma4:31b:cloud` $0.1/$0.4. gemma4 rates approximate.
_Generated 2026-09-03T22:35:09.987304+00:00_
