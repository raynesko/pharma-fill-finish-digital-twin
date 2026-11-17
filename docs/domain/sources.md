# Sources for T1.1.1

Retrieved 2026-11-15 by web search; fetch depth noted per row. **Confidence** is for use as evidence in this project (primary regulation = high; vendor or blog = low/medium, indicative only). Record all retrievals; re-verify before quoting.

| ID | Type | Title | Link | Retrieval depth | Confidence | Used for |
|---|---|---|---|---|---|---|
| S1 | Regulator guidance **[primary]** | FDA, *Sterile Drug Products Produced by Aseptic Processing - Current Good Manufacturing Practice* (2004; FDA PDF dated September 2004, Federal Register notice October 4, 2004, docket FDA-2003-D-0145) | https://www.fda.gov/regulatory-information/search-fda-guidance-documents/sterile-drug-products-produced-aseptic-processing-current-good-manufacturing-practice | search result only, full text not read | High (existence/status); content points need reading | Aseptic framework; fill-area clearance candidate |
| S2 | Regulator **[primary]**, read via secondary summaries | EudraLex Volume 4, Annex 1 *Manufacture of Sterile Medicinal Products* (final text published 2022-08-25) | Official text not fetched. Summaries: https://www.nsf.org/knowledge-library/annex-1-revised-overview ; https://scilife.io/blog/planning-for-eu-gmp-annex1 | summaries only | Medium until official text read | Grade A with unidirectional airflow, RABS/isolators, interventions risk-assessed and qualified, contamination control strategy |
| S3 | Regulation **[primary]** | 21 CFR 211.130 Packaging and labeling operations | https://www.law.cornell.edu/cfr/text/21/211.130 | fetched | High (verify against eCFR) | Labeling/packaging controls, line clearance (e), lot traceability (c) |
| S4 | Regulation **[primary]** | 21 CFR 211.192 Production record review | https://www.law.cornell.edu/cfr/text/21/211.192 | fetched | High (verify against eCFR) | QA record review before release |
| S5 | Pharmacopeia, secondary summary | USP <790> Visible Particulates in Injections and <1790> Visual Inspection of Injections | https://www.gmp-compliance.org/gmp-news/usp-monograph-1790-visual-inspection-of-injections-comes-into-force ; https://www.drugfuture.com/Pharmacopoeia/usp38/data/v38332/usp38nf33s2_c790.html | search summaries | Medium. **AQL values conflict between editions (0.65% vs 0.26%); do not quote either** | 100% inspection plus AQL release sampling |
| S6 | Industry guide | ISPE Baseline Guide Vol. 3: Sterile Product Manufacturing Facilities, 3rd ed. (April 2018) | https://ispe.org/publications/guidance-documents/sterile-product-manufacturing-facilities-third-edition | catalog page, paid document not read | Medium; predates the 2022 Annex 1 | Facility and barrier-technology context |
| S7 | Vendor | Syntegon, liquid vial filling | https://syntegon.com/solution-finder/pharma/liquid-vial-filling | search summary; direct page fetch returned 404 | Low-Medium | Equipment types (washer, filler, stoppering options) |
| S8 | Vendor | Bausch+Ströbel, vial filling and closing line | https://www.bausch-stroebel.com/en/solutions-concepts/process-solutions/vial-filling-and-closing-line | search summary | Low-Medium | Line sequence, external cleaning, inline checks |
| S9 | Design walkthrough (non-peer-reviewed) | Walkthrough: Design a Pharmaceutical Fill-Finish Line (Vials + Syringes) | https://compendium-01j.pages.dev/Walkthroughs/design-pharma-fill-finish-line | search summary | **Low** | Tunnel temperature/time indication only; do not cite in README |
| S10 | Trade article | Counteracting product loss during the inline inspection of vials | https://cleanroomtechnology.com/counteracting-product-loss-during-the-inline-inspection-of-vials-210266 | search summary | Low-Medium | Inline checks (fill weight, stopper position, crimp, print), false-reject context |
| S11 | Industry reference book | PDA, *Aseptic Processing of Parenteral Products* Vol. 1 (table of contents) | https://store.pda.org/TableOfContents/Aseptic_Vol1_TOC.pdf | TOC only | Medium (existence); content not read | Pointer for deep reading on vial processing and inspection |

## Gaps to close in later tickets
- No sourced vials/min rates, MTBF/MTTR, changeover durations or AVI false-reject rates: **T2.1.1**.
- Read the official Annex 1 text and the FDA 2004 guidance sections on interventions and personnel before quoting any clause.
- Find the fill-area line-clearance citation (see process_map.md).
