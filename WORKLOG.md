# WORKLOG (every wall, retry, wrong guess, fix). Entry template at bottom.

## Entries earned during planning (from MASTER_PLAN section 13.2)
- W-001 Research: NativeX page fetch returned nothing; relied on search excerpts. [tool wall]
- W-002 Research: Gemini free-tier limits conflict across sources; no hard-coded number. [data conflict]
- W-003 Plan v1/v2: assumed scene-boundary snapping; data has only 100 scenes / 50 eps. Replaced by block-level cuts. [AI assumption wrong]
- W-004 Plan v2: assumed cliffhangers show up as trailing `?`/interruption; only 9/50 final lines end in ?/!. Now semantic + positional. [AI assumption wrong]  <- best candidate for the doc's "one AI mistake"
- W-005 Data exploration: substring keyword counter gave "ring"=361 blocks; word-boundary truth is 35. [AI code bug]  <- most concrete numbers
- W-006 Plan v2: expected violence lexicon (slap) to help; "slap" appears in 1 block. Rules moved to structure. [AI assumption wrong]
- W-007 Setup: sandbox allowlist excludes free LLM providers; no GitHub connector found. Created D1/D6. [tool wall]

## Entries from the build
- W-008 Step 2 (parse), 8 Nov 2026: first parser run FAILED LOUDLY on episode-006: `SCENE HEADING:` / `SCENE START:` / `SCENE END:` / `ACTIONS AND DIALOGUE:` are UPPER-CASE in that file only (other 49 use "Scene heading:" etc.). The plan said "zero anomalies" because the earlier exploration only used time lines. Fix: scene-metadata regexes made case-insensitive. After fix: 50 eps, 100 scenes, 3727 blocks, CAMERA 1754, ACTION 372, speech 1487 + audio 114 = 1601, runtime 6162.6 s: all match plan section 2.2. [data surprise; also an AI assumption wrong: plan claimed a perfectly uniform grammar] Used in doc: maybe (good example of "parser fails loudly, T9 works").
- W-009 Step 1 (setup), 8 Nov 2026: `mkdir -p dir/{a,b}` created a literal "{a,b}" folder because the tool shell is `sh`; use `bash -c '...'`. [tool quirk]

## Template
### W-0xx · step · date
- What I tried / what went wrong (evidence) / why / what I did instead / result
- Counts as: [AI mistake | data surprise | tool or limit wall | my decision | retry]  · Used in the doc? [Y/N]
- W-010 Step 0 (user), 8 Nov 2026: user watched 5 real promos; 4/5 are JOINED (multi-segment), median 50 s, openings are visual (masked man, hospital bed...), endings are an open relationship/danger question. Effect: stitched candidates stay in the MVP; target_len_prior -> [40,60]; confirms F2. Saved in ground_truth_notes.md. [my decision, backed by user data]
- W-011 Step 3, 8 Nov 2026: first alias heuristic proposed MATRIARCH->NOBLE MATRIARCH AND my override proposed NOBLE MATRIARCH->MATRIARCH (a cycle). Removed the override; alias rows with confidence likely/story default to apply=no until the user confirms. Also my first generic rule would have merged LORD ASHCROFT with LADY ASHCROFT (different people): prefix strip now only fires if the base label exists as its own speaker. [AI mistake, caught in review]

## W-012 (8 Nov, continued session) first shortlist let rule score favour stitched joins and dropped 10 episodes
Shortlist by raw rule score gave 38 stitched / 26 windows but only 40 episodes. Fixed with a stratified pass (best candidate of any source per episode first, then fill by score): 50 of 50 episodes represented.
## W-013 judge notes: my own enum slip caught by the schema
I labelled two hook types as `danger` (a cliffhanger enum). pydantic rejected the whole build (ValidationError on hook.type), I fixed the two lines. Lesson for the doc: schema validation on LLM/human judge output catches vocabulary drift before it reaches the ranking.
## W-014 rule score over-credits episode ends
`ends_ep` (+0.14) rewards any clip that ends where the episode ends, including cosy endings (E19 shortlist #15 ends on a couple nestling: judge gave cliffhanger 2). The rules are a recall filter, not a ranker.
## W-015 sandbox cannot reach any LLM API
Judge = Claude in chat (human-in-loop file, same schema). API path (src/score_pointwise.py) only exercised with the stub (64 ok, 0 hallucinated IDs).
