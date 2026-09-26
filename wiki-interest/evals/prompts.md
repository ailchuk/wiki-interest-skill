# Eval prompts

Run one case (from the skill folder; needs Claude Code 2.x as `claude` or `CLAUDE_BIN=/path/to/claude`):

```bash
bash evals/run.sh ex2 "Ми думаємо додати курс з астрономії до освітнього застосунку. Чи зростає інтерес до цієї теми в україномовній Wikipedia, і наскільки цьому зростанню можна довіряти?"
```

Follow-up in the same session: add `--resume <session>` (the session id is printed on the first line).

| Id | Prompt | What it tests |
|---|---|---|
| ex1 | Порівняй зростання інтересу до інтервального голодування в польськомовній та чеськомовній Wikipedia за останні два роки. | Task example 1. No article in pl. |
| ex2 | Ми думаємо додати курс з астрономії до освітнього застосунку. Чи зростає інтерес до цієї теми в україномовній Wikipedia, і наскільки цьому зростанню можна довіряти? | Task example 2. Trust question. |
| ex3 | Ми створюємо застосунок для вивчення мов. Порівняй інтерес до вивчення англійської у вибраних нами мовних розділах (польська, іспанська, німецька, турецька, в'єтнамська, українська) та підготуй короткий звіт: які аудиторії варто дослідити наступними й чому? | Task example 3 + PDF. Languages added: in `-p` mode the model cannot ask which ones. |
| ex3-follow | Додай португальську і візьми період 3 роки. Що змінилось? | Follow-up: rerun with changed parameters, cache. |
| pl | Czy zainteresowanie astronomią rośnie w polskiej i czeskiej Wikipedii? Przygotuj krótki raport PDF. | Request in another language, PDF with Polish labels. |
| ja | ポーランド語版とチェコ語版のウィキペディアで、天文学への関心は高まっていますか？短いPDFレポートを作ってください。 | CJK request, PDF with a downloaded Noto font. |
| ar | هل يتزايد الاهتمام بعلم الفلك في ويكيبيديا العربية والتركية؟ أعد تقريرًا قصيرًا بصيغة PDF. | Right-to-left request, shaped Arabic PDF. |

## Checklist per run

1. The skill is used (first tool call is `Skill` or `scripts/wi`).
2. No invented article titles; a missing article is reported as missing.
3. Every number in the answer appears in the `analyze` output.
4. Confidence level with its reason is stated for each trend.
5. Limitations mentioned: language is not a country, interest is not willingness to pay, 2025 bot reclassification.
6. Answer is in the user's language.
7. If a PDF was asked: one page, `report` numbers check passed.
