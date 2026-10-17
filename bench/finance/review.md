You are reviewing a finished codebase for code quality. Do not change any file and do not run the program or its tests; read the code only. The repository implements the specification at the end of this message: the Python package in `fin/` and its tests in `tests/`. Correctness against the specification is checked separately by other tests; your job is the quality of the code.

Read the whole package and a representative part of the tests, in parts if files are large. Then reply with only one JSON object, nothing before or after it:

{"scores": {"structure": N, "readability": N, "correctness_risks": N, "error_handling": N, "data_safety": N, "tests": N, "consistency": N}, "overall": N, "issues": ["...", "..."], "strengths": ["...", "..."]}

Scores are integers from 1 (poor) to 10 (excellent):

- structure: modules and responsibilities are well separated; no duplicated logic; the layers (CLI, HTTP API, domain logic, storage) don't leak into each other.
- readability: clear names, short focused functions, code that is easy to follow.
- correctness_risks: 10 means few risks. Logic that looks wrong, fragile or likely to break on inputs the specification allows (dates, rounding, currencies, partial payments, closed periods).
- error_handling: user errors are detected and reported consistently (exit code 2, message, nothing changed); no crashes with tracebacks on bad input; database changes are atomic.
- data_safety: money is Decimal everywhere and never float; SQL uses parameters, never string formatting; no data is lost or half-written on errors.
- tests: tests are meaningful, check behaviour rather than implementation, cover edge cases and every section, and are independent of each other.
- consistency: the same conventions (naming, JSON shapes, validation, formatting of amounts) across all modules.

`overall` is your overall judgement (1-10), not an average. `issues`: up to 6, most important first, each specific (file and function) and one sentence. `strengths`: up to 3.

Specification:

