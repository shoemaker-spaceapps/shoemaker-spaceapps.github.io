# Earth's Moon twins

Team Shoemaker, NASA Space Apps Challenge 2026. Challenge: *Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars*. We cover the Moon only.

- Site: https://shoemaker-spaceapps.github.io/ (globes) and https://shoemaker-spaceapps.github.io/explore/ (map, tables and method)
- Demo, 7 slides: [PDF](https://shoemaker-spaceapps.github.io/demo/demo.pdf) and https://shoemaker-spaceapps.github.io/demo/

## What we did

We cut Earth into 22,147 windows, each 10 km wide, and scored how much each one looks like 13 places on the Moon: the Apollo 11, 15 and 16 sites, the Nobile crater area, and the 9 Artemis III candidate regions near the south pole. The score compares median slope, steep-end slope (90th percentile), relief and rock type. The weights come from AHP (analytic hierarchy process, a way to turn expert pairwise judgments into weights): rock 0.42, steep-end slope 0.23, relief 0.23, median slope 0.12.

We never used the known analog sites to build the score. We used them, and 16 look-alikes with the wrong rock, only to test it.

## What we found

- Mare target: AUC 0.92 (95% interval 0.77 to 1.00). AUC is the chance that a known analog scores higher than a look-alike; 0.5 is a coin flip. Terrain alone gives 0.43, rock alone 0.82. We picked the look-alikes for their different rock, so rock separating them is expected; the finding is that terrain alone fails. The step from 0.82 to 0.92 suggests that terrain adds to rock, but the intervals overlap.
- No hard negative reaches the top 100 for its own target. The closest is Spitzkoppe-Erongo granites, at rank 629 of the 22,030 windows with a score.
- The best mare candidates are Arabian basalt fields (harrats) in Jordan and Saudi Arabia, the best Imbrium-rim candidates are in the Afar rift, and the rough Artemis III targets match terrain in the Andes. These lie outside the four well-studied regions and are less studied as lunar analogs.
- Some places match on rock and terrain but lie under farmland, so our bare-surface mask hides them. We list them as rock analogs, for sampling rather than surface tests. Karacadağ lava field in southeastern Türkiye ranks 11 of 22,030 for the mare and is our first candidate for field sampling and XRF. Some windows sit on rock the global map calls basic plutonic: Doğanşehir, Malatya, eastern Türkiye for the highland (rank 7 of all windows); northwestern Iran (Khoy ophiolite belt) and Karaman, central Türkiye for Nobile (ranks 1 and 2 of all windows). There the rock is most likely ophiolite, not anorthosite, so we mark them low confidence.
- Diviner puts the coldest spots in our Artemis III windows at 40 to 96 K as a yearly mean. At the coldest Earth terrain match, the lowest hourly temperature in 2001 to 2025 was -47 °C (NASA POWER).

Final tables are in `results/`. Candidate profiles with reasons are in `results/robust_candidates.csv`.

## Limits

- Imbrium has one known site, so its AUC (0.90) has no interval.
- GLiM, the global rock map, gives both known highland sites the wrong rock, so highland results are low confidence (AUC 0.53, interval 0.29 to 0.83).
- 10 km windows are too coarse for small craters such as Meteor Crater. NASA POWER climate cells are about 50 km wide.
- Earth cannot reproduce lunar gravity, vacuum, radiation or permanent shadow.

## Repository layout

```
docs/        the website: homepage with globes (index.html), explore page (explore/), assets/, data/, and the demo (demo/)
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
python src/site/test_home.py
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
NE_COUNTRIES=data/raw/ne_10m_admin_0_countries.shp python src/pipeline/countries.py
python src/analysis/lithology_check.py
```

Then run the commands in the section above. The raw files are not in the repository because they are several gigabytes and have their own licences:

| Data | Where to get it | File we used |
| --- | --- | --- |
| SLDEM2015 (LRO LOLA with Kaguya) | [PGDA product 54](https://pgda.gsfc.nasa.gov/products/54) | two 256 px/deg tiles covering 0 to 120 E, with their .LBL labels |
| LOLA south pole elevation | [PGDA product 90](https://pgda.gsfc.nasa.gov/products/90) | LDEM_80S_80MPP_ADJ.TIF |
| GLiM rock map | [PANGAEA](https://doi.pangaea.de/10.1594/PANGAEA.788537) | LiMW_GIS 2015.gdb and the 0.5 degree grid in hartmann-moosdorf_2012.zip (unpack to data/raw/glim_0p5/) |
| Global Aridity Index v3.1 | [figshare](https://doi.org/10.6084/m9.figshare.7504448) | ai_v31_yr.tif |
| Copernicus GLO-30, ESA WorldCover | [AWS open data](https://registry.opendata.aws/copernicus-dem/), [WorldCover](https://esa-worldcover.org/en) | read online by the pipeline |
| Natural Earth admin-0 countries | [naturalearthdata.com](https://www.naturalearthdata.com/downloads/10m-cultural-vectors/) | ne_10m_admin_0_countries.shp (v5.1.1) |
| NASA POWER, LRO Diviner | [POWER](https://power.larc.nasa.gov/), [PDS](https://pds-geosciences.wustl.edu/missions/lro/diviner.htm) | read online by the scripts |

## Column glossary

Column names come from our pipeline and are kept as they are; this is what they mean.

| Column | Meaning |
| --- | --- |
| window_id, roi | window id (E_000000 ...) and the region it was cut from (auto_ = automatic cell, neg_ = hard negative) |
| region, country, area | place label used everywhere on the site, Natural Earth country of the window centre, coarse area box used only for counts |
| slope_p50, slope_p90 | median and 90th percentile slope in the window, degrees |
| relief | highest minus lowest point in the window, metres |
| bare_frac, snow_frac | share of bare ground and of snow or ice (ESA WorldCover) |
| aridity_index | rain divided by evaporation demand; below 0.05 is hyper-arid |
| lito, lito_merkez | main rock class by area, and the class at the window centre (bazaltik = basaltic, plutonik_bazik = basic plutonic, sedimanter = sedimentary, kristalen = crystalline, volkanik_asidik = acid volcanic, bilinmiyor = unknown) |
| bazalt_frac, bazik_plutonik_frac | area share of basalt (GLiM vb) and basic plutonic rock (GLiM pb) |
| aday_maskesi | 1 if the window is bare (30% or more) or dry (aridity below 0.2) |
| genel_skor, arazi_benzerligi, kayac_eslesmesi | official score, terrain similarity, rock match (0 or 1) |
| sim, rank, rank_all | pipeline score and its rank among bare windows and among all windows |
| sicaklik_en_soguk_ay_min_C, gunluk_fark_C, yagis_mm_yil | lowest hourly temperature in 2001 to 2025 (POWER climatology T2M_MIN, lowest of the 12 months), mean daily temperature swing, yearly rain (NASA POWER) |
| inis_uygun, rover_uygun | slope proxies: gentle enough for landing tests, drivable for rovers |
| dims, eval_track | what a known site is known for (arazi = terrain, kayac = rock, surec = process, operasyon = operations) and how it is evaluated |

## Data and credits

NASA: LRO LOLA ([PGDA](https://pgda.gsfc.nasa.gov/products/90)), LRO Diviner ([PDS](https://pds-geosciences.wustl.edu/missions/lro/diviner.htm)), [POWER](https://power.larc.nasa.gov/), [GIBS and Worldview](https://worldview.earthdata.nasa.gov/). NASA and JAXA: [SLDEM2015](https://pgda.gsfc.nasa.gov/products/54) (LOLA with the Kaguya Terrain Camera). ESA: CAFE analog catalogue. [LROC QuickMap](https://quickmap.lroc.asu.edu/) for the Artemis III regions. [Macrostrat](https://macrostrat.org/). Country names: [Natural Earth](https://www.naturalearthdata.com/) admin-0, 1:10m (public domain). Globes: NASA SVS [CGI Moon Kit](https://svs.gsfc.nasa.gov/4720) and [Blue Marble](https://visibleearth.nasa.gov/images/73909/december-blue-marble-next-generation-w-topography-and-bathymetry). Map: [Leaflet](https://leafletjs.com/), charts: [Plotly](https://plotly.com/javascript/), globes: [globe.gl](https://globe.gl/).

Attribution required by the data licences:

- Copernicus DEM GLO-30 ([licence](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM)): produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.
- ESA WorldCover 2021 v200, CC BY 4.0: © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium.
- Global Aridity Index and Potential Evapotranspiration (ET0) Database, Version 3.1, CC BY 4.0: Zomer, R. and Trabucco, A. (2019), figshare, https://doi.org/10.6084/m9.figshare.7504448.
- GLiM, CC-BY 3.0: Hartmann, J. and Moosdorf, N. (2012), Global Lithological Map Database v1.0, PANGAEA, https://doi.org/10.1594/PANGAEA.788537; and The new global lithological map database GLiM, Geochemistry, Geophysics, Geosystems 13, Q12004, https://doi.org/10.1029/2012GC004370.
- Esri World Imagery: Source: Esri, Vantor, Earthstar Geographics, and the GIS User Community.

We resampled these data to our 10 km windows.

## Team

- Melike Kızılay: geology, lunar targets and analog interpretation
- Tarık Tuna Taşaltı: data pipeline, similarity model and validation
- Nagihan Koçcenk: water and ISRU (in-situ resource utilization) use cases
- Zeynep Naz Erkoç: known analog catalogue and hard negative analogs

GitHub: https://github.com/shoemaker-spaceapps

## License

Code: MIT, see LICENSE. Data belong to their providers, see Data and credits.
