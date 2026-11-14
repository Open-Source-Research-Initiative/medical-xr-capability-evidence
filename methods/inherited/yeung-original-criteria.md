**Yeung et al. (2021): Original Bibliometric Search Criteria and Analysis Methods**

Extracted on 11 November 2026 from the original PDF saved in Zotero. This document describes the published study's methods; proposed changes for the follow-up are identified separately. Page references below refer to the PDF's numbered pages.

Source: Yeung AWK et al. *Virtual and Augmented Reality Applications in Medicine: Analysis of the Scientific Literature*. Journal of Medical Internet Research. 2021;23(2):e25499. DOI: 10.2196/25499. Zotero item QRCV9JBW; attachment UDCMTX27. [Open the saved Zotero paper](https://www.zotero.org/colelyons/search/Virtual%20and%20Augmented%20Reality%20Applications%20in%20Medicine/everything/items/QRCV9JBW/attachment/UDCMTX27/reader).

**Original retrieval criteria — PDF page 3**

| Criterion | What the paper reports |
|---|---|
| Database | Web of Science Core Collection |
| Search date | September 16, 2020 |
| Search field | TOPIC; described by the authors as searching titles, abstracts and keywords |
| Technology terms | "virtual reality*" OR "augmented reality*" OR "mixed reality*" OR "computer-mediated reality*" |
| Medical terms | medic* OR illness* OR disease* OR health* OR pharma* |
| Relationship between term groups | AND: a record had to match the technology group and the medical group in the queried fields |
| Language restrictions | None |
| Publication-type restrictions | None |
| Other restrictions | The authors state that no additional restrictions were used |
| Prespecified date range | No explicit starting-year filter is reported; 1992–2020 describes the retrieved records |
| Geographic, population, intervention or study-design eligibility | No separate criteria are reported |
| Clinical relevance screening / full-text eligibility assessment | No separate manual screening procedure is described in the published methods |

The exact published search expression, with straight quotation marks substituted for typographic quotation marks, is:

```text
TOPIC: ("virtual reality*" OR "augmented reality*" OR "mixed reality*" OR "computer-mediated reality*") AND TOPIC: (medic* OR illness* OR disease* OR health* OR pharma*)
```

Do not silently add AI, metaverse, spatial computing, device names or new medical terms to the replication query. Those belong in a separately documented extension.

**Original corpus — results, not eligibility criteria**

The search returned 8,399 publications dated 1992–2020. The 2020 count was 802 through the September 16 search date, so 2020 was incomplete. The corpus included original articles, reviews, proceedings papers, editorials and meeting abstracts. It was not restricted to patient studies, randomized trials, clinical effectiveness studies or immersive headsets. These facts follow from the broad retrieval approach; the paper does not report an additional eligibility screen. [PDF p. 3.]

Document-type overlap matters: Web of Science tagged 2,213 records as proceedings papers; 305 were also tagged as original articles. The authors reported 1,908 proceedings papers separately after accounting for that overlap. Do not sum the raw overlapping database tags as if they were mutually exclusive. [PDF p. 3.]

**Original data extraction and software — PDF page 3**

| Step | Reported method |
|---|---|
| Basic publication and citation counts | Web of Science Analyze and Create Citation Report functions |
| Export | Full records of the retrieved publications |
| Term and keyword mapping | VOSviewer 1.6.15 |
| Additional bibliometrics and trend topics | Bibliometrix 3.0 through its Biblioshiny web interface |
| Statistical tests | SPSS 26.0 |

The paper does not specify the full export-field manifest, all Core Collection indexes selected, detailed name/term cleaning rules, or every software setting. These should be recorded explicitly in a follow-up rather than assumed to be recoverable from the article.

**Original mapping thresholds and selection rules**

| Analysis | Input and inclusion rule | Counting/display rule | Source |
|---|---|---|---|
| VOSviewer term map | Phrases in titles and abstracts appearing in at least 0.5% of publications; reported as 42 of 8,399 | Repeated appearances within one publication count once; circle size represents frequency, color citations per publication, and distance co-occurrence relationships | p. 3; Figure 2, p. 7 |
| VOSviewer author-keyword density map | Author keywords appearing in at least 0.1% of publications; reported as 9 of 8,399 | Higher-frequency areas appear red and lower-frequency areas yellow | p. 3; Figure 4, p. 9 |
| Display exclusions in keyword density map | "virtual reality," "augmented reality," and "mixed reality" omitted because they were the principal search terms | A visualization exclusion, not exclusion of publications from the corpus | Figure 4, p. 9 |
| Biblioshiny Trend Topics | Abstract words appearing in at least 5 publications | Each year limited to 5 words | p. 3 |
| Medical-condition table | Conditions mentioned in at least 0.5% of publication titles/abstracts; reported as 42 of 8,399 | Frequency and citations per publication reported | p. 6; Table 5, p. 8 |
| Author-keyword rankings | Top 10 keywords by frequency and top 10 by citations per publication | Two separate rankings | Table 6, p. 10 |
| Simulation subset | Papers mentioning "simulation" in their keywords | Top 10 most cited papers presented | p. 9; Table 7, p. 11 |

The counts 42 and 9 reflect the original corpus. A percentage-based replication on a larger corpus should retain the percentages and document the resulting count thresholds and rounding. Keeping 42 and 9 regardless of corpus size would be a different threshold policy.

**Original indicators, grouping rules and statistical comparisons**

| Item | Definition or rule in the paper | Source |
|---|---|---|
| Publication activity | Annual publications; publication counts/shares by authors, organizations, countries, journals and research areas; document-type composition | pp. 3–6 |
| Citation indicators | Citation counts and citations per publication (CPP); H-index and M-index in the author/organization tables | pp. 3–6 |
| M-index | H-index divided by the number of years since the first publication within the dataset | Table 1, p. 4; Table 2, p. 5 |
| Productive entities | Top 10 authors, organizations, countries and journals shown | Tables 1–4, pp. 4–6 |
| International collaboration | Single-country publications (SCP) and multiple-country publications (MCP); percentage MCP/(MCP+SCP) | Table 3, p. 5 |
| Country attribution for SCP/MCP | Bibliometrix used the corresponding author's country; SCP+MCP therefore need not equal the separate total publication count attributed to a country | Table 3 footnote, p. 5 |
| Core journals | Most productive journals collectively accounting for one-third of all articles, using Bradford's law; 85 core and 3,565 noncore journals resulted | p. 5 |
| Research-area source | Web of Science journal research-area assignments | p. 6 |
| Mutually exclusive research-area comparison | Reverse priority order across the six largest areas: Rehabilitation, Psychology, Surgery, Neurosciences/Neurology, Engineering, Computer Science; remaining records assigned to Others | p. 6; the first three priorities are spelled out and the rest follow the stated reverse ordering |
| CPP comparison: original articles versus reviews | Two-sample t test | p. 3 |
| CPP comparison: core versus noncore journals | Two-sample t test | p. 3 |
| CPP comparison across research areas | One-way analysis of variance | p. 3 |
| Post-hoc comparisons | Results describe post-hoc comparisons, but the specific post-hoc procedure is not named | p. 6 |
| Significance threshold | P < .05 | p. 3 |

These are the authors' reported methods, not an endorsement that every test or citation comparison should be reused unchanged. Any methodological changes in the follow-up should be labeled.

**What remains unspecified or would require the original export**

The article does not provide enough information to reproduce every software operation exactly. Unresolved details include precise index coverage, database state at extraction, the original record export, export options, name/term harmonization, map layout and clustering settings, and the post-hoc procedure. Manual clinical screening and risk-of-bias appraisal are not described. Country collaboration measures are reported, but a full co-authorship network analysis should not be attributed to the original study merely because the software supports it.

The authors acknowledge that they searched one database and that publication/citation counts do not directly establish scientific quality, which depends on factors such as study design, sample size and reporting. [PDF p. 12.]

**Implications for the proposed follow-up.** Preserve the original query as a comparable series, reconstruct a complete 2020 baseline, retain a separate expanded-search series, and log all methods that the original article leaves unspecified. Actual platform use, AI functions, financial measures, operating costs and SoS dependencies would be new extraction dimensions introduced by our proposal. They were not original inclusion criteria or bibliometric endpoints.
