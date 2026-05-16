# Source Manifest

PDFs/HTML files in `backend/data/sources/<sport>/` are **gitignored**. This manifest records URLs + expected filenames so anyone can re-fetch.

To re-download a source: open the URL, save with the filename in column 1 into the matching `backend/data/sources/<sport>/` folder.

Total target: ~40 files across 4 sports. Authority score column drives the trust-weighted reranker.

---

## Football ⚽ (target: 12-15 sources)

| Filename | URL | Authority | Lang |
|---|---|---|---|
| uefa_medical_regulations_2024.pdf | TBD — fill from uefa.com/MultimediaFiles/Download/uefaorg/Medical/ | 0.9 | en |
| fifa_medical_network_manual.pdf | TBD — fill from fifa.com medical resources | 0.9 | en |
| tff_saglik_komisyonu.pdf | TBD — fill from tff.org/Resources/TFF/ | 0.9 | tr |
| uefa_pro_license_nutrition.pdf | TBD | 0.9 | en |
| ais_football_nutrition.pdf | https://www.ais.gov.au/nutrition/ | 0.8 | en |
| ioc_nutrition_consensus_football.pdf | TBD — olympic.org consensus statements | 1.0 | en |
| bjsm_football_injury_2024.pdf | TBD — bjsm.bmj.com | 0.85 | en |
| acsm_soccer_position_stand.pdf | TBD — acsm.org | 0.85 | en |

## Wrestling 🤼 (target: 6-8 sources)

| Filename | URL | Authority | Lang |
|---|---|---|---|
| twf_yayinlari.pdf | TBD — twf.gov.tr | 0.9 | tr |
| uww_medical_regulations.pdf | TBD — unitedworldwrestling.org | 0.9 | en |
| ioc_combat_sports_weight_consensus.pdf | TBD — olympic.org | 1.0 | en |
| acsm_wrestler_weight_loss.pdf | TBD — acsm.org | 0.85 | en |
| usa_wrestling_nutrition.pdf | TBD — usawrestling.org | 0.8 | en |
| bjsm_wrestling_safety.pdf | TBD — bjsm.bmj.com | 0.85 | en |

## Weightlifting 🏋️ (target: 6-8 sources)

| Filename | URL | Authority | Lang |
|---|---|---|---|
| iwf_technical_competition_rules.pdf | TBD — iwf.sport | 0.9 | en |
| thf_kilavuzlar.pdf | TBD — thf.org.tr | 0.9 | tr |
| nsca_weightlifting_position.pdf | TBD — nsca.com | 0.85 | en |
| ioc_strength_sports_nutrition.pdf | TBD — olympic.org | 1.0 | en |
| jissn_protein_review.pdf | TBD — jissn.biomedcentral.com | 0.85 | en |

## Volleyball 🏐 (target: 6-8 sources)

| Filename | URL | Authority | Lang |
|---|---|---|---|
| fivb_medical_regulations.pdf | TBD — fivb.com | 0.9 | en |
| tvf_yayinlari.pdf | TBD — tvf.org.tr | 0.9 | tr |
| bjsm_jumpers_knee.pdf | TBD — bjsm.bmj.com | 0.85 | en |
| acsm_volleyball_position.pdf | TBD — acsm.org | 0.85 | en |
| ioc_red_s_consensus.pdf | TBD — olympic.org | 1.0 | en |

---

## How filenames map to authority

The ingest script (`backend/data/ingest.py`) classifies authority from the filename:

- Contains `ioc`, `olympic`, `who`, `cdc`, `nih`, `wada` → **1.0** (IOC/government)
- Contains `gsb`, `gov.tr` → **1.0** (government)
- Contains `fifa`, `uefa`, `tff`, `twf`, `thf`, `tvf`, `iwf`, `fivb`, `nsca`, `acsm` → **0.9** (federation)
- Contains `bjsm`, `jissn`, `pubmed`, `frontiers` → **0.85** (journal)
- Contains `ais`, `usa wrestling`, `usoc` → **0.8** (national institute)
- Default → **0.85**

Keep filenames descriptive so the heuristic catches them correctly.
