# Start here: read, explore or contribute

This project maps how XR and related 3D/AI capabilities become useful, sustainable medical applications. Its data and methods are public. The evidence review is unfinished: initial AI assessments exist for all 18,976 publication groups, source adjudication covers 9,226, and no completed human verification is documented. Scientific screening is paused; documentation, tooling and methods feedback are welcome.

**Planning a human source check?** Read [the source-first procedure](human-verification.md) before opening AI examples, decision tables or the full archive. Reading those decisions affects what you can later describe as blinded review. You can still help if already exposed; disclose it.

## Read in your browser

No installation or GitHub account is needed to read the public record:

1. Read the [question and status](../README.md), then the [current checkpoint](checkpoint.md) for exact counts and pending work.
2. Use the [data walkthrough](data-walkthrough.md) to understand the tables and decision labels. Large CSVs need **Download raw file**; GitHub cannot preview the largest ones.
3. Read the [methods index](../methods/README.md) for the rule packet, dictionary and historical versions.
4. To offer help, choose **Join the project** in [New issue](https://github.com/Open-Source-Research-Initiative/medical-xr-from-capabilities-to-sustainable-use/issues/new/choose). A GitHub account is needed to open issues or pull requests; organization membership is not required.

## Explore locally

Install Git and use Python **3.12 or later** for these commands. The public tools use Python's standard library; no packages, API keys, subscription, GPU or restored evidence archive are needed. In a terminal:

```sh
git clone https://github.com/Open-Source-Research-Initiative/medical-xr-from-capabilities-to-sustainable-use.git
cd medical-xr-from-capabilities-to-sustainable-use
python --version
python scripts/verify_open_data.py
```

If your Python command is `python3` or `py -3`, substitute it for `python` throughout. Check that its version is at least 3.12. Run repository-relative commands from the directory containing this project's README and `scripts/` folder.

The verifier should print `"result": "PASS"`, 43 metadata tables, 18,976 frozen IDs and 9,226 adjudicated records. It checks file integrity and coverage, not scientific accuracy.

To inspect existing AI decisions for one group, run:

```sh
python scripts/lookup_publication.py P0000314
python scripts/lookup_publication.py P0000314 --json
```

The first command gives a short summary; the second prints the complete CSV projection rows and their provenance. Omitted source text and rationales remain in the full evidence archive. See the [walkthrough](data-walkthrough.md) before interpreting a result. `python scripts/show_example.py` presents an existing source-to-decision trace for the same group. These commands only read files; they perform no screening or new source assessment.

You can also use **Code → Download ZIP** and extract it for these data tools. That download has no Git history, so `scripts/verify_public_tree.py` requires a complete Git clone instead. To contribute from a terminal, fork the project on GitHub, clone your fork, create a branch and open a pull request to this repository's `main`. [CONTRIBUTING.md](../CONTRIBUTING.md) also explains browser-only changes.

## Find the right files

| Location | What it is for |
| --- | --- |
| [data/open/](../data/open/README.md) | Convenient CSV projections, catalog and links to original source tables |
| [Evidence release](../data/README.md#complete-evidence-archive) | Full original workspace, source text, rationales and history; choose `workspace.zip`, not the automatic source-code ZIP |
| [methods/](../methods/README.md) and [protocol.md](../protocol.md) | Scientific rules, scope, dictionary and method chronology |
| [scripts/](../scripts) | Read-only public lookup, example and verification tools |
| [analysis/](../analysis/README.md) | Preserved historical helpers that expect the original workspace; not the startup commands |
| [provenance/](../provenance) | Hashes, original-to-public mappings and dated administrative records |
| [Join the project](join-the-project.md) | Current ways to help and how assignments are coordinated |

Original project code is MIT; original prose and decision metadata are CC BY 4.0. Third-party sources retain their own notices and terms. See [reuse terms](../LICENSE.md).
