# Data, controlled access and restoration

The complete controlled archive preserves 36,839 original files: exports, frozen inventory, memberships, both initial passes, repairs, adjudications, source receipts, prompts, code and historical drafts. It remains unchanged. [The full file manifest](../provenance/legacy-file-manifest.csv) and [artifact checksums](../provenance/artifacts.json) identify it. File modification times are preservation metadata, not reconstructed commit dates.

## Public reuse

The repository provides [operative methods and dictionary](../methods/README.md), count/schema records, preservation manifests, 51 unchanged historical Python files and a [runnable OA example](../examples/README.md). One excerpt-bearing helper and its containing local draft commits are withheld from public history. Original project code is MIT and prose is CC BY 4.0; [third-party exclusions](../LICENSE.md) remain.

Read IDs as strings and preserve leading zeros, empty fields and qualified dates. sources.csv indexes migration guidance, not the research inventory. The blank human-verification CSV contains no completed assessments.

## Private GitHub collaboration

Cole selected GitHub on 13 November 2026. The private companion is [medical-xr-controlled-evidence](https://github.com/Open-Source-Research-Initiative/medical-xr-controlled-evidence). Its permitted derivatives provide all 18,976 IDs, both initial decision passes and 9,226 current adjudicated rows, with available reviewer/model identities, artifact hashes, memberships and queue metadata. The derivation manifest specifies retained and omitted fields for every source. These projections are **not** complete original evidence ledgers.

After Cole grants access, clone that private repository and run `python validate_export.py` to check derivative hashes and coverage. The private repository contains a source-only locator for the OA example, a blank human result template and access/rights instructions. GitHub read access permits inspection of its authorized contents; it does not grant a database subscription or redistribution rights.

Request access from Cole / @ajhcs with your GitHub username, intended task, needed IDs/material, affiliation if relevant to licensed access, and duration. Do not include restricted text in a public issue. Cole reviews permissions, grants named access at the least necessary level, records the grant in the private access log and reviews/removes it when the task ends. No new collaborator invitation is inferred from this project setup.

## Material still held locally

Raw articles, RIS exports, bulk abstracts, free-text evidence/rationales, private conversations, the complete workspace ZIP and excerpt-bearing original Git bundle remain in Cole's local controlled archive. A private GitHub repository does not establish permission to transfer institutional/provider material to that service. The private rights queue identifies this unresolved scope. No claim is made that the full evidence archive is now shared online.

Approved collaborators obtain owning sources through their own permitted access. If a specific item may be shared, Cole records its terms, permitted recipients and location before transfer. A GitHub release asset is available for a rights-cleared large package; GitHub documents a per-file limit below 2 GiB and access through repository permissions. The present metadata derivatives fit ordinary Git and require no alternative storage service. [GitHub release documentation](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).

## Recovery

Verify the recorded archive checksum, then extract into a separate empty workspace, preserving internal paths. Do not overwrite the original. Same-machine restoration passed all 36,839 captured hashes and 22,601 inherited manifest paths. Fresh-environment or cross-machine reproduction of the original analysis remains unperformed.

The inherited read-only validator runs from a restored original workspace. Copied historical analysis scripts depend on that layout. Do not start screening or the scientific watcher from this public code copy; screening remains paused.
