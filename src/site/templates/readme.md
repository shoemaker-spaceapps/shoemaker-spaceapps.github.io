# Earth's Moon twins

Team $team, NASA Space Apps Challenge 2026. Challenge: *$challenge*. We cover the Moon only.

- Site: $site_url
- Demo, 7 slides: $demo_url ([PDF]($demo_pdf))

## What we did

We cut Earth into $n_windows windows, each 10 km wide, and scored how much each one looks like $n_targets places on the Moon: the Apollo 11, 15 and 16 sites, the Nobile crater area, and the $n_artemis Artemis III candidate regions near the south pole. The score compares median slope, steep-end slope (90th percentile), relief and rock type. The weights come from AHP (analytic hierarchy process, a way to turn expert pairwise judgments into weights): rock 0.42, steep-end slope 0.23, relief 0.23, median slope 0.12.

We never used the known analog sites to build the score. We used them, and $n_neg look-alikes with the wrong rock, only to test it.

## What we found

- Mare target: AUC $mare_auc (95% interval $mare_lo to $mare_hi). AUC is the chance that a known analog scores higher than a look-alike; 0.5 is a coin flip. Terrain alone gives $terrain_auc, rock alone $rock_auc.
- No hard negative reaches the top 100 for its own target. The closest is $best_neg_name, at rank $best_neg_rank of $n_windows.
- Outside the well-studied areas, the best mare candidates are basalt fields in the Arabian Peninsula, the best Imbrium-rim candidates are in the Afar rift, and the rough Artemis III targets match terrain in the Andes.
- Diviner puts the coldest spots in our Artemis III windows at $div_cold_lo to $div_cold_hi K as a yearly mean. The coldest Earth terrain match has a coldest-month minimum of $earth_cold_C °C.

Final tables are in `results/`. Candidate profiles with reasons are in `results/robust_candidates.csv`.

## Limits

- Imbrium has one known site, so its AUC ($imb_auc) has no interval.
- GLiM, the global rock map, gives both known highland sites the wrong rock, so highland results are low confidence (AUC $high_auc, interval $high_lo to $high_hi).
- 10 km windows are too coarse for small craters such as Meteor Crater. NASA POWER climate cells are about 50 km wide.
- Earth cannot reproduce lunar gravity, vacuum, radiation or permanent shadow.

## Repository layout

```
docs/        the website (index.html, assets/, data/) and the 7-slide demo (demo/)
src/         code: pipeline/ builds windows and climate, analysis/ scores and checks, site/ builds pages and texts
data/        small inputs: known sites, hard negatives, Artemis III regions, AHP weights, source catalogues
results/     final tables; results/pipeline/ holds the window and target tables they come from
submission/  texts and images for the Space Apps project page
```

## Reproduce

Python 3.12. From the repository root:

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

The last line is only needed for screenshots and the demo PDF.

### From the tables in this repository (no downloads, a few minutes)

```
python src/pipeline/analog_pipeline.py --stage full
python src/analysis/evaluate.py --out results/pipeline --t3 data/known_analogs_moon.csv --negatives data/hard_negatives.csv --ahp data/ahp_weights.csv
python src/analysis/final_analysis.py
python src/analysis/water_ice.py
python src/site/build_site.py
python src/site/build_demo.py
python src/site/build_submission.py
python src/site/capture.py
python src/site/check_pages.py
```

### From raw data (about one hour; Earth tiles are read online)

Put the large files in `data/raw/`, set the four paths, then run:

```
export MOON_DEM=data/raw/SLDEM2015_256_0N_60N_000_120_FLOAT.LBL,data/raw/SLDEM2015_256_60S_0S_000_120_FLOAT.LBL
export MOON_POLAR_DEM=data/raw/LDEM_80S_80MPP_ADJ.TIF
export GLIM_PATH="data/raw/LiMW_GIS 2015.gdb"
export ARIDITY_TIF=data/raw/ai_v31_yr.tif
python src/pipeline/prepare_known_sites.py
python src/pipeline/analog_pipeline.py --stage tables --auto-rois --workers 4
python src/pipeline/power_climate.py
python src/pipeline/diviner_targets.py
python src/analysis/lithology_check.py
```

Then run the commands in the section above. The raw files are not in the repository because they are several gigabytes and have their own licences:

| Data | Where to get it | File we used |
| --- | --- | --- |
| SLDEM2015 (LRO LOLA with Kaguya) | [PGDA product 54](https://pgda.gsfc.nasa.gov/products/54) | two 256 px/deg tiles covering 0 to 120 E, with their .LBL labels |
| LOLA south pole elevation | [PGDA product 90](https://pgda.gsfc.nasa.gov/products/90) | LDEM_80S_80MPP_ADJ.TIF |
| GLiM rock map | [PANGAEA](https://doi.pangaea.de/10.1594/PANGAEA.788537) | LiMW_GIS 2015.gdb and the 0.5 degree grid in hartmann-moosdorf_2012.zip (unpack to data/raw/glim_0p5/) |
| Global Aridity Index v3 | [figshare](https://doi.org/10.6084/m9.figshare.7504448) | ai_v31_yr.tif |
| Copernicus GLO-30, ESA WorldCover | [AWS open data](https://registry.opendata.aws/copernicus-dem/), [WorldCover](https://esa-worldcover.org/en) | read online by the pipeline |
| NASA POWER, LRO Diviner | [POWER](https://power.larc.nasa.gov/), [PDS](https://pds-geosciences.wustl.edu/missions/lro/diviner.htm) | read online by the scripts |

## Column glossary

Column names come from our pipeline and are kept as they are; this is what they mean.

| Column | Meaning |
| --- | --- |
| window_id, roi | window id (E_000000 ...) and the region it was cut from (auto_ = automatic cell, neg_ = hard negative) |
| slope_p50, slope_p90 | median and 90th percentile slope in the window, degrees |
| relief | highest minus lowest point in the window, metres |
| bare_frac, snow_frac | share of bare ground and of snow or ice (ESA WorldCover) |
| aridity_index | rain divided by evaporation demand; below 0.05 is hyper-arid |
| lito, lito_merkez | main rock class by area, and the class at the window centre (bazaltik = basaltic, plutonik_bazik = basic plutonic, sedimanter = sedimentary, kristalen = crystalline, volkanik_asidik = acid volcanic, bilinmiyor = unknown) |
| bazalt_frac, bazik_plutonik_frac | area share of basalt (GLiM vb) and basic plutonic rock (GLiM pb) |
| aday_maskesi | 1 if the window is bare (30% or more) or dry (aridity below 0.2) |
| genel_skor, arazi_benzerligi, kayac_eslesmesi | official score, terrain similarity, rock match (0 or 1) |
| sim, rank, rank_all | pipeline score and its rank among bare windows and among all windows |
| sicaklik_en_soguk_ay_min_C, gunluk_fark_C, yagis_mm_yil | coldest-month minimum temperature, daily temperature swing, yearly rain (NASA POWER) |
| inis_uygun, rover_uygun | slope proxies: gentle enough for landing tests, drivable for rovers |
| dims, eval_track | what a known site is known for (arazi = terrain, kayac = rock, surec = process, operasyon = operations) and how it is evaluated |

## Data and credits

NASA: LRO LOLA ([PGDA](https://pgda.gsfc.nasa.gov/products/90)), LRO Diviner ([PDS](https://pds-geosciences.wustl.edu/missions/lro/diviner.htm)), [POWER](https://power.larc.nasa.gov/), [GIBS and Worldview](https://worldview.earthdata.nasa.gov/). NASA and JAXA: [SLDEM2015](https://pgda.gsfc.nasa.gov/products/54) (LOLA with the Kaguya Terrain Camera). ESA: [Copernicus DEM GLO-30](https://registry.opendata.aws/copernicus-dem/), [WorldCover](https://esa-worldcover.org/en), CAFE analog catalogue. [GLiM](https://doi.pangaea.de/10.1594/PANGAEA.788537) (Hartmann and Moosdorf 2012, CC-BY 3.0). [Global Aridity Index v3](https://doi.org/10.6084/m9.figshare.7504448). [LROC QuickMap](https://quickmap.lroc.asu.edu/) for the Artemis III regions. [Macrostrat](https://macrostrat.org/). Map: [Leaflet](https://leafletjs.com/), charts: [Plotly](https://plotly.com/javascript/), imagery layer: Esri.

## Team

$team_md

GitHub: $org_url

## License

Code: MIT, see LICENSE. Data belong to their providers, see Data and credits.
