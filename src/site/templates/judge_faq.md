# Likely judge questions

**What does the tool do in one sentence?**
It ranks $n_windows Earth windows, each 10 km wide, by how much they look like $n_targets places on the Moon, and explains where each match breaks.

**How do you know the ranking means anything?**
We tested it on $n_sites known analog sites and $n_neg hard negatives (look-alikes with the wrong rock). For the mare target the AUC is $mare_auc, with a 95% interval of $mare_lo to $mare_hi. A random ranking would give 0.5. None of the hard negatives reaches the top 100 for its own target.

**Did you tune the score on the known sites?**
No. The weights come from AHP (expert pairwise judgments) and were set before testing. The known sites are used only to test the score.

**Why is terrain alone below 0.5 for the mare?**
The mare is flat and bare. So are salt flats and sand seas. On terrain alone, the best salt flat window ($best_salt_name) ranks $best_salt_rank of $n_windows, ahead of $n_mare_known_below of our $n_mare_known known mare sites. Rock type is what separates them, which is why the combined score reaches $mare_auc.

**What about the highland and the Artemis III targets?**
The highland test fails (AUC $high_auc, interval $high_lo to $high_hi) because the global rock map labels both known highland sites with the wrong rock. We say so and mark highland candidates as low confidence. For the Artemis III regions the lunar rock type is not set, so we rank them by terrain only and mark them that way.

**How good is your lunar slope?**
For the Artemis III regions our 10 km median slope is $qm_lo to $qm_hi times the LROC QuickMap region slope. They agree in size, not exactly, because the areas and methods differ.

**Which candidates are new?**
$robust_md

**Where does the analogy break?**
Everywhere for gravity, vacuum and radiation. On top of that, each candidate card lists its own breaks: rain, plant cover, relief or rock that does not match. For the polar targets, no Earth site has permanent shadow: Diviner puts the coldest spots in our Artemis III windows at $div_cold_lo to $div_cold_hi K as a yearly mean, while the coldest Earth terrain match has a coldest-month minimum of $earth_cold_C °C.

**What about water and ice?**
We sort Earth regions into dry-surface analogs (to bury ice and test extraction), ice-bearing analogs (to drill and melt real ice) and terrain analogs (to plan rover routes for moving ice). Diviner's model finds buried ice could stay stable under $div_ice_lo to $div_ice_hi of the ground in our Artemis III windows.

**What NASA data did you use?**
LRO LOLA and SLDEM2015 for lunar elevation, LRO Diviner for polar temperatures, NASA POWER for Earth climate, GIBS and Worldview for imagery, and LROC QuickMap for the Artemis III regions.

**What would you do next?**
A finer rock map than GLiM, thermal infrared data (ASTER) to tell basalt from look-alikes from orbit, Diviner for every polar target, and the same method for Mars.

**How did you use AI?**
For coding, debugging, data processing scripts and first drafts of texts. The team made the scientific decisions and checked every result.
