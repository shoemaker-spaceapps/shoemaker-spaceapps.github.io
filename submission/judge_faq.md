# Likely judge questions

**What does the tool do in one sentence?**
It ranks 22,147 Earth windows, each 10 km wide, by how much they look like 13 places on the Moon, and explains where each match breaks.

**How do you know the ranking means anything?**
We tested it on 15 known analog sites and 16 hard negatives (look-alikes with the wrong rock). For the mare target the AUC is 0.92, with a 95% interval of 0.77 to 1.00. A random ranking would give 0.5. None of the hard negatives reaches the top 100 for its own target.

**Did you tune the score on the known sites?**
No. The weights come from AHP (expert pairwise judgments) and were set before testing. The known sites are used only to test the score.

**Why is terrain alone below 0.5 for the mare?**
The mare is flat and bare. So are salt flats and sand seas. On terrain alone, the best salt flat window (Salar de Atacama) ranks 518 of 22,147, ahead of 5 of our 7 known mare sites. Rock type is what separates them, which is why the combined score reaches 0.92.

**What about the highland and the Artemis III targets?**
The highland test fails (AUC 0.53, interval 0.29 to 0.83) because the global rock map labels both known highland sites with the wrong rock. We say so and mark highland candidates as low confidence. For the Artemis III regions the lunar rock type is not set, so we rank them by terrain only and mark them that way.

**How good is your lunar slope?**
For the Artemis III regions our 10 km median slope is 0.87 to 1.45 times the LROC QuickMap region slope. They agree in size, not exactly, because the areas and methods differ.

**Which candidates are new?**
  - Mare (Apollo 11): Arabian Peninsula (32.225, 37.553); Arabian Peninsula (22.495, 40.243); Afar and East Africa (13.135, 40.731)
  - Imbrium rim (Apollo 15): Afar and East Africa (11.995, 41.638); Afar and East Africa (11.495, 42.546); Arabian Peninsula (25.315, 37.649)
  - Highlands (Apollo 16), low confidence: Iran, Afghanistan and Pakistan (32.725, 59.481); Central Asia and Tibet (35.495, 89.887); Iran, Afghanistan and Pakistan (26.635, 66.352)
  - Nobile crater area: Central Asia and Tibet (47.315, 93.199); Iran, Afghanistan and Pakistan (36.225, 58.167); Iran, Afghanistan and Pakistan (32.635, 59.481)
  - Artemis III regions, terrain only: Andes (22 of 45 candidates), then Patagonia; Sahara; Iran, Afghanistan and Pakistan; Galapagos

**Where does the analogy break?**
Everywhere for gravity, vacuum and radiation. On top of that, each candidate card lists its own breaks: rain, plant cover, relief or rock that does not match. For the polar targets, no Earth site has permanent shadow: Diviner puts the coldest spots in our Artemis III windows at 40 to 96 K as a yearly mean, while the coldest Earth terrain match has a coldest-month minimum of -47 °C.

**What about water and ice?**
We sort Earth regions into dry-surface analogs (to bury ice and test extraction), ice-bearing analogs (to drill and melt real ice) and terrain analogs (to plan rover routes for moving ice). Diviner's model finds buried ice could stay stable under 7% to 60% of the ground in our Artemis III windows.

**What NASA data did you use?**
LRO LOLA and SLDEM2015 for lunar elevation, LRO Diviner for polar temperatures, NASA POWER for Earth climate, GIBS and Worldview for imagery, and LROC QuickMap for the Artemis III regions.

**What would you do next?**
A finer rock map than GLiM, thermal infrared data (ASTER) to tell basalt from look-alikes from orbit, Diviner for every polar target, and the same method for Mars.

**How did you use AI?**
For coding, debugging, data processing scripts and first drafts of texts. The team made the scientific decisions and checked every result.
