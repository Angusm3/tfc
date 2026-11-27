# TFC's own art and sound inventory

Files copied unchanged from `legacy-0.32/` (bits, audio) into this mod. A file is TFC's own when it is not byte-identical to a
file the 2014 stock `cnc` mod shipped, and is not already provided by stock 20250330 `cnc` (`mods/tfc/bits`, `uibits` or the
C&C content mixes). Sprites sit in `bits/` (mounted as `tfc|bits`); sounds sit in `audio/` (mounted as `tfc|audio`, added to
`mod.yaml` by this change). Counts: 78 sprites, 86 sounds (79 .aud, 7 .wav), 0 UI art.

Column "Used by in 0.32" lists the 0.32 data files whose text mentions the file's name (a name match, so rules files can appear
for sprites whose name is also an actor name); "unused in 0.32" means no 0.32 yaml or lua file mentions it.

| File | Type | Used by in 0.32 |
|---|---|---|
| audio/deagle.wav | sound (WAV) | factions/tfa/rules/army.yaml, weapons.yaml |
| audio/fouronthefloor.aud | sound (AUD) | voice set HijackerVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/goingmyway.aud | sound (AUD) | unused in 0.32 |
| audio/hitit.aud | sound (AUD) | voice set HijackerVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/hotwired.aud | sound (AUD) | voice set HijackerVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/icraata.aud | sound (AUD) | voice set IvanVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/icraatb.aud | sound (AUD) | voice set IvanVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/icraatc.aud | sound (AUD) | voice set IvanVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/icraatd.aud | sound (AUD) | voice set IvanVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/icradia.aud | sound (AUD) | voice set IvanVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/icradib.aud | sound (AUD) | voice set IvanVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/icramoa.aud | sound (AUD) | voice set IvanVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/icramob.aud | sound (AUD) | voice set IvanVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/icramoc.aud | sound (AUD) | voice set IvanVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/icramod.aud | sound (AUD) | voice set IvanVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/icramof.aud | sound (AUD) | voice set IvanVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/icrasea.aud | sound (AUD) | voice set IvanVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/icraseb.aud | sound (AUD) | voice set IvanVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/icrasec.aud | sound (AUD) | voice set IvanVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/icrased.aud | sound (AUD) | voice set IvanVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/icrasee.aud | sound (AUD) | voice set IvanVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/icrasef.aud | sound (AUD) | voice set IvanVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/infgun3.aud | sound (AUD) | weapons.yaml |
| audio/iseaata.aud | sound (AUD) | voice set SealVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/iseaatb.aud | sound (AUD) | voice set SealVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/iseaatc.aud | sound (AUD) | voice set SealVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/iseadia.aud | sound (AUD) | voice set SealVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/iseadib.aud | sound (AUD) | voice set SealVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/iseadic.aud | sound (AUD) | voice set SealVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/iseamoa.aud | sound (AUD) | voice set SealVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/iseamob.aud | sound (AUD) | voice set SealVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/iseamoc.aud | sound (AUD) | voice set SealVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/iseasea.aud | sound (AUD) | voice set SealVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/iseaseb.aud | sound (AUD) | voice set SealVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/iseasec.aud | sound (AUD) | voice set SealVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/iseased.aud | sound (AUD) | voice set SealVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itanata.aud | sound (AUD) | voice set TanyaVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itanatb.aud | sound (AUD) | voice set TanyaVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itanatc.aud | sound (AUD) | voice set TanyaVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itanatd.aud | sound (AUD) | voice set TanyaVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itandia.aud | sound (AUD) | voice set TanyaVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itanmoa.aud | sound (AUD) | voice set TanyaVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itanmob.aud | sound (AUD) | voice set TanyaVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itanmoc.aud | sound (AUD) | voice set TanyaVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itanmod.aud | sound (AUD) | voice set TanyaVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itanmoe.aud | sound (AUD) | voice set TanyaVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itanmof.aud | sound (AUD) | voice set TanyaVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itansea.aud | sound (AUD) | voice set TanyaVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itanseb.aud | sound (AUD) | voice set TanyaVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itansec.aud | sound (AUD) | voice set TanyaVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itansed.aud | sound (AUD) | voice set TanyaVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itansee.aud | sound (AUD) | voice set TanyaVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itesata.aud | sound (AUD) | voice set ShockVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itesatb.aud | sound (AUD) | voice set ShockVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itesatc.aud | sound (AUD) | voice set ShockVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itesatd.aud | sound (AUD) | voice set ShockVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itesate.aud | sound (AUD) | voice set ShockVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itesdia.aud | sound (AUD) | voice set ShockVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itesdib.aud | sound (AUD) | voice set ShockVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itesdic.aud | sound (AUD) | voice set ShockVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itesdid.aud | sound (AUD) | voice set ShockVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itesmoa.aud | sound (AUD) | voice set ShockVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itesmob.aud | sound (AUD) | voice set ShockVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itesmoc.aud | sound (AUD) | voice set ShockVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itesmod.aud | sound (AUD) | voice set ShockVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itesmoe.aud | sound (AUD) | voice set ShockVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itesmof.aud | sound (AUD) | voice set ShockVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itessea.aud | sound (AUD) | voice set ShockVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itessec.aud | sound (AUD) | voice set ShockVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itessed.aud | sound (AUD) | voice set ShockVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/itessee.aud | sound (AUD) | voice set ShockVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/jackemup.aud | sound (AUD) | HijackerVoice Build (0.32 wrote jackmeup, a typo; corrected in tfc-voices.yaml); unused in 0.32 as written |
| audio/needaride.aud | sound (AUD) | voice set HijackerVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/nokeysnoproblem.aud | sound (AUD) | voice set HijackerVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/obelpowr.wav | sound (WAV) | factions/nod/rules/army.yaml |
| audio/obelray1.wav | sound (WAV) | weapons.yaml, weaponsV.yaml |
| audio/prifle.wav | sound (WAV) | factions/nod/rules/army.yaml, weapons.yaml |
| audio/SKS.wav | sound (WAV) | factions/tfa/rules/army.yaml, weapons.yaml |
| audio/sup.aud | sound (AUD) | unused in 0.32 |
| audio/SV98.wav | sound (WAV) | weapons.yaml |
| audio/tesla1.aud | sound (AUD) | weapons.yaml |
| audio/tslachg2.aud | sound (AUD) | factions/tfa/rules/army.yaml |
| audio/what.aud | sound (AUD) | voice set HijackerVoice (voices.yaml, now audio/tfc-voices.yaml) |
| audio/wheredoyouwantit.aud | sound (AUD) | unused in 0.32 |
| audio/wlvrgun.wav | sound (WAV) | weapons.yaml |
| audio/yeah.aud | sound (AUD) | voice set HijackerVoice (voices.yaml, now audio/tfc-voices.yaml) |
| bits/aslr.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml, rules/ai.yaml |
| bits/aslricon.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/bdzr.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml, rules/ai.yaml, rules/husks.yaml |
| bits/bdzricon.shp | sprite (SHP) | factions/tfa/sequences/army.yaml, rules/husks.yaml |
| bits/cmbt.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml, rules/ai.yaml, rules/defaults.yaml |
| bits/cmbticon.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/ecdr.shp | sprite (SHP) | factions/nod/rules/army.yaml, factions/nod/sequences/army.yaml, rules/ai.yaml |
| bits/ecdricon.shp | sprite (SHP) | factions/nod/sequences/army.yaml |
| bits/fb1.shp | sprite (SHP) | unused in 0.32 |
| bits/fb2.shp | sprite (SHP) | sequences/misc.yaml |
| bits/fb3.shp | sprite (SHP) | sequences/misc.yaml, weapons.yaml |
| bits/fgtnbarracks.shp | sprite (SHP) | unused in 0.32 |
| bits/fhtnk.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml, rules/ai.yaml, rules/husks.yaml, rules/world.yaml |
| bits/fhtnkicon.shp | sprite (SHP) | factions/tfa/sequences/army.yaml, rules/husks.yaml |
| bits/fsal.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml, rules/ai.yaml |
| bits/fsal2.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/fsalicon.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/fsalmake.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/fsam.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml |
| bits/fsamicon.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/fsammake.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/ftch.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml, rules/ai.yaml, rules/husks.yaml, rules/world.yaml |
| bits/ftchicon.shp | sprite (SHP) | factions/tfa/sequences/army.yaml, rules/husks.yaml |
| bits/grnh.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml, rules/ai.yaml |
| bits/grnhicon.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/grnhmake.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/hjkr.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml, rules/ai.yaml |
| bits/hjkricon.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/hqgdi.shp | sprite (SHP) | factions/gdi/rules/army.yaml, sequences/structures.yaml |
| bits/hqnod.shp | sprite (SHP) | factions/nod/rules/army.yaml, sequences/structures.yaml |
| bits/huey.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml |
| bits/hueyicon.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/litning.shp | sprite (SHP) | sequences/misc.yaml |
| bits/mech.shp | sprite (SHP) | factions/gdi/rules/army.yaml, factions/nod/rules/army.yaml, factions/nod/sequences/army.yaml, rules/ai.yaml, weapons.yaml |
| bits/mechicon.shp | sprite (SHP) | factions/nod/sequences/army.yaml |
| bits/medi.shp | sprite (SHP) | factions/gdi/rules/army.yaml, factions/gdi/sequences/army.yaml, rules/ai.yaml |
| bits/mediicon.shp | sprite (SHP) | factions/gdi/sequences/army.yaml |
| bits/mgnst.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml, rules/ai.yaml |
| bits/mgnsticon.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/mlta.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml, rules/ai.yaml |
| bits/mltaicon.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/mltv.shp | sprite (SHP) | sequences/misc.yaml, weapons.yaml |
| bits/mltvinf.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml, rules/ai.yaml |
| bits/mltvinficon.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/mrtr.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml, rules/ai.yaml |
| bits/mrtricon.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/parach.shp | sprite (SHP) | sequences/misc.yaml |
| bits/paradrop.shp | sprite (SHP) | rules/aircraftV.yaml |
| bits/pinficon.shp | sprite (SHP) | sequences/misc.yaml |
| bits/prflicon.shp | sprite (SHP) | sequences/infantry.yaml |
| bits/rdst.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml |
| bits/rdsticon.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/rdstmake.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/rfnry.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml, rules/ai.yaml |
| bits/rfnryicnh.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/rfnrymake.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/slar.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml, rules/ai.yaml |
| bits/slaricon.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/slarmake.shp | sprite (SHP) | unused in 0.32 |
| bits/smaw.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml, rules/ai.yaml, rules/world.yaml |
| bits/smawicon.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/snpr.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml |
| bits/snprd.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml |
| bits/snpricon.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/spc.shp | sprite (SHP) | factions/nod/rules/army.yaml, factions/nod/sequences/army.yaml |
| bits/spcicon.shp | sprite (SHP) | factions/nod/sequences/army.yaml |
| bits/tent.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml, rules/ai.yaml |
| bits/tenticon.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/tentmake.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/tfsr.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml |
| bits/tfsricon.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/tsla.shp | sprite (SHP) | factions/tfa/rules/army.yaml, factions/tfa/sequences/army.yaml, rules/ai.yaml |
| bits/tslaicon.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/tslamake.shp | sprite (SHP) | factions/tfa/sequences/army.yaml |
| bits/vlcn.shp | sprite (SHP) | factions/gdi/rules/army.yaml, factions/gdi/sequences/army.yaml, rules/ai.yaml |
| bits/vlcnicon.shp | sprite (SHP) | factions/gdi/sequences/army.yaml |
| bits/wlvr.shp | sprite (SHP) | factions/gdi/rules/army.yaml, factions/gdi/sequences/army.yaml, rules/ai.yaml |
| bits/wlvricon.shp | sprite (SHP) | factions/gdi/sequences/army.yaml |

## Not copied

- `uibits/chrome.png`: TFC's 0.32 file differs from the stock one already in `mods/tfc/uibits/`; not overwritten (chrome lane).
- 0.32 files identical to the 2014 stock mod but absent from stock 20250330 `cnc`: `bits/apctur2.shp`, `bits/crate.shp`,
  `bits/cursor.pal`, `bits/lstnew.shp`, `bits/lstnew2.shp`, `bits/overlay.shp`, `uibits/reticle.png`, `uibits/strategic.png`.
- 0.32 files identical to the 2014 stock mod whose stock 20250330 counterpart has different content (the stock 20250330 file is used):
  `apctur.shp`, `eye.shp`, `eyemake.shp`, `fact.shp`, `handmake.shp`, `harvdump.shp`, `levelup.shp`, `missmake.shp`, `mouse2.shp`,
  `mouse4.shp`, `mpspawn.shp`, `pylemake.shp`, `rank.shp`, `silo.shp`, `silomake.shp`, `snow.mix`, `v19.shp`, `waypoint.shp`.
- `audio/nuyell6.aud`, `nuyell7`, `nuyell10`, `nuyell11`, `nuyell12`: byte-identical to the stock `bits/` copies.
