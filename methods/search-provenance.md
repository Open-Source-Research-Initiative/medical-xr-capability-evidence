# Search provenance and limits

## Historical baseline

The inherited Yeung 2021 search describes Web of Science Core Collection, searched 16 September 2020, using:

```
TOPIC: ("virtual reality*" OR "augmented reality*" OR "mixed reality*" OR "computer-mediated reality*") AND TOPIC: (medic* OR illness* OR disease* OR health* OR pharma*)
```

The inherited record reports no additional language or document-type restriction and 8,399 results spanning 1992–2020. That observed span is not a reconstructed starting-year filter. See [the original search record](inherited/yeung-original-query.txt) and Yeung et al., [DOI 10.2196/25499](https://doi.org/10.2196/25499). This historical baseline does not establish that follow-up exports used identical queries.

## Frozen follow-up inventory

The snapshot reconciles 16 RIS files and 26,142 raw records into 18,976 provisional publication groups. [The export manifest](search-export-manifest.csv) supplies file identifiers, hashes, sizes, encodings, recorded sources/database names and year counts without distributing the exports.

| Source observed in exports | Files | Raw records | Publication-group memberships |
| --- | ---: | ---: | ---: |
| ProQuest | 1 | 6,710 | 6,549 |
| EBSCOhost | 1 | 6,382 | 6,328 |
| Web of Science | 14 | 13,050 | 12,999 |

Memberships overlap. EBSCOhost records name Academic Search Ultimate. The specific ProQuest database and Web of Science collection/index are not recorded in these exports. No Scopus-labelled export was identified; that does not establish what may have been searched elsewhere.

**Follow-up query variants, search dates and applied filters were not recovered.** File timestamps and publication years are not substitutes. The inherited reconciliation README already disclosed this gap. The record cannot support a claim of a fully reproducible or exhaustive systematic search. A future update needs a separately dated, human-approved plan with exact database/platform/index, full syntax, date/time, filters, counts, export limits and archived queries. No search update was executed during this paused remediation.

Frozen representative-year counts are 2020: 804; 2021: 2,095; 2022: 2,445; 2023: 2,691; 2024: 3,416; 2025: 3,985; 2026: 3,528; 2027: 12. Issue year can differ from first journal publication. The new-report boundary is 1 June 2020; no 2025 upper cutoff applies. These counts do not measure acceleration or prove date eligibility.

## Grouping and remaining uncertainty

Reconciliation linked exact normalized DOI or same-source accession only when normalized title and conservative document-type class also matched. Incompatible title/type collisions were blocked. Longest available abstracts were selected with record provenance; other fields can come from another member. Grouping is not eligibility assessment and does not establish independent studies.

There are 5,767 multirecord groups, 60 year conflicts and 32 DOI conflicts; 152 unmerged title/author/year candidate groups and 232 blocked identifier candidate groups remain distinct. The representative table has 1,544 groups without abstracts, 4,976 without a KW tag and 1,976 without a recognized DOI. Memberships, blocked matches and records remain preserved in controlled storage.

Frozen inventory SHA-256: `2b4eb990d6d03a6682e8133f19f0b39e144af887fba7a745a8c8040306c28d13`. Retrieval, report identity, missing sources and human verification remain unresolved. Missed papers outside the inventory cannot be assessed from within-inventory agreement.
