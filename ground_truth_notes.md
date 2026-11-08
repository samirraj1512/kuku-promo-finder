# Step 0 ground truth: real promos watched by the user (8 Nov 2026), verbatim observations lightly tidied

| # | Title / platform | Length | First 3 s | Structure | Ending (open question) | Clear alone? |
|---|---|---|---|---|---|---|
| 1 | Duke With Benefits, Official Trailer (2024) | 59 s | introduces a charming male lead | joined together | they finally admit they're in love, but the boy has a fiance | yes |
| 2 | Nero: Made Men, Teaser, ReelShort | 21 s | a scary masked man | joined together | why did he kidnap the girl; who is he unmasked; are they related | no |
| 3 | "She's pregnant with a billionaire's child!" | 13 s | woman in a hospital bed | continuous | they didn't know she was pregnant | yes |
| 4 | Kidnapped by the Devil, Trailer, Full Cast, ReelShort | 50 s | woman panicking | joined | will the drug dealer keep her; what will she do | yes |
| 5 | Baby, Please Don't Marry Him, Trailer, Full Cast, ReelShort | 55 s | rich woman in a car | joined | who will the girl finally be with | yes |

## What this tells the build (calibration)
- 4 of 5 are "joined" (multi-segment): stitched candidates (source 3c) are NOT optional. Keep them in the MVP, drop only if time is gone. Up to 3 segments (HC5) is right.
- Lengths 13, 21, 50, 55, 59 s: median 50 s. Set soft `target_len_prior` to [40, 60]; the hard 20-60 rule stays. (13 s is below the brief's 20 s floor.)
- First 3 s is a VISUAL character/situation image (masked man, hospital bed, panicking woman, woman in car), not a spoken line. Confirms finding F2: CAMERA/ACTION text must reach the model and hook rules must not rely on dialogue.
- Endings are an open QUESTION about the relationship or danger ("will she...", "who is he", "who will she choose"). Matches rubric cliff types: mystery, decision, danger. Add `romantic_triangle/decision` weight in cliff_type vocab if needed.
- 3 of 5 are official trailers/teasers (made from a whole series), not episode clips. The brief wants clips from the show itself, so we only borrow their STRUCTURE.
- The one promo that was NOT clear alone (#2) was the shortest-hook-with-no-setup teaser (a mystery with no context): supports the cold-viewer clarity gate.
- Caveat: n=5, one rater, platform trailers: indicative only. State in the doc.
