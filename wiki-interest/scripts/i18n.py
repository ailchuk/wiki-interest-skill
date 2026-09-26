"""Fixed texts for charts, reports and confidence reasons (en, uk). Other languages fall back to en."""

LANGS = ("en", "uk")

TEXT = {
    "en": {
        "trend_title": "Monthly views, index: previous 12 months = 100",
        "last12": "last 12 months",
        "growth_title": "Growth: last 12 months vs previous 12",
        "growth": "Raw",
        "growth_clean": "Without spikes",
        "adj_growth": "Adjusted for Wikipedia traffic",
        "HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW",
        "lang": "Lang", "article": "Article", "vpd": "Views/day", "raw": "Growth",
        "clean": "W/o spikes", "adj": "Adjusted", "steady": "Months up", "conf": "Confidence",
        "missing": "no article", "no_views": "no views",
        "findings": "Findings", "recommendation": "Recommendation", "next_steps": "Next steps", "assumptions": "Assumptions", "limitations": "Limitations",
        "data_table": "Data",
        "question": "Question",
        "generated": "Generated {date} with wiki-interest. Data: Wikimedia Pageviews API, Wikidata.",
        "reproduce": "Reproduce",
        "a_topic": "Topic = these Wikipedia articles (Wikidata {qid}): {articles}.",
        "a_articles": "Topic = these Wikipedia articles: {articles}.",
        "a_period": "Period: {start} to {end}, complete months only. Growth = last 12 months vs the previous 12 (removes seasonality).",
        "a_filters": "Human views only (bots and crawlers excluded), all platforms (desktop, mobile web, app).",
        "a_spikes": "Spike = a day with over 3x its usual views (median of +-14 days); 'without spikes' replaces such days with the usual level.",
        "a_adjusted": "'Adjusted' = change in the article's share of all views of that Wikipedia, so an overall traffic decline is not read as lost interest.",
        "l_interest": "Views measure curiosity, not willingness to pay.",
        "l_country": "A language edition is not a country: readers of one language live in many countries, and many people read other languages' Wikipedias.",
        "l_proxy": "One article is a proxy for the topic; related articles and other sources (search, AI assistants, video) are not covered.",
        "l_low": "Low volume in {langs}: numbers are noisy, treat the trend as unconfirmed.",
        "l_missing": "No article in {langs}: interest there cannot be measured this way.",
        "l_spikes": "Spike days (news, events) affect {langs}: see 'without spikes'.",
        "l_appeared": "Article created or renamed during the period in {langs}: growth is not comparable.",
        "l_bots": "In 2025 Wikimedia improved bot detection and reclassified March-August 2025 traffic; earlier 'human' views may still include bots, so part of a decline across 2025 can be a counting change.",
    },
    "uk": {
        "trend_title": "Перегляди за місяць, індекс: попередні 12 місяців = 100",
        "last12": "останні 12 місяців",
        "growth_title": "Зростання: останні 12 місяців проти попередніх 12",
        "growth": "Сире",
        "growth_clean": "Без сплесків",
        "adj_growth": "З поправкою на трафік вікі",
        "HIGH": "ВИСОКА", "MEDIUM": "СЕРЕДНЯ", "LOW": "НИЗЬКА",
        "lang": "Мова", "article": "Стаття", "vpd": "Перегл./день", "raw": "Зростання",
        "clean": "Без сплесків", "adj": "З поправкою", "steady": "Міс. вище", "conf": "Довіра",
        "missing": "статті немає", "no_views": "немає переглядів",
        "findings": "Висновки", "recommendation": "Рекомендація", "next_steps": "Наступні кроки", "assumptions": "Припущення", "limitations": "Обмеження",
        "data_table": "Дані",
        "question": "Питання",
        "generated": "Згенеровано {date} навичкою wiki-interest. Дані: Wikimedia Pageviews API, Wikidata.",
        "reproduce": "Відтворити",
        "a_topic": "Тема = ці статті Вікіпедії (Wikidata {qid}): {articles}.",
        "a_articles": "Тема = ці статті Вікіпедії: {articles}.",
        "a_period": "Період: {start} - {end}, лише завершені місяці. Зростання = останні 12 місяців проти попередніх 12 (прибирає сезонність).",
        "a_filters": "Лише перегляди людей (боти й краулери виключені), усі платформи (десктоп, мобільний сайт, застосунок).",
        "a_spikes": "Сплеск = день, коли переглядів більш ніж утричі більше за звичайне (медіана +-14 днів); «без сплесків» замінює такі дні звичайним рівнем.",
        "a_adjusted": "«З поправкою» = зміна частки статті серед усіх переглядів цієї Вікіпедії, щоб загальне падіння трафіку не читалося як втрата інтересу.",
        "l_interest": "Перегляди показують цікавість, а не готовність платити.",
        "l_country": "Мовний розділ - не країна: читачі однієї мови живуть у різних країнах, і багато людей читають Вікіпедію іншими мовами.",
        "l_proxy": "Одна стаття - лише проксі теми; пов'язані статті й інші джерела (пошук, AI-асистенти, відео) не враховані.",
        "l_low": "Мало переглядів у {langs}: цифри шумні, тренд не підтверджений.",
        "l_missing": "Немає статті в {langs}: інтерес там так виміряти не можна.",
        "l_spikes": "На {langs} впливають сплески (новини, події): див. «без сплесків».",
        "l_appeared": "Статтю створили або перейменували в цей період у {langs}: зростання не можна порівнювати.",
        "l_bots": "У 2025 Wikimedia покращила виявлення ботів і перекласифікувала трафік за березень-серпень 2025; раніші «людські» перегляди можуть містити ботів, тож частина падіння протягом 2025 може бути зміною обліку.",
    },
}

REASONS = {
    "en": {
        "low_volume": "low volume: {vpd:.1f} views/day (under {min} = LOW)",
        "appeared": "no views in the first {months} month(s): article created or renamed during the period",
        "no_baseline": "no views in the previous 12 months: growth undefined",
        "spike_driven": "growth comes from spike days: {growth} raw vs {clean} without spikes",
        "volume_ok": "solid volume: {vpd:.0f} views/day",
        "moderate_volume": "moderate volume: {vpd:.0f} views/day (HIGH needs {min}+)",
        "steady_up": "{n}/12 months above the same month a year earlier",
        "steady_down": "{n}/12 months below the same month a year earlier",
        "steady_flat": "without spikes the change is within +-5%",
        "unsteady_up": "only {n}/12 months above the same month a year earlier (HIGH needs {need})",
        "unsteady_down": "only {n}/12 months below the same month a year earlier (HIGH needs {need})",
        "agree": "same direction after adjusting for total Wikipedia traffic",
        "disagree": "trend differs after adjusting for total Wikipedia traffic: {clean} without spikes, {adj} adjusted, whole Wikipedia {wiki}",
    },
    "uk": {
        "low_volume": "мало переглядів: {vpd:.1f} за день (менше {min} = НИЗЬКА)",
        "appeared": "перші {months} міс. без переглядів: статтю створили або перейменували в цей період",
        "no_baseline": "немає переглядів у попередні 12 місяців: зростання не визначене",
        "spike_driven": "зростання дали сплески: {growth} сире проти {clean} без сплесків",
        "volume_ok": "достатній обсяг: {vpd:.0f} переглядів за день",
        "moderate_volume": "середній обсяг: {vpd:.0f} переглядів за день (для ВИСОКОЇ треба {min}+)",
        "steady_up": "{n}/12 місяців вищі, ніж той самий місяць роком раніше",
        "steady_down": "{n}/12 місяців нижчі, ніж той самий місяць роком раніше",
        "steady_flat": "без сплесків зміна в межах +-5%",
        "unsteady_up": "лише {n}/12 місяців вищі, ніж роком раніше (для ВИСОКОЇ треба {need})",
        "unsteady_down": "лише {n}/12 місяців нижчі, ніж роком раніше (для ВИСОКОЇ треба {need})",
        "agree": "напрям той самий після поправки на загальний трафік вікі",
        "disagree": "після поправки на трафік вікі тренд інший: без сплесків {clean}, з поправкою {adj}, уся вікі {wiki}",
    },
}


def lang_or_en(lang):
    return lang if lang in LANGS else "en"


def t(lang, key, **kw):
    s = TEXT[lang_or_en(lang)][key]
    return s.format(**kw) if kw else s


def pct(x):
    """0.123 -> '+12%'; None -> 'n/a'. Integers only, so reports and checks agree."""
    if x is None:
        return "n/a"
    v = round(x * 100)
    return "0%" if v == 0 else f"{v:+d}%"


def reason(code, params, lang="en"):
    p = dict(params)
    for k in ("growth", "clean", "adj", "wiki"):
        if k in p:
            p[k] = pct(p[k])
    if code in ("steady", "unsteady"):
        code = f"{code}_{ {1: 'up', -1: 'down', 0: 'flat'}[p['dir']] }"
    return REASONS[lang_or_en(lang)][code].format(**p)
