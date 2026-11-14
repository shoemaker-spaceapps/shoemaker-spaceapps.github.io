# Likely judge questions

**What does the tool do in one sentence?**
It ranks $n_windows Earth windows, each 10 km wide, by how much they look like $n_targets places on the Moon, and explains where each match breaks.

**How do you know the ranking means anything?**
We tested it on $n_sites known analog sites and $n_neg hard negatives (look-alikes with the wrong rock). For the mare target the AUC is $mare_auc, with a 95% interval of $mare_lo to $mare_hi. A random ranking would give 0.5. None of the hard negatives reaches the top 100 for its own target.

**Did you tune the score on the known sites?**
No. The weights come from AHP (expert pairwise judgments) and were set before testing. The known sites are used only to test the score.

**Why is terrain alone below 0.5 for the mare?**
The mare is flat and bare. So are salt flats, playas and sand seas. On terrain alone, the best salt flat or playa window ($best_salt_name) ranks $best_salt_rank of $n_valid, ahead of $n_mare_known_below of our $n_mare_known known mare sites.

**So rock does all the work?**
Partly by design. We picked the look-alikes because their rock differs, so the rock term is expected to separate them. The finding is that terrain alone fails. The step from rock alone ($rock_auc) to rock plus terrain ($mare_auc) suggests terrain helps, but the intervals overlap, so we do not claim it is proven.

**What about the highland and the Artemis III targets?**
The highland test fails (AUC $high_auc, interval $high_lo to $high_hi) because the global rock map labels both known highland sites with the wrong rock. We say so and mark highland candidates as low confidence. For the Artemis III regions the lunar rock type is not set, so we rank them by terrain only and mark them that way.

**How good is your lunar slope?**
For the Artemis III regions our 10 km median slope is $qm_lo to $qm_hi times the LROC QuickMap region slope. They agree in size, not exactly, because the areas and methods differ.

**Are these candidates new?**
They lie outside the four well-studied regions (Antarctica, Atacama, Iceland, Hawaii) and are less studied as lunar analogs. We do not claim they are unknown. The Afar region, including the Danakil Depression, is already studied as a Mars and astrobiology analog; what we add is a ranked, checked case for it as a lunar terrain analog. The Arabian basalt fields (harrats) are less studied as lunar mare analogs.
$robust_md

**Why is Karacadağ not on your main list?**
Our main list keeps only bare or dry ground, where a rover could work. Karacadağ lava field, a basalt plateau in southeastern Türkiye, matches the mare on rock and terrain (rank $kara_rank of $n_valid windows, median slope $kara_s50° against $mare_s50°) but only $kara_bare is bare; most of it is farmland. So we list it as a rock analog: a first candidate for field sampling and XRF analysis, not for surface operations. Some windows sit on rock the global map calls basic plutonic: $oph_list. There the rock is most likely ophiolite, not anorthosite, so we mark them low confidence.

**Where does the analogy break?**
Everywhere for gravity, vacuum and radiation. On top of that, each candidate card lists its own breaks: rain, plant cover, relief or rock that does not match. For the polar targets, no Earth site has permanent shadow: Diviner puts the coldest spots in our Artemis III windows at $div_cold_lo to $div_cold_hi K as a yearly mean, while at the coldest Earth terrain match the lowest hourly temperature in 2001 to 2025 was $earth_cold_C °C.

**What about water and ice?**
We sort Earth windows into dry-surface analogs (aridity below 0.05 and more than 80% bare; to bury ice and test extraction), ice-bearing analogs (bare ground with snow or ice on more than 5% of the window, or mean annual air temperature below -2 °C, a common proxy for likely permafrost; to drill and melt real ice) and terrain analogs (to plan rover routes for moving ice). Each window is grouped on its own values. For Nobile the best dry-surface test region is $nob_dry and the best ice-bearing one $nob_ice. Diviner's model finds that water ice would stay stable within 2.9 m of the surface (losing less than 1 kg per square metre per billion years) under $div_ice_lo to $div_ice_hi of the ground in our Artemis III windows.

**What NASA data did you use?**
LRO LOLA and SLDEM2015 for lunar elevation, LRO Diviner for polar temperatures, NASA POWER for Earth climate, GIBS and Worldview for imagery, and LROC QuickMap for the Artemis III regions.

**What would you do next?**
A finer rock map than GLiM, thermal infrared data (ASTER) to tell basalt from look-alikes from orbit, Diviner for every polar target, and the same method for Mars.

**How did you use AI?**
An AI assistant wrote most of the code and most of the texts, following our directions. The team defined the problem, chose the targets, the known sites and the hard negatives, made the geological and the water and ISRU interpretation, and reviewed the results.
