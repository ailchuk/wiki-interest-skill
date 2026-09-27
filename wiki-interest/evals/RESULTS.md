# Eval results: Claude Haiku 4.5 via Claude Code 2.1.283

Prompts and checklist: [prompts.md](prompts.md). Each run starts in a fresh workspace with only this skill installed (`bash evals/run.sh`). Dates: 2026-09-26 and 2026-09-27.

## Final round (round 8, everything below already fixed)

| Case | Tool calls | Time | Cost | Result |
|---|---|---|---|---|
| ex1 pl vs cs, fasting | 5 | 54 s | $0.069 | Pass. Says the comparison is impossible (no pl article) and what that absence means - niche or not written up yet, readers may use another edition, without guessing which - keeps pl in the run as MISSING, then reports cs with LOW confidence and its reason, plus limitations incl. the 2025 bot reclassification. |
| ex2 astronomy, uk | 5 | 46 s | $0.039 | Pass. -47% adjusted, LOW because 18 views/day, answers the trust question directly. |
| ex3 English, 6 editions + PDF | 9 | 92 s | $0.076 | Pass. Finds two concepts, analyzes them as one basket, names the editions that hold only part of it, PDF in one page ([example](examples/ex3-english-learning-report.pdf)). |
| th "we launch above 200/day, below 50 is pointless" | 7 | 59 s | $0.052 | Partial. Reruns with `--low-views 50` and Polish drops to LOW as the user would want; `--high-views 200` still missed. |

Every run: the skill triggered on the first call, no invented article titles, every number traceable to `analyze` output, `check` run before replying, PDFs one page.

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
| 8 | With `check` added, Haiku ran it four times on an answer that had already passed, edited between each, then replied with a fresh summary it never checked. 16 tool calls, 151 s. | On success `check` says the answer passed, and to send the file word for word without checking again. Next run: 5 calls, 60 s, and the reply was the checked text. |
| 8 | That fix swallowed the PDF: "send it" was read as the end of the job. | `check` lists `report` as the first of the two remaining steps, and SKILL.md says the chat message is not the report. |
| 8 | "Learning English" still measured by one article, after both SKILL.md and a `find` hint asked for more. | SKILL.md now starts by naming the concepts a question covers: a thing is one, an activity at least two. Next run searched twice and analyzed `Q1860,Q1455178` as a basket. |
| 8 | "The Vietnamese web is growing" given as the cause of a trend. | The answer template names the three inventions to avoid, in those words. Later runs move such guesses into "what to verify" instead. |
| 8 | The user's own audience size ("from 200 a day") was ignored and the thresholds stayed at the defaults. | `analyze` prints the thresholds in use and the flags that change them. Next run used `--low-views 50`. |
| 8 | `check` called the level missing when the answer wrote the inflected "НИЗЬКІЙ" for "НИЗЬКА", and rejected "20" although `analyze` prints it in every LOW reason. | Confidence words matched by stem; thresholds count as values the tool printed. |
| 8 | A missing article ended the subject: "interest there cannot be measured", nothing more, although the absence is itself worth reporting. | `find` now says how many Wikipedias do have the topic and names the largest of them, that the gap means niche or not-yet-written rather than no interest, and that a large edition may be analyzed separately as a global signal but never as the missing language's audience. |
| 8 | After that change: "Polish readers may read it in English or German" - German came from our list of large editions, not from data. Another run dropped pl from `analyze` and put en in its place, unasked, then called the en trend "global interest". | `find` says the list is where articles exist, not what readers read, and not to name a language; the missing language stays in `--langs`, another edition only on the user's request. Next 3 runs: pl kept, nothing put in its place. |
| 8 | The blanket "do not name a language" was still broken: a run listed English and German as editions to check. Naming an edition that demonstrably has the article is not an invention, and a rule broken every run weakens the ones next to it. | The rule now separates the two cases: an edition may be named as something to check, never as a claim about who reads what. Next run kept the naming inside "what to research next", where a hypothesis belongs. |
| 8 | Local test: the skill folder was copied with `cp -r` together with a working `.venv`; a copied venv does not work in a new folder, pip failed, and Haiku then answered from general knowledge ("astronomy has steady demand", competitor advice). | `wi` records where the venv was built and rebuilds a moved one (`venv --clear`), deletes a failed install, and never wipes a folder that is not a venv. The install error and SKILL.md say: tell the user what failed and stop. Rerun with an install that cannot succeed: one retry, then a plain "cannot run the analysis", no answer without data. |
| 8 | Claude Desktop on Windows (local agent mode): no `bash` on PATH and no Python installed (`python` = the Store stub, exit 49). Nothing from the skill ran, so the model got no `ERROR:` line and tried 10 commands, 8 failed. | `python scripts/wi.py` now works without bash: `bootstrap.py` builds the same `.venv` and the printed commands use that form. SKILL.md: no bash -> python entry; no Python -> tell the user to install it and stop. Tested on Linux without the wrapper; not yet rerun on Windows. |
| 8 | Windows, Claude Desktop: "101 users a day" for 101 views/day. Also found here: printed commands had unquoted `C:\...` paths that bash mangles, the venv marker used the logical path so every symlinked eval workspace rebuilt the venv (a 2-minute pip run that Claude Code moved to the background), and on Windows `.venv` inside Claude Desktop's skill folder passed the 260-character path limit. | Template: "views, never users or visitors"; `check` reminds when such a word appears. Commands printed with forward slashes and quotes; marker uses the physical path; Windows venv at `~/.cache/wiki-interest/venv`. Rerun: "101 перегляд на день", both limitations present, 5 calls, 38 s. |
| 8 | "Compare over the last 3 months": `--months 3` was refused (growth needs 24 months) and the model, barred from computing numbers, answered it could not. A real product gap: the question is natural and the data was there. | `analyze` always prints `Last N months vs the same months a year earlier` (`--recent N`, 1-12, default 3; seasons cancel), with views/day in the window; `check` and `report` accept those numbers; the `--months` error points to it; `--recent` gets its own run folder. Rerun: the 3-month numbers and views/day right, the 12-month confidence kept apart - but "high confidence" still written next to the 3-month +62%. |

## Known limits of a small model

- Causes and market claims are the one rule code cannot enforce: `check` can only remind. Runs now hedge them or move them into "what to verify", but a sentence like "the market is saturated" can still reach the user. A judge model would be the honest fix.
- The basket has to be assembled by the model. When it names the concepts first it does this well, but the second concept it picks is its own choice ("second-language acquisition" rather than IELTS), and a poor choice is not detectable by code.
- Confidence reasons can be paraphrased wrongly: the ex3 example PDF explains MEDIUM as "variance in the data", while `analyze` gives "trend differs after adjusting". `check` verifies the level word, not its reason.
- Confidence attached to the wrong number: the 12-month level written next to the 3-month window, although `analyze` says that window has none. `check` verifies numbers, not what they are attached to.
- Half-followed refinements: the user's lower bound became `--low-views`, the upper bound did not.
- A passing `check` costs one extra tool call per question, about 10-15 s.

## Totals

49 Haiku runs in 8 rounds, $3.28 in total, including prompts in Ukrainian, Polish, Japanese and Arabic. In the final round a question takes 42-92 s and 5-9 tool calls; the cheaper rounds before `check` existed ran 22-61 s and 1-6 calls.

## Other scripts (round 7, PDF labels in 14 languages)

| Case | Tool calls | Time | Cost | Result |
|---|---|---|---|---|
| pl (Polish prompt + PDF) | 5 | 41 s | $0.059 | Pass. Answer in Polish, PDF with Polish labels, numbers check passed. |
| ja (Japanese prompt + PDF) | 5 | 43 s | $0.058 | Pass. Answer in Japanese, `--lang ja`, Noto Sans JP downloaded once, numbers check passed. |
| ar (Arabic prompt + PDF) | 5 | 39 s | $0.060 | Pass. Answer in Arabic, `--lang ar`, right-to-left shaped PDF ([example](examples/ar-astronomy-report.pdf)); -40% / -49% adjusted match the data. Limitations only in the PDF, not in the chat answer - the gap `check` was built to close. |
