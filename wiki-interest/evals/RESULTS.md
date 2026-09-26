# Eval results: Claude Haiku 4.5 via Claude Code 2.1.283

Prompts and checklist: [prompts.md](prompts.md). Each run starts in a fresh workspace with only this skill installed (`bash evals/run.sh`). Date: 2026-09-26.

## Final round (after all fixes)

| Case | Tool calls | Time | Cost | Result |
|---|---|---|---|---|
| ex1 pl vs cs, fasting | 3 | 31 s | $0.047 | Pass. Says the comparison is impossible (no pl article), reports cs with LOW confidence, limitations incl. 2025 bot reclassification. |
| ex2 astronomy, uk | 3 | 26 s | $0.045 | Pass. -48% adjusted, LOW because 18 views/day, limitations. |
| pl (Polish prompt + PDF) | 5 | 41 s | $0.059 | Pass. Answer in Polish, PDF with English labels, numbers check passed. |
| ex3 English, 6 editions + PDF | 6 | 60 s | $0.074 | Partial. Numbers, ranking and PDF correct; the chat answer adds causes not in the data ("economic growth of Vietnam") and skips limitations. The same case passed fully in round 4. |
| ex3-follow (+pt, 3 years) | 1 | 22 s | $0.096 | Partial. One cached `analyze` call, year-by-year numbers and labels read correctly; still uses a flag emoji and "accelerating" for a single +2% year. |

Every run: skill triggered on the first call, no invented article titles, every number traceable to `analyze` output, PDFs one page.

## Other scripts (after adding PDF labels in 14 languages)

| Case | Tool calls | Time | Cost | Result |
|---|---|---|---|---|
| ja (Japanese prompt + PDF) | 5 | 43 s | $0.058 | Pass. Answer in Japanese, `--lang ja`, Noto Sans JP downloaded once, numbers check passed. |
| ar (Arabic prompt + PDF) | 5 | 39 s | $0.060 | Pass. Answer in Arabic, `--lang ar`, right-to-left shaped PDF ([example](examples/ar-astronomy-report.pdf)); -40% / -49% adjusted match the data. Limitations only in the PDF, not in the chat answer. |

## What the rounds changed

| Round | Problem seen | Fix |
|---|---|---|
| Pilot | Skill works on a Ukrainian prompt, but limitations from SKILL.md were skipped. | Rules moved into `analyze` output (`## Answer rules`). |
| 1 | ex1: no pl article, Haiku analyzed the broader "Post" (fasting) and compared it with cs. | `find` and SKILL.md: never replace a missing article with a broader topic. Round 2+: no substitution. |
| 1 | "Low volume (< 20)" read as "20 needed for HIGH". | Reason text: "under 20 = LOW". |
| 1 | PDF: bold leaked to the end of bullets; `**Question:**` rendered as a bullet (bug in our parser). | Parser fix + regression test with real model markdown. |
| 1 | MEDIUM called "reliable"; claims about competition. | Confidence scale spelled out; "claim only what views show". |
| 2 | Language editions named as countries; invented sum "es + pt = 541 views/day". | Table shows "Vietnamese (vi)"; answer template: no country names, no sums or new numbers. Round 3+: no invented numbers. |
| 3 | Follow-up "3 years": identical numbers read as "stable for 3 years". Real product gap: `--months` only extended the chart. | Year-by-year growth for every 12-month block, with code-computed labels `improving / worsening / about the same`. |
| 4 | "-16% -> -15%" called "worse"; Polish user got Ukrainian PDF labels. | Labels computed in code (round 5 read them correctly); report hint no longer suggests `uk`. |

## Known limits of a small model

- Chat answers still vary between runs on the widest case (ex3): sometimes speculative causes or missing limitations. PDFs are safer: numbers are checked and limitations are added by code.
- Broad intents: SKILL.md asks for 2-3 related articles ("learning English" = English language + IELTS); Haiku analyzed a second article in 1 of 5 ex3 runs. A built-in article basket would make this reliable.
- Next step: a `check` command for the chat answer (same numbers check + required limitations), or a hook that runs it before the reply.

## Totals

23 Haiku runs in 7 rounds, $1.60 in total, 22-61 s and 1-6 tool calls per question.
