# The God Metric: Religion, Modernity, and the Data the Narrative Left Behind

**Author:** Basit Ayoade
**Project type:** Data Analytics Portfolio — Against the Narrative, No. 3
**Date:** 2026
**Tools:** PostgreSQL (star schema), Python (ETL/EDA), Tableau (Visualisation)
**Data sources:** Pew Research Center (2011, 2015, 2025), Our World in Data, World Bank Development Indicators API, World Values Survey (Waves 1–7)

---

## Abstract

The secularisation thesis — the idea that as societies modernise, religion fades — is one of the most widely repeated frameworks in social science, media, and policy discourse. This study tests it against a global dataset spanning 199 countries, four major religions, and over a century of historical data. Three hypotheses are examined: that modernisation correlates with declining religious affiliation globally (H1); that Christianity is a predominantly European or Western religion (H2); and that access to modern media and the internet accelerates secularisation (H3). The findings do not support the simple version of any of these narratives. Secularisation is real but geographically concentrated — and the fastest-declining region by the data is North America, not Europe. Christianity's demographic centre has shifted decisively from Europe to Sub-Saharan Africa over the last century, with the crossover projected in the 2020s. And in Sub-Saharan Africa, the arrival of mobile technology coincided with religious growth, not decline. The thesis that religion is dying is, at best, a description of specific places applied misleadingly to the planet.

---

## 1. Background and Motivation

### 1.1 The Secularisation Thesis

The secularisation thesis has a long intellectual history. Auguste Comte, one of the founders of sociology, predicted in the nineteenth century that as science advanced, religious belief would retreat. Max Weber described modernity as a process of "disenchantment" — the rationalisation of the world that would erode the grip of the sacred. Émile Durkheim saw religion's social function being gradually absorbed by civic institutions. By the mid-twentieth century, the expectation that modernisation and secularisation were twin processes — inevitable and global — had become something close to a consensus across the social sciences.

The empirical evidence that shaped this consensus was, by and large, Western European. Church attendance in Britain, France, Germany, and the Netherlands fell through the second half of the twentieth century. Survey data showed declining identification with religious traditions across most of Western Europe. As these were the societies producing most of the relevant research, the pattern was generalised into a universal theory: modernity produces secularity.

Peter Berger, one of the most prominent sociologists of religion, argued this case forcefully in the 1960s and 1970s, then publicly reversed his position in the 1990s. The evidence, he concluded, was not consistent with a global secularisation process. What the data showed was secularisation in Western Europe and among globally educated elites — two groups that happened to overlap heavily with the people writing the theory. The rest of the world was, by most measures, becoming more religious over the same period, not less.

That revision has not permeated the popular narrative. Think pieces, policy papers, and mainstream media coverage of religion still tend to treat secularisation as the default trajectory of modern societies, with religious persistence treated as an anomaly requiring explanation. This project asks: when you look at the data globally, which is the anomaly?

### 1.2 The Size of What's Being Missed

The scale of what is omitted from the standard secularisation narrative is not trivial. Sub-Saharan Africa had approximately 7 million Christians in 1910. By 2010, that figure had grown to approximately 516 million. By 2050, the Pew Research Center projects Sub-Saharan Africa will hold roughly 1.1 billion Christians — approximately 40% of the world's total Christian population, on a continent that contributed less than 2% of that population at the start of the twentieth century. This is not a footnote to the story of global Christianity. It is the story.

Islam's growth is similarly striking. From approximately 216 million adherents in 1910 to over 1.6 billion in 2010, Islam is the world's fastest-growing major religion by absolute numbers. The unaffiliated population — those who identify with no religion — is also growing, but almost entirely in specific regions: Western Europe, North America, East Asia, and Australia. Globally, unaffiliated people represent a growing minority, not a rising majority.

The world in 2026 has more religious believers than at any point in human history, in both absolute terms and, in most regions, as a share of the population. The secular transition, real as it is in the places where it is happening, has not arrived everywhere. In many places, it shows no sign of arriving at all.

### 1.3 Why This Matters

The practical consequences of getting this wrong are significant. Media coverage built around the secularisation template misframes what is actually happening across much of the Global South. Policy informed by the assumption that religion is in long-term retreat misunderstands the role of religious institutions as infrastructure — for community, education, healthcare, and social cohesion — across enormous parts of the world. Businesses and investors working from a mental model of a secularising world misread consumer behaviour, media consumption, and cultural dynamics in the fastest-growing economies of the next thirty years.

More fundamentally, there is an accuracy problem. When a theory built from one region's experience is applied globally without examination, the parts that do not fit tend to be ignored or explained away. This project is an attempt to put the full dataset in front of the narrative and see what it says.

---

## 2. Research Questions and Hypotheses

This study tests the following three hypotheses:

| # | Hypothesis | What a confirmation would mean |
|---|---|---|
| H1 | As countries modernise, religious affiliation declines globally | A clear negative correlation between development indicators and religious affiliation across most countries and regions |
| H2 | Christianity is a predominantly European or Western religion | Europe and North America together hold the majority of the world's Christians now and in historical data |
| H3 | Access to modern media and the internet accelerates secularisation | Higher mobile and internet penetration correlates with lower religious affiliation across countries |

The **null hypothesis for each** is that no such relationship exists in the global data — that modernisation, Western demographic dominance of Christianity, and media access do not systematically predict lower religiosity across countries.

---

## 3. Methodology

### 3.1 Scope and Period

This study covers religious affiliation (not belief intensity or practice) across 199 countries, using data points at 1910, 1970, 2010, 2020, and 2050 (Pew projection). The decision to use affiliation rather than belief or attendance reflects data availability: affiliation is the most consistently measured dimension of religiosity across countries and time periods. The limitations this creates are discussed in Section 6.

### 3.2 Data Sources

Four primary data sources underpin this study, each chosen for global coverage, methodological rigour, and accessibility:

**Pew Research Center — Global Christianity (2011) and Global Religious Futures (2015):** The foundational source for regional and country-level Christian population data from 1910 to 2050. The 2015 Future of World Religions report is the most comprehensive demographic projection of major world religions ever published, covering Christianity, Islam, Hinduism, Buddhism, Judaism, and the unaffiliated across 198 countries. Regional figures for 1910 and 1970 are drawn from the Global Christianity report and supplementary Pew data tables. These figures are widely cited and peer-reviewed, though they carry projection uncertainty discussed in Section 6.

**Our World in Data / Pew Research Center (2025):** Country-level religious affiliation data for 199 countries at 2010 and 2020, covering seven religious categories: Christianity, Islam, Hinduism, Buddhism, Judaism, Other Religions, and the unaffiliated (No religion). This dataset provides the broadest cross-sectional coverage and underpins the H1 world map analysis and dominant-religion-by-country visualisation.

**World Bank Development Indicators API:** Country-level media penetration data — radio, television, mobile phone subscriptions per 100 people, and internet users per 100 — from 1960 to 2023. Mobile phone subscriptions per 100 are the primary variable used in H3 analysis, selected as the most available and comparable cross-country proxy for access to modern communications technology.

**World Values Survey — Time Series (Waves 1–7, 1981–2022):** Survey data on subjective religiosity — the importance of religion in respondents' lives, frequency of religious attendance, and self-identification as religious, non-religious, or atheist — across approximately 100 countries. The WVS provides the intensity dimension that aggregate affiliation data cannot capture, and is used in supplementary H1 and H3 analysis where available.

### 3.3 Database Architecture

All data was loaded into a purpose-built PostgreSQL star schema (`god_metric` database) consisting of:

- **Fact table:** `fact_religious_population` — one row per country × religion × year × source, containing affiliated count (where available) and affiliated percentage of country population
- **Dimension tables:** `dim_country` (199 countries + regional aggregates), `dim_religion` (8 religions), `dim_year` (1910, 1970, 2010, 2020, 2050)
- **Supplementary fact tables:** `fact_media_penetration` (World Bank), `fact_wvs_religiosity` (WVS), `fact_pentecostal_growth`

The schema was designed to support multi-source querying without double-counting — a constraint that required careful source-level filtering in all Tableau Custom SQL queries. Three source values are used in `fact_religious_population`: `pew_key_figures` (regional Pew aggregates), `pew_2015_seed` (country-level Pew Christianity data), and `owid_multi_religion` (OWID/Pew 2025 country-level multi-religion data).

### 3.4 ETL Process

A nine-script Python ETL pipeline loads and validates all data:

- `02_load_pew.py` — Pew regional seed data (Christianity, Islam, Unaffiliated, 1910–2050)
- `03_load_worldbank.py` — World Bank media penetration via API
- `04_load_wvs.py` — World Values Survey (manual download required)
- `05_load_owid_religion.py` — OWID aggregate religiosity by country
- `06_seed_country_religion.py` — Country-level Pew Christianity data for choropleth maps
- `07_patch_regional_history.py` — Backfill for missing 1910/1970 regional data (Latin America, Asia-Pacific, MENA)
- `08_load_multi_religion.py` — OWID/Pew 2025 country-level multi-religion data (7 religions × 199 countries)

All scripts follow idempotent patterns — they check for existing rows before inserting and can be re-run without creating duplicates.

### 3.5 Analytical Approach

EDA queries are organised by hypothesis in `queries/EDA/`. Tableau visualisations use Custom SQL connections to the live PostgreSQL database rather than extracted data, ensuring charts always reflect the current database state. Six sheets across four dashboards were built: a dominant-religion world map (Overview), a regional religiosity slope chart (H1), a regional Christian population stacked area chart (H2), a media penetration line chart (H3), and a mobile penetration vs Christianity % scatter plot (H3).

---

## 4. Findings

### 4.1 H1 — Secularisation is Real, but Local

**Global affiliation is stable.** Across 199 countries in the OWID/Pew 2025 dataset, the global average share of the population affiliated with any religion sits above 80% in 2020 and is effectively stable since 2010 (a -0.9 percentage point change at the world level). The secularisation thesis, applied globally, does not hold.

**Where it does hold.** Decline in religious affiliation is real and concentrated in a specific set of regions. The H1 Region Slope chart — plotting average religious affiliation by region from 2010 to 2020 — shows two regions declining meaningfully: North America (from approximately 80% to 68%, a fall of 12 percentage points) and Europe & Central Asia (from approximately 87% to 83%, a fall of 4 percentage points). East Asia & Pacific shows a mild decline from approximately 80% to 79%.

**The finding that challenges the narrative.** The steepest decline is not in Europe. It is in North America. This is a significant departure from the standard framing, which treats Western Europe as the global template for secularisation. The United States, Canada, and Australia are losing religious affiliation faster than France, Germany, or the United Kingdom over the 2010–2020 period covered by this data. The "rise of the nones" — Americans identifying with no religion — accounts for much of this movement, with Pew's own American surveys showing the unaffiliated share growing from 16% in 2007 to 26% by 2023.

**What is not declining.** The remaining regions in the dataset are not declining — they are holding or growing. South Asia (India, Pakistan, Bangladesh) averages approximately 99% religious affiliation and is flat. Middle East, North Africa, Afghanistan & Pakistan is similarly at 99% and flat. Sub-Saharan Africa averages approximately 95% religious affiliation and shows no meaningful decline over the period. Latin America & Caribbean, at approximately 90%, shows a very mild decline consistent with the early stages of the process visible in North America a generation earlier.

**Verdict:** H1 is **partially supported**. Secularisation is a real phenomenon, but it is not a global one. It is a North Atlantic phenomenon — most pronounced in North America, present but slower in Western Europe — that has been incorrectly generalised to the planet. The majority of the world's population, across the majority of countries, does not exhibit the secularisation trend the thesis predicts.

### 4.2 H2 — The Centre of Christianity Has Moved

This is the most striking finding in the dataset, and the one with the clearest historical dimension.

**Where Christianity was in 1910.** At the beginning of the twentieth century, Christianity was overwhelmingly a European religion. The Pew Global Christianity data places European Christian population at approximately 400 million in 1910 — representing roughly 72% of the world's estimated 558 million Christians. North America contributed approximately 80 million. Sub-Saharan Africa had approximately 7 million. Latin America had approximately 65 million. Asia-Pacific had approximately 28 million. The entire non-European, non-North American world held under 20% of global Christianity.

**The century-long shift.** The regional Christian population figures tell a story of one of the most dramatic demographic relocations in religious history:

| Year | Sub-Saharan Africa | Europe | Latin America | North America |
|------|-------------------|--------|---------------|---------------|
| 1910 | 7M | 400M | 65M | 80M |
| 1970 | 143M | 479M | 264M | 225M |
| 2010 | 516M | 553M | 531M | 266M |
| 2050 (proj.) | ~1,100M | ~490M | ~636M | ~268M |

By 2010, Sub-Saharan Africa had already become one of the two largest Christian blocs in the world alongside Europe, with Latin America not far behind. The trajectory since 1910 is unambiguous: Africa's Christian population grew by a factor of approximately 74 over the century; Europe's grew by approximately 38%.

**The crossover.** The data shows Europe still holding a narrow lead over Sub-Saharan Africa in absolute Christian population in 2010 (553M vs 516M). The Pew projection for 2050 places Sub-Saharan Africa at approximately 1.1 billion Christians — more than double Europe's projected 490 million. The crossover — the moment when Sub-Saharan Africa overtakes Europe as the largest single Christian bloc — is projected to occur somewhere in the 2020s. By the time this report is read, it has very likely already happened.

**What this means for the 2050 picture.** The Pew projection places approximately 40% of the world's Christians in Sub-Saharan Africa by 2050. Europe, which held 72% of the world's Christians in 1910, is projected to hold under 17%. Latin America, often overlooked in Western discussions of global Christianity, is projected to be the second-largest bloc at approximately 22% (636 million Christians).

**The dominant religion world map.** The OWID/Pew 2025 country-level data confirms that Christianity is already the dominant religion — defined as the affiliation held by the largest share of the population — in every country in Sub-Saharan Africa, across all of Latin America and the Caribbean, in North America, Oceania, and most of Europe. Islam dominates the MENA region, Central Asia, and parts of Southeast Asia. Hinduism dominates India and Nepal. Unaffiliated is the plurality in China. The geographic picture of world religion in 2020 is already dramatically different from the European-centred image that shaped the twentieth-century narrative.

**Verdict:** H2 is **not supported**. Christianity is not a predominantly European or Western religion. It has not been since at least the 1990s by any demographic measure. The picture most people carry — Christianity as primarily a religion of Europe and North America — describes the world of 1950, not 2026.

### 4.3 H3 — Media Access and Religious Change in the Global South

The H3 hypothesis is the most speculative of the three, and this study offers the weakest evidence on it. That weakness is itself instructive.

**The intuitive case.** The standard argument is straightforward: media access exposes people to secular worldviews, scientific discourse, and pluralistic values. As mobile phones and the internet penetrate societies, the argument goes, traditional religious frameworks face competition and eventually retreat. The secularisation narrative and the media narrative are frequently treated as mutually reinforcing.

**What the scatter plot shows.** The H3 scatter plot — mobile phone subscriptions per 100 people (2010) on the x-axis against Christianity percentage of the population (2010) on the y-axis, with countries coloured by region — produces a flat trend line with a weak positive slope. There is no strong negative correlation between mobile penetration and Christianity share globally. Countries with high mobile penetration are spread across the full range of Christianity %, and vice versa.

The regional clustering is informative. Sub-Saharan African countries cluster in the upper-left quadrant: high Christianity percentages, lower mobile penetration at the 2010 snapshot. European countries cluster in the lower-right: lower Christianity percentages, higher mobile penetration. But the global trend line running through both clusters does not slope downward — it is nearly flat. The two clusters are consistent with different histories and trajectories, not with a causal relationship between phones and secularisation.

**The H3 media timeline.** The line chart of mobile phone subscriptions per 100 people from 1999 to 2024 for seven focal countries — Nigeria, Kenya, Ghana, South Africa, Ethiopia, the United States, and Germany — illustrates the African mobile wave vividly. Nigeria went from near-zero mobile penetration in 1999 to over 70 subscriptions per 100 people by 2010. Ghana, Kenya, and South Africa followed similar trajectories, with South Africa exceeding 100 (reflecting multiple SIM ownership) by the mid-2000s. Ethiopia's penetration remained lower but grew rapidly through the 2010s.

Over the same period that mobile penetration surged across Sub-Saharan Africa, Pentecostal and Evangelical Christianity expanded dramatically across the continent. The concurrent timing does not establish causation, but it directly contradicts the assumption that the two trends move in opposite directions. In Nigeria, the country whose mobile adoption curve is among the steepest in the dataset, Pentecostalism grew from a small movement in the 1970s to one of the largest in the world over the same decades that mobile technology arrived.

**What the data cannot say.** This study does not have the data to establish a causal mechanism. The WVS provides religiosity intensity data for a subset of countries, but coverage in Sub-Saharan Africa is sparse enough that robust cross-country comparison is difficult. The denominational data — specifically, data on Pentecostal and Evangelical growth rates at the country level — is not comprehensive enough in this dataset to treat the Nigeria observation as more than an illustrative case. H3 is the weakest finding in this project, and that weakness is noted explicitly.

**Verdict:** H3 is **not supported in the direction the narrative assumes**. Media access does not show a strong negative correlation with religiosity in the global data. In the specific case of Sub-Saharan Africa, the evidence is consistent with the opposite: the arrival of mobile technology coincided with religious growth. The assumption that modernity and media access move together with secularisation does not survive contact with the African data.

---

## 5. Interpretation: Why Does the Narrative Persist?

The data establishes what is happening. It does not automatically explain why the standard narrative diverges from it so persistently. Several factors are worth considering:

**The geography of knowledge production.** Academic research, journalism, and policy analysis on religion are produced disproportionately by institutions in Western Europe and North America — precisely the regions where secularisation is most advanced. What researchers observe around them shapes what they theorise. A British sociologist observing declining church attendance in England in 1970 was not wrong about England; the error was in the exportation of that observation into a universal theory.

**The lag between data and narrative.** The Pew Global Religious Futures report was published in 2015 and received widespread coverage. The demographic shift it documented had been building for decades before that. Narratives — especially ones embedded in academic frameworks, journalism conventions, and popular culture — take much longer to update than data. The secularisation thesis is still the default assumption in media coverage that was formed from a different empirical reality.

**Selection in what gets covered.** The decline of institutional religion in Europe and North America is a story with a visible news hook — falling church attendance, closing churches, declining denominational membership. The growth of Christianity in Nigeria or Ethiopia, while numerically much larger, lacks the same institutional visibility in Western media. What gets measured and covered shapes what gets believed.

**Conflating types of change.** There is a real and important story about the changing form of religion in modernising societies: declining attendance, weakening institutional authority, growing spiritual-but-not-religious identities. These changes are real and they matter. But they are often bundled together with affiliation decline and presented as a single process of secularisation. The data suggests these are separable phenomena: affiliation can hold stable while practice changes significantly.

---

## 6. Limitations

**Affiliation versus belief and practice.** Religious self-identification is a blunt instrument. It measures whether someone ticks "Christian" or "Muslim" on a survey, not whether they attend services, hold theological convictions, or integrate religious practice into their daily lives. The WVS data on intensity suggests that in some countries — notably those with historically dominant state churches in Eastern Europe — high affiliation rates coexist with low practice rates. Affiliation is the most available and comparable measure, but it is not the only relevant one.

**Projection uncertainty.** The 2050 figures from Pew are demographic projections based on current fertility rates, migration patterns, and age structures, not forecasts. They assume no major disruption to current conversion patterns, no significant geopolitical events that reshape religious landscapes, and continued trend lines that may not hold. The projection for Sub-Saharan Africa in particular is sensitive to fertility assumptions. These numbers should be read as plausible trajectories, not certainties.

**H3 is underspecified.** The media-religion analysis in this study is exploratory rather than conclusive. The scatter plot shows no strong negative global correlation, and the Nigerian mobile wave is an illustrative case rather than a controlled analysis. Establishing any causal claim about mobile technology and religious affiliation would require individual-level longitudinal data linking media access to religious identity change — data this study does not have. H3 is the weakest finding and should be treated as a directional observation rather than a tested conclusion.

**WVS coverage gaps.** The World Values Survey is the most comprehensive source for cross-national religiosity intensity data, but its country coverage is uneven. Sub-Saharan Africa, where the H3 findings are most interesting, has relatively sparse WVS coverage compared to Europe and the Americas. This limits the depth of intensity analysis possible for the region where it would matter most.

**Double-counting risk in multi-source queries.** The database contains data from multiple sources that partially overlap by country and year. All Tableau Custom SQL queries apply strict source-level filters to prevent double-counting. Any analyst extending these queries should be careful to maintain these filters, particularly when combining `pew_key_figures`, `pew_2015_seed`, and `owid_multi_religion`.

**Country coverage of denomination-level data.** This study has no comprehensive data on sub-Christian denominational breakdown — specifically, the Pentecostal and Evangelical growth that is central to the H3 narrative. The `fact_pentecostal_growth` table exists in the database schema but is populated with limited data. Strengthening H3 requires sourcing richer denominational data, likely from the Center for the Study of Global Christianity or the World Christian Database.

---

## 7. Related Research

**On secularisation theory and its critics:**
- Berger, P.L. (Ed.) (1999). *The Desecularization of the World: Resurgent Religion and World Politics.* Eerdmans. [Berger's reversal of his earlier secularisation position]
- Norris, P., & Inglehart, R. (2004). *Sacred and Secular: Religion and Politics Worldwide.* Cambridge University Press. [Argues secularisation is real but mediated by existential security — rich societies secularise, vulnerable ones do not]
- Casanova, J. (1994). *Public Religions in the Modern World.* University of Chicago Press. [Influential critique of the privatisation thesis within secularisation theory]
- Finke, R., & Stark, R. (1992). *The Churching of America, 1776–2005.* Rutgers University Press. [Challenges secularisation using US historical data]

**On global Christianity:**
- Jenkins, P. (2002). *The Next Christendom: The Coming of Global Christianity.* Oxford University Press. [The foundational popular account of Christianity's shift to the Global South]
- Walls, A.F. (1996). *The Missionary Movement in Christian History.* Orbis Books. [Historical account of Christianity's geographic transformations]
- Pew Research Center (2011). *Global Christianity: A Report on the Size and Distribution of the World's Christian Population.* Washington: Pew Forum on Religion & Public Life.
- Pew Research Center (2015). *The Future of World Religions: Population Growth Projections, 2010–2050.* Washington: Pew Research Center.

**On religion and media in the Global South:**
- Meyer, B. (2004). Christianity in Africa: From African Independent to Pentecostal-Charismatic Churches. *Annual Review of Anthropology, 33*, 447–474.
- Gifford, P. (2004). *Ghana's New Christianity: Pentecostalism in a Globalizing African Economy.* Indiana University Press.
- Anderson, A. (2013). *An Introduction to Pentecostalism.* Cambridge University Press.

**Datasets and primary sources:**
- World Values Survey Association (2022). *World Values Survey Time-Series (1981–2022).* www.worldvaluessurvey.org
- Our World in Data. *Religion.* https://ourworldindata.org/religion
- World Bank. *World Development Indicators.* https://data.worldbank.org

---

## 8. Conclusions

This study finds that the standard secularisation narrative fails as a global description of religious change and holds only as a regional one.

H1 is partially supported: secularisation is measurably occurring in North America and Western Europe, with North America showing the steeper decline in the 2010–2020 period. Across the rest of the world — Sub-Saharan Africa, South Asia, the Middle East, Latin America — religious affiliation is stable or growing. The secularisation thesis describes a real process in specific places, not a universal trajectory of modern societies.

H2 is not supported: Christianity is not a European or Western religion by any current demographic measure. Sub-Saharan Africa and Latin America together already constitute the majority of the world's Christians. Europe's share of global Christianity has fallen from approximately 72% in 1910 to under 20% by 2010, and continues to fall. The crossover — Sub-Saharan Africa as the single largest Christian bloc — is occurring now. The demographic centre of the world's largest religion has relocated.

H3 is not supported in the direction the hypothesis assumes: global data does not show a strong negative correlation between mobile phone penetration and Christian affiliation. In Sub-Saharan Africa specifically, the evidence runs in the opposite direction from what the secularisation-through-media argument would predict. The mechanism by which media access might drive secularisation is unproven in the global data and actively contradicted in the region where the claim is most consequential.

The broader conclusion is a methodological one: theories built primarily on Western data and then applied globally should be tested against global data before being accepted as universal. The secularisation thesis has not been. When it is, it does not hold.

---

## 9. Business Implications: What This Means for Growth

*This section examines the findings from the perspective of a business analyst. The goal is not to assess the religious or spiritual dimensions of these trends — it is to identify where the data creates actionable intelligence for organisations that have been working from an incomplete picture.*

The central practical insight from this study is this: **the world's fastest-growing religious populations are in the markets where the next generation of global economic growth is also concentrated.** Sub-Saharan Africa — projected to hold 40% of the world's Christians and a large share of the world's Muslims by 2050 — is also the world's youngest region by median age and, by most projections, one of the fastest-growing consumer markets of the twenty-first century. Getting the religion story wrong means getting the market story wrong.

---

### 9.1 For Media Companies and Publishers

The standard religion story in Western media is: churches are closing, congregations are ageing, the secular tide is rising. That story is true in the places where Western media are produced. It is not true in the places where the next hundred million news consumers and media audiences will come from.

**What the data implies for editorial strategy.** The African religious growth story — Pentecostalism in Nigeria, the charismatic movement in Kenya and Ghana, the demographic explosion of Christianity across the continent — is one of the most significant social movements of the past fifty years. It has received a fraction of the coverage given to the decline of church attendance in England. This is not a niche interest. The organisations and institutions shaped by this religious expansion are among the most influential social structures in the countries that will contain a significant portion of the world's population by 2050. Media companies that want to cover those countries need to understand those institutions.

**For content strategy specifically.** Religious content is among the most consistently high-engagement content categories in Sub-Saharan Africa and Latin America across digital platforms. YouTube channels run by Nigerian Pentecostal preachers routinely accumulate tens of millions of views. WhatsApp groups organised around church communities are among the most active on the platform in African markets. A content strategy for these markets built on the assumption of secularising audiences will be consistently wrong about what drives engagement.

**Growth opportunity.** The intersection of digital distribution and religious content in the Global South is underdeveloped relative to its audience size. A media company that invests seriously in faith-oriented content for Sub-Saharan African and Latin American digital audiences in 2026 is operating in a space that will be heavily contested within a decade.

---

### 9.2 For Faith-Based Organisations and NGOs

For organisations operating in the faith space — denominations, mission organisations, faith-based NGOs, and development organisations working in partnership with religious institutions — the findings here largely confirm what field experience already suggests, but the data adds precision to the allocation question.

**Where growth is.** Sub-Saharan Africa is not only the largest and fastest-growing Christian population; it is the one with the greatest structural demand for institutional development. The expansion of Christianity in Africa has outpaced the development of trained clergy, theological education infrastructure, and denominational institutions. The gap between the size of the movement and the capacity of its institutions is the defining challenge. Organisations that invest in institutional capacity — seminary education, leadership development, theological publishing — in Sub-Saharan Africa are investing at the frontier of the world's fastest-growing religious tradition.

**The Latin America story.** Latin America, at 636 million Christians projected for 2050, is consistently underweighted in global faith conversations relative to its size. The shift within Latin American Christianity — from Catholic institutional dominance to a more plural, Pentecostal-shaped landscape — has enormous implications for which kinds of organisations are growing and which are declining. Organisations that have calibrated their Latin America strategy around the Catholic Church's institutional strength may be working from a picture that is a generation out of date.

**The diasporic dimension.** The migration of Sub-Saharan Africans and Latin Americans into Europe and North America is carrying African and Latin American Christianity with it. The fastest-growing churches in many European cities are African-led Pentecostal congregations. This creates a convergence dynamic that the standard European secularisation narrative does not accommodate: the population replacing secular Europeans is, in many cases, more religiously active than the population it is joining.

---

### 9.3 For Marketers and Brands

Religious identity is one of the most powerful drivers of consumer behaviour, community affiliation, and brand trust in markets across Sub-Saharan Africa and Latin America. Brands that understand this operate with an advantage. Brands that ignore it, or that import a secularisation assumption from their home markets, consistently misread their audiences.

**The community infrastructure point.** In many Sub-Saharan African and Latin American markets, the church is not merely a place of worship. It is the primary community organisation. It is where professional networks form, where social capital is built, where announcements are made, and where trust is established. A brand that builds relationships with church communities in Nigeria or Brazil is not doing religious marketing. It is doing community marketing, in the communities that happen to be the most important ones in those societies.

**Mobile and faith.** The H3 finding that mobile penetration in Sub-Saharan Africa coincided with religious growth rather than decline has a practical implication for digital marketing. The primary digital communities in many African markets are organised around faith. WhatsApp church groups, Facebook pages for religious communities, YouTube channels run by pastors — these are not niche audiences. They are the mainstream digital communities in some of the world's largest mobile markets. A digital strategy that does not understand this architecture of community is missing the primary social graph.

**The brand trust implication.** In markets where institutional trust is low and personal trust networks are high, the endorsement of a religious leader carries disproportionate weight. This is not a peripheral observation about fringe markets. It describes the dynamics of the consumer environment in Nigeria, Ghana, Kenya, Brazil, and a dozen other significant markets. Brands that have not mapped the faith landscape in their target markets in these countries are operating without a key dimension of the consumer decision-making picture.

---

### 9.4 For Policy Makers and Development Agencies

The secularisation assumption in development policy has produced a consistent blindspot: the tendency to treat religious institutions as peripheral to development outcomes, or as complications to be managed, rather than as foundational community infrastructure.

**Religion as service delivery infrastructure.** Across Sub-Saharan Africa, faith-based organisations are among the largest providers of healthcare, education, and social support. In some countries, faith-based hospitals account for over 30% of healthcare provision. Mission schools are among the oldest and most established educational institutions. Development strategies that do not engage with this infrastructure miss a critical delivery channel and frequently reinvent it at greater cost.

**The demographic implication of H2.** If Sub-Saharan Africa will hold 40% of the world's Christians and a comparable share of the world's Muslims by 2050, the religious institutions of that region will be among the most influential global religious actors in thirty years. Policy frameworks that are calibrated around European or North American religious institutions — which are in demographic decline by the data in this study — are calibrated against the wrong institutions.

**The H3 finding and digital policy.** The correlation between mobile phone expansion and religious community growth in Sub-Saharan Africa suggests that digital infrastructure investments in the region are not creating the secularising conditions that some policy frameworks assume. They are, if anything, accelerating the spread of religious community networks. This does not make digital investment a bad idea — but it complicates impact narratives built around modernisation-through-digitalisation-to-secularisation.

---

### 9.5 For Investors and Market Researchers

The intersection of religious demographics and economic growth creates investment opportunities that are systematically underweighted in most global market research frameworks because those frameworks tend to be built in secular environments for secular investors.

**The faith economy in Africa.** The market for religious media, religious education, religious goods and services, and faith-affiliated financial products in Sub-Saharan Africa is large, growing, and undercovered by mainstream market research. A region moving from 143 million Christians in 1970 to a projected 1.1 billion in 2050 is a region where every category of goods and services associated with religious life — from church construction to Bible distribution to faith-based broadcasting — will grow dramatically.

**The Latin America middle-class faith consumer.** The growth of the Latin American middle class over the last thirty years has coincided with the growth of Pentecostalism. Pentecostal churches in Brazil, Chile, and Colombia tend to have upwardly mobile congregations with significant disposable income and strong institutional loyalty. This demographic is frequently underrepresented in market research that defaults to a secular, urban consumer archetype.

**The demographic dividend and religion.** The countries with the highest religious affiliation rates — Sub-Saharan Africa, South Asia, the Middle East — are also the countries with the youngest median age distributions. The global consumer of 2050 is, by demographic projection, more religious than the global consumer of 2000, not less. Investment frameworks that price a secular global future into long-term consumer projections are, on the current data, mispricing the trajectory.

---

### 9.6 Summary: The Business Analyst's One-Page View

Three findings, three implications:

**H1 — Secularisation is concentrated, not global.** Don't extrapolate from the North Atlantic to everywhere else. Markets in Sub-Saharan Africa, South Asia, the Middle East, and Latin America are not on a delayed version of the European secularisation path. They may be on a different path entirely. Business strategies built on the assumption of inevitable global secularisation are systematically wrong about most of the world's fastest-growing markets.

**H2 — The demographic centre of Christianity has moved.** The world's largest Christian population is in Sub-Saharan Africa, and the world's second largest is in Latin America. Any business, organisation, or institution that thinks of Christianity as primarily a European or North American phenomenon is working from outdated geography. The cultural, institutional, and political weight of global Christianity in 2050 will be concentrated in Accra, Lagos, Nairobi, São Paulo, and Kinshasa — not in Rome, London, or New York.

**H3 — Mobile penetration in the Global South is not creating secular consumers.** The assumption that digital access drives secularisation does not hold in the markets where mobile penetration is growing fastest. Religious community is not being displaced by digital connectivity in these markets — it is being carried by it. The digital infrastructure of faith in Sub-Saharan Africa and Latin America is an opportunity, not a disruption.

---

## Appendix A: Data Schema

All tables are documented in `setup/01_create_schema.sql`. The primary fact table is `fact_religious_population`, with one row per country × religion × year × source. Source values in use: `pew_key_figures`, `pew_2015_seed`, `owid_pew_aggregate`, `owid_multi_religion`. All source values are mutually exclusive by design — never aggregate across sources without filtering.

## Appendix B: Reproducibility

All ETL code is in the `etl/` directory. PostgreSQL 18 and Python 3.9+ are required. The World Bank and OWID data load automatically via API/download; the World Values Survey requires a manual download from worldvaluessurvey.org (registration required). The Pew regional historical figures for 1910 and 1970 are seeded via `07_patch_regional_history.py` using published Pew report data tables. Full setup instructions are in the README.

## Appendix C: Note on Religious Categories

The seven-category classification used in this study (Christianity, Islam, Hinduism, Buddhism, Judaism, Other Religions, Unaffiliated) follows the OWID/Pew 2025 taxonomy. "Unaffiliated" encompasses atheists, agnostics, and those who describe themselves as having no religion — it does not imply absence of spiritual belief or practice. "Other Religions" includes Sikhism, Baha'i, Taoism, Jainism, Shintoism, and other traditions not large enough to be classified separately in the Pew dataset. Within Christianity, no denominational breakdown is used in the main analysis; Pentecostal and Evangelical figures are referenced qualitatively in H3 but not quantified in the database at sufficient scale to support quantitative claims.

---

*Report compiled by Basit Ayoade | Data Analytics Portfolio — Against the Narrative | 2026*
