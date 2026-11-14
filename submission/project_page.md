# Space Apps project page: text for each field

Copy each block into the field with the same name.

## Project Name

Earth's Moon Twins

## High-Level Project Summary

We built a map that ranks 22,147 places on Earth, each 10 km wide, by how much they look like 13 places on the Moon, including the 9 Artemis III candidate regions near the south pole. For each lunar target it compares slope, relief and rock type, and it says where the match breaks: gravity, vacuum, climate, rock. We tested it against 15 known analog sites and 16 look-alikes with the wrong rock, such as salt flats, sand seas and granite. For the lunar mare it tells them apart with an AUC of 0.92 (95% interval 0.77 to 1.00; 0.5 is a coin flip). Mission teams can use it to find lesser-known test sites, such as the basalt fields of the Arabian Peninsula and the Afar rift, and to see which tests each place suits.

## Link to Project Demo

- 7-slide demo: https://shoemaker-spaceapps.github.io/demo/
- Same demo as PDF: https://shoemaker-spaceapps.github.io/demo/demo.pdf

## Link to Final Project

- Website with the interactive map: https://shoemaker-spaceapps.github.io/
- Code and data tables: https://github.com/shoemaker-spaceapps/shoemaker-spaceapps.github.io

## Detailed Project Description

**What it does.** Pick a lunar target on the map: one of the Apollo 11, 15 and 16 sites, the Nobile crater area, or one of the 9 Artemis III regions. The map shows the Earth windows that look most like it, from a pool of lesser-known places, all bare-surface windows, or all windows. Each window opens a side-by-side table of its numbers and the Moon's, a climate line from NASA POWER, and a link to the NASA Worldview satellite view. For each target, five "featured analogs" explain why the place is similar, where the analogy breaks, and what a mission team could test there.

**How it works.**
1. Moon elevation comes from LRO LOLA (SLDEM2015, made with Kaguya) and, near the south pole, from the LOLA polar elevation model. Earth elevation comes from Copernicus GLO-30, land cover from ESA WorldCover, rock type from GLiM, dryness from the Global Aridity Index, and climate from NASA POWER.
2. We cut Earth into 10 km windows: 21 study regions, 759 half-degree cells picked automatically because they are dry and basaltic, and 17 hard negative boxes. That gives 22,147 windows.
3. For every window and every target we compute median slope, steep-end slope (90th percentile), relief, and the main rock class by area.
4. One score per window and target uses weights from AHP (analytic hierarchy process, a way to turn expert pairwise judgments into weights): rock 0.42, steep-end slope 0.23, relief 0.23, median slope 0.12. For the Artemis III targets the lunar rock type is not set, so we rank them by terrain only.
5. We check the score with AUC against hard negatives, with intervals from a bootstrap that resamples whole sites, and with a second score from an earlier version of our pipeline.

**What we found.**
- Look-alikes do not reach the top. None of our 16 hard negatives gets into the top 100 for its own target; the closest is Spitzkoppe-Erongo granites at rank 629.
- Shape alone is misleading. For the mare target, terrain alone scores an AUC of 0.43, worse than chance. Rock alone gives 0.82, and both together 0.92. The best salt flat window, Salar de Atacama, ranks 518 of 22,147 on terrain, ahead of 5 of our 7 known mare sites.
- New candidates beyond Antarctica, Atacama, Iceland and Hawaii:
  - Mare (Apollo 11): Arabian Peninsula (32.225, 37.553); Arabian Peninsula (22.495, 40.243); Afar and East Africa (13.135, 40.731)
  - Imbrium rim (Apollo 15): Afar and East Africa (11.995, 41.638); Afar and East Africa (11.495, 42.546); Arabian Peninsula (25.315, 37.649)
  - Highlands (Apollo 16), low confidence: Iran, Afghanistan and Pakistan (32.725, 59.481); Central Asia and Tibet (35.495, 89.887); Iran, Afghanistan and Pakistan (26.635, 66.352)
  - Nobile crater area: Central Asia and Tibet (47.315, 93.199); Iran, Afghanistan and Pakistan (36.225, 58.167); Iran, Afghanistan and Pakistan (32.635, 59.481)
  - Artemis III regions, terrain only: Andes (22 of 45 candidates), then Patagonia; Sahara; Iran, Afghanistan and Pakistan; Galapagos
- Our 10 km median slope for the Artemis III regions is 0.87 to 1.45 times the LROC QuickMap region slope, so the two agree in size.

**Water, ice and ISRU.** Polar craters that never see sunlight hold water ice, and these cold traps are the main reason for a polar base. NASA Diviner data put the coldest spots in our Artemis III windows at 40 to 96 kelvin as a yearly mean, and its thermal model finds buried ice could stay stable under 7% to 60% of the ground. No Earth place matches that; the coldest Earth terrain match has a coldest-month minimum of -47 °C. We group Earth regions by the water or ice test they suit (ISRU, in-situ resource utilization, means making water, oxygen or fuel from local material): dry-surface analogs such as Sahara and Tibesti, Chad; ice-bearing analogs such as Europe and Anatolia and Central Asia and Tibet; terrain analogs such as Iran, Afghanistan and Pakistan and Andes. Each region comes with a one-line reading and a concrete ISRU test.

**Benefits.** Analog site choice today leans on a few famous places. This map gives a ranked, checkable list with reasons and limits for each place, so a team can pick a site for a specific test (rover driving on basaltic ground, landing hazard detection on rough slopes, ice extraction in dry regolith) and see what the site cannot simulate.

**Creativity.** We tested the method against hard negatives: places chosen in advance because they look like the Moon from orbit but have the wrong rock. That is how we found that terrain similarity alone is misleading for the mare. We also add a water and ice reading for the polar targets, and NASA Diviner temperatures on the lunar side.

**Validity.** The known sites were used only for testing, never for building the score. Each AUC comes with a 95% interval from a bootstrap over whole sites and negative regions. We report what does not work: Imbrium has one known site, and the highland test fails because the global rock map gives both known highland sites the wrong rock. We fixed one site box (Merriam Crater) that sat 24 km away from the crater, and we dropped one negative (Jabal al Akhdar) once the rock map showed ophiolite gabbro there.

**Limits.** Earth cannot reproduce lunar gravity, vacuum, radiation or permanent shadow. GLiM misses small rock units. 10 km windows are too coarse for small craters. We have only 15 known sites.

**Tools.** Python (rasterio, GeoPandas, pyproj, shapely, NumPy, pandas), Leaflet and Plotly for the site, Playwright for screenshots and the demo PDF, GitHub Pages for hosting.

**Team.**
- Melike Kızılay: geology, lunar targets and analog interpretation
- Tarık Tuna Taşaltı: data pipeline, similarity model and validation
- Nagihan Koçcenk: water and ISRU (in-situ resource utilization) use cases
- Zeynep Naz Erkoç: known analog catalogue and hard negative analogs

## Use of Super Intelligence (SI)

We used an AI coding assistant (Claude by Anthropic) for writing and debugging code, for data processing scripts (downloads, reprojection, the NASA POWER and Diviner readers), and for first drafts of the website, the demo and these texts. The team defined the problem, made the scientific decisions, chose the lunar targets, the known analog sites and the hard negatives, did the geological interpretation, set the AHP weights, and checked every result. Every number on the site comes from our own data tables.

## NASA Data

- **LRO LOLA south pole elevation, LDEM_80S_80MPP_ADJ** (Planetary Geodesy Data Archive): https://pgda.gsfc.nasa.gov/products/90. Elevation, slope and relief for the Nobile and Artemis III targets.
- **SLDEM2015, LRO LOLA with Kaguya Terrain Camera** (Planetary Geodesy Data Archive): https://pgda.gsfc.nasa.gov/products/54. Elevation, slope and relief for the Apollo targets.
- **LRO Diviner Polar Resource Product** (PDS Geosciences Node): https://pds-geosciences.wustl.edu/missions/lro/diviner.htm. Yearly mean and maximum temperature and ice stability in the polar target windows.
- **NASA POWER climatology, 2001 to 2025**: https://power.larc.nasa.gov/. Coldest-month minimum, daily temperature swing, rain and wind for every Earth window.
- **NASA GIBS and Worldview (MODIS Terra true color, Blue Marble)**: https://worldview.earthdata.nasa.gov/. Map layers and satellite views of every candidate.
- **LRO LROC QuickMap** (Arizona State University): https://quickmap.lroc.asu.edu/. Artemis III region centres and the slope check.

## Space Agency Partner Data and Other References

- **ESA Copernicus DEM GLO-30**: https://registry.opendata.aws/copernicus-dem/. Earth elevation, slope and relief.
- **ESA WorldCover 2021 v200**: https://esa-worldcover.org/en. Bare ground and snow share.
- **JAXA Kaguya (SELENE) Terrain Camera**: https://www.kaguya.jaxa.jp/index_e.htm. Part of SLDEM2015.
- **ESA CAFE analog site catalogue**. Known analog sites, checked against the literature by our team.
- **GLiM, Global Lithological Map** (Hartmann and Moosdorf 2012, CC-BY 3.0): https://doi.pangaea.de/10.1594/PANGAEA.788537. Rock type.
- **Global Aridity Index v3** (Zomer et al.): https://doi.org/10.6084/m9.figshare.7504448. Dryness.
- **Macrostrat**: https://macrostrat.org/. Rock type check at known sites.
- **Esri World Imagery**: high-resolution map layer.
- **Leaflet** (https://leafletjs.com/) and **Plotly** (https://plotly.com/javascript/): map and charts.
