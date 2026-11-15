# Space Apps project page: text for each field

Copy each block into the field with the same name.

## Project Name

Earth's Moon Twins

## High-Level Project Summary

We built a map that ranks 22,147 places on Earth, each 10 km wide, by how much they look like 13 places on the Moon, including the 9 Artemis III candidate regions near the south pole. For each lunar target it compares slope, relief and rock type, and it says where the match breaks: gravity, vacuum, climate, rock. We tested it against 15 known analog sites and 16 look-alikes with the wrong rock, such as salt flats, sand seas and granite. For the lunar mare it tells them apart with an AUC of 0.92 (95% interval 0.77 to 1.00; 0.5 is a coin flip). Mission teams can use it to find lesser-known test sites, such as the Arabian basalt fields (harrats) and the Afar rift, and to see which tests each place suits.

## Link to Project Demo

- Demo as PDF (7 slides): https://shoemaker-spaceapps.github.io/demo/demo.pdf
- Same demo as web slides: https://shoemaker-spaceapps.github.io/demo/

## Link to Final Project

- Website: https://shoemaker-spaceapps.github.io/ (globes) and https://shoemaker-spaceapps.github.io/explore/ (full map, tables and method)
- Code and data tables: https://github.com/shoemaker-spaceapps/shoemaker-spaceapps.github.io

## Detailed Project Description

**What it does.** On the homepage, two globes show the Moon and the Earth. Pick a lunar target on the Moon globe (one of the Apollo 11, 15 and 16 sites, the Nobile crater area, or one of the 9 Artemis III regions), and the Earth globe turns to the windows that look most like it; click one to compare it with the Moon. A surface switch shows either bare rock, ready for field tests, or any surface, which adds rock analogs under farmland and grass. Below the globes, a table gives the best Earth match for each lunar target. The explore page has the full map, with a pool of lesser-known places, all bare-surface windows, or all windows. Each window opens a side-by-side table of its numbers and the Moon's, a climate line from NASA POWER, and a link to the NASA Worldview satellite view. For each target, five "featured analogs" explain why the place is similar, where the analogy breaks, and what a mission team could test there.

**How it works.**
1. Moon elevation comes from LRO LOLA (SLDEM2015, made with Kaguya) and, near the south pole, from the LOLA polar elevation model. Earth elevation comes from Copernicus GLO-30, land cover from ESA WorldCover, rock type from GLiM, dryness from the Global Aridity Index, and climate from NASA POWER.
2. We cut Earth into 10 km windows: 21 study regions, 759 half-degree cells picked automatically because they are dry and basaltic, and 17 hard negative boxes. That gives 22,147 windows.
3. For every window and every target we compute median slope, steep-end slope (90th percentile), relief, and the main rock class by area.
4. One score per window and target uses weights from AHP (analytic hierarchy process, a way to turn expert pairwise judgments into weights): rock 0.42, steep-end slope 0.23, relief 0.23, median slope 0.12. For the Artemis III targets the lunar rock type is not set, so we rank them by terrain only.
5. We check the score with AUC against hard negatives, with intervals from a bootstrap that resamples whole sites, and with a second score from an earlier version of our pipeline.

**What we found.**
- Look-alikes do not reach the top. None of our 16 hard negatives gets into the top 100 for its own target; the closest is Spitzkoppe-Erongo granites at rank 629.
- Shape alone is misleading. For the mare target, terrain alone scores an AUC of 0.43, worse than chance. Rock alone gives 0.82, and both together 0.92. The best salt flat or playa window, Dasht-e Kavir, ranks 245 of 22,030 on terrain, ahead of 5 of our 7 known mare sites. We picked the look-alikes for their different rock, so it is expected that rock separates them; the real finding is that terrain alone fails. The step from 0.82 to 0.92 suggests that terrain adds to rock, but the intervals overlap.
- Candidates outside the four well-studied regions (Antarctica, Atacama, Iceland, Hawaii) and less studied as lunar analogs:
  - Mare (Apollo 11): Harrat ash Shaam, Jordan (32.225, 37.553); harrat basalt field, Saudi Arabia (22.495, 40.243); Ethiopia (13.135, 40.731)
  - Imbrium rim (Apollo 15): Ethiopia (11.995, 41.638); Djibouti (11.495, 42.546); harrat basalt field, Saudi Arabia (25.315, 37.649)
  - Highlands (Apollo 16), low confidence: Iran (32.725, 59.481); Tibetan Plateau, China (35.495, 89.887); Pakistan (26.635, 66.352)
  - Nobile crater area: Mongolia (47.315, 93.199); Iran (36.225, 58.167); Iran (32.635, 59.481)
  - Artemis III regions, terrain only: Andes (22 of 45 candidates, in Chile and Argentina), then Patagonia, Argentina; Chad; Iran; Galapagos, Ecuador
- Bare rock and rock analogs are two different lists. Our bare-surface mask keeps places where a rover could work on exposed ground. Some places match on rock and terrain but lie under fields or grass, so the mask hides them; we list them separately as rock analogs, useful for sampling, not for surface operations. The best for the mare, in Mongolia, ranks 6 of 22,030 windows but is only 0% bare.
- Our 10 km median slope for the Artemis III regions is 0.87 to 1.45 times the LROC QuickMap region slope, so the two agree in size.

**Water, ice and ISRU.** Polar craters that never see sunlight hold water ice, and these cold traps are the main reason for a polar base. NASA Diviner data put the coldest spots in our Artemis III windows at 40 to 96 kelvin as a yearly mean, and its thermal model finds that water ice would stay stable within 2.9 m of the surface under 7% to 60% of the ground. No Earth place matches that; at the coldest Earth terrain match the lowest hourly temperature in 2001 to 2025 was -47 °C (NASA POWER). We group Earth windows by the water or ice test they suit (ISRU, in-situ resource utilization, means making water, oxygen or fuel from local material). Each window is grouped on its own values: dry-surface when aridity is below 0.05 and more than 80% is bare; ice-bearing when the window passes the bare-surface mask and snow or ice covers more than 5% of it, or the mean annual air temperature is below -2 °C (a common proxy for likely permafrost). For Nobile: dry-surface analogs such as Peru and Iran; ice-bearing analogs such as Tibetan Plateau, China and Arctic islands, Canada; terrain analogs such as Mongolia and Iran. Each row comes with a one-line reading and a concrete ISRU test.

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

An AI assistant (Claude by Anthropic) wrote most of the code and most of the texts on the website, in the demo and on this page, following the team's directions. The team defined the problem, chose the lunar targets, selected the known analog sites and the hard negatives, made the geological interpretation and the water and ISRU interpretation, set the AHP weights, and reviewed the results. Every number shown comes from our own result tables.

## NASA Data

- **LRO LOLA south pole elevation, LDEM_80S_80MPP_ADJ** (Planetary Geodesy Data Archive): https://pgda.gsfc.nasa.gov/products/90. Elevation, slope and relief for the Nobile and Artemis III targets.
- **SLDEM2015, LRO LOLA with Kaguya Terrain Camera** (Planetary Geodesy Data Archive): https://pgda.gsfc.nasa.gov/products/54. Elevation, slope and relief for the Apollo targets.
- **LRO Diviner Polar Resource Product** (PDS Geosciences Node): https://pds-geosciences.wustl.edu/missions/lro/diviner.htm. Yearly mean and maximum temperature and ice stability in the polar target windows.
- **NASA POWER climatology, 2001 to 2025**: https://power.larc.nasa.gov/. Lowest hourly temperature in 2001 to 2025 (climatology T2M_MIN), mean daily temperature swing, rain and wind for every Earth window.
- **NASA GIBS and Worldview (MODIS Terra true color, Blue Marble)**: https://worldview.earthdata.nasa.gov/. Map layers and satellite views of every candidate.
- **LRO LROC QuickMap** (Arizona State University): https://quickmap.lroc.asu.edu/. Artemis III region centres and the slope check.
- **NASA SVS CGI Moon Kit and NASA Blue Marble**: https://svs.gsfc.nasa.gov/4720 and https://visibleearth.nasa.gov/images/73909/december-blue-marble-next-generation-w-topography-and-bathymetry. Textures of the two globes on the homepage.

## Space Agency Partner Data and Other References

- **ESA Copernicus DEM GLO-30**: https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM. Earth elevation, slope and relief. Produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.
- **ESA WorldCover 2021 v200** (CC BY 4.0): https://esa-worldcover.org/en. Bare ground and snow share. © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium.
- **JAXA Kaguya (SELENE) Terrain Camera**: https://www.kaguya.jaxa.jp/index_e.htm. Part of SLDEM2015.
- **ESA CAFE analog site catalogue**. Known analog sites, checked against the literature by our team.
- **GLiM, Global Lithological Map Database v1.0** (CC-BY 3.0): Hartmann, J. and Moosdorf, N. (2012), PANGAEA, https://doi.org/10.1594/PANGAEA.788537, and Geochemistry, Geophysics, Geosystems 13, Q12004, https://doi.org/10.1029/2012GC004370. Rock type.
- **Global Aridity Index and Potential Evapotranspiration (ET0) Database, Version 3.1** (CC BY 4.0): Zomer, R. and Trabucco, A. (2019), figshare, https://doi.org/10.6084/m9.figshare.7504448. Dryness.
- **Macrostrat**: https://macrostrat.org/. Rock type check at known sites.
- **Natural Earth admin-0 countries, 1:10m, v5.1.1** (public domain): https://www.naturalearthdata.com/. Country of every window.
- **Esri World Imagery**: high-resolution map layer. Source: Esri, Vantor, Earthstar Geographics, and the GIS User Community.
- **Leaflet** (https://leafletjs.com/), **Plotly** (https://plotly.com/javascript/) and **globe.gl** (https://globe.gl/): map, charts and globes.
