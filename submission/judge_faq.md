# Likely judge questions

**What does the tool do in one sentence?**
It ranks 22,147 Earth windows, each 10 km wide, by how much they look like 13 places on the Moon, and explains where each match breaks.

**How do you know the ranking means anything?**
We tested it on 15 known analog sites and 16 hard negatives (look-alikes with the wrong rock). For the mare target the AUC is 0.92, with a 95% interval of 0.77 to 1.00. A random ranking would give 0.5. None of the hard negatives reaches the top 100 for its own target.

**Did you tune the score on the known sites?**
No. The weights come from AHP (expert pairwise judgments) and were set before testing. The known sites are used only to test the score.

**Why is terrain alone below 0.5 for the mare?**
The mare is flat and bare. So are salt flats, playas and sand seas. On terrain alone, the best salt flat or playa window (Dasht-e Kavir) ranks 245 of 22,147, ahead of 5 of our 7 known mare sites.

**So rock does all the work?**
Partly by design. We picked the look-alikes because their rock differs, so the rock term is expected to separate them. The finding is that terrain alone fails. The step from rock alone (0.82) to rock plus terrain (0.92) suggests terrain helps, but the intervals overlap, so we do not claim it is proven.

**What about the highland and the Artemis III targets?**
The highland test fails (AUC 0.53, interval 0.29 to 0.83) because the global rock map labels both known highland sites with the wrong rock. We say so and mark highland candidates as low confidence. For the Artemis III regions the lunar rock type is not set, so we rank them by terrain only and mark them that way.

**How good is your lunar slope?**
For the Artemis III regions our 10 km median slope is 0.87 to 1.45 times the LROC QuickMap region slope. They agree in size, not exactly, because the areas and methods differ.

**Are these candidates new?**
They lie outside the four well-studied regions (Antarctica, Atacama, Iceland, Hawaii) and are less studied as lunar analogs. We do not claim they are unknown. The Afar region, including the Danakil Depression, is already studied as a Mars and astrobiology analog; what we add is a ranked, checked case for it as a lunar terrain analog. The Arabian basalt fields (harrats) are less studied as lunar mare analogs.
  - Mare (Apollo 11): Arabian Peninsula (32.225, 37.553); Arabian Peninsula (22.495, 40.243); Afar and East Africa (13.135, 40.731)
  - Imbrium rim (Apollo 15): Afar and East Africa (11.995, 41.638); Afar and East Africa (11.495, 42.546); Arabian Peninsula (25.315, 37.649)
  - Highlands (Apollo 16), low confidence: Iran, Afghanistan and Pakistan (32.725, 59.481); Central Asia and Tibet (35.495, 89.887); Iran, Afghanistan and Pakistan (26.635, 66.352)
  - Nobile crater area: Central Asia and Tibet (47.315, 93.199); Iran, Afghanistan and Pakistan (36.225, 58.167); Iran, Afghanistan and Pakistan (32.635, 59.481)
  - Artemis III regions, terrain only: Andes (22 of 45 candidates), then Patagonia; Sahara; Iran, Afghanistan and Pakistan; Galapagos

**Where does the analogy break?**
Everywhere for gravity, vacuum and radiation. On top of that, each candidate card lists its own breaks: rain, plant cover, relief or rock that does not match. For the polar targets, no Earth site has permanent shadow: Diviner puts the coldest spots in our Artemis III windows at 40 to 96 K as a yearly mean, while at the coldest Earth terrain match the lowest hourly temperature in 2001 to 2025 was -47 °C.

**What about water and ice?**
We sort Earth regions into dry-surface analogs (to bury ice and test extraction), ice-bearing analogs (to drill and melt real ice) and terrain analogs (to plan rover routes for moving ice). Diviner's model finds that water ice would stay stable within 2.9 m of the surface (losing less than 1 kg per square metre per billion years) under 7% to 60% of the ground in our Artemis III windows.

**What NASA data did you use?**
LRO LOLA and SLDEM2015 for lunar elevation, LRO Diviner for polar temperatures, NASA POWER for Earth climate, GIBS and Worldview for imagery, and LROC QuickMap for the Artemis III regions.

**What would you do next?**
A finer rock map than GLiM, thermal infrared data (ASTER) to tell basalt from look-alikes from orbit, Diviner for every polar target, and the same method for Mars.

**How did you use AI?**
An AI assistant wrote most of the code and most of the texts, following our directions. The team defined the problem, chose the targets, the known sites and the hard negatives, made the geological and the water and ISRU interpretation, and reviewed the results.
