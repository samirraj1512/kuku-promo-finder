# Promo Finder: Master Plan (v3)

**Assignment:** Kuku AI Generalist, Problem 1 "Find the Promos"
**Show in the input pack:** *I Married a Broken Soldier. He Was a Duke* (50 episodes, English, US audience)
**Document date:** 8 Nov 2026
**Status:** planning complete, build not started
**Supersedes:** the 11-step plan (v1) and the research-upgraded plan (v2) from the chat. This file is the single source of truth.

---

## 0. Read this first

### 0.1 Legend

| Mark | Meaning |
|---|---|
| 🤖 | Claude does it (code, runs, drafts) |
| 🛑 | **You** must act or decide. Work pauses here. |
| 📝 | An entry goes into `WORKLOG.md` (every wall, retry, wrong guess, fix) |
| ✅ | Measured from your actual data in this chat |
| 🔬 | Hypothesis, to be tested during the build |
| ⚠️ | Unverified or conflicting information. Check before relying on it. |

### 0.2 The approach in six lines

1. Parse all 50 screenplays into numbered blocks with exact timestamps (plain code, no AI).
2. Generate promo candidates from **three independent sources**: rule-based windows, an LLM that reads each episode and proposes spans, and stitched "hook + recap + cliffhanger" combinations.
3. The model **never writes timestamps**. It picks block IDs and my code converts IDs to times, so invented timestamps are impossible.
4. Score with an anchored rubric (pointwise), test "makes sense alone" with a cold-viewer call, then rank the top ~12 with pairwise comparisons in both orders.
5. Check quality against **your blind labels**, baselines (random and "last 45 seconds"), an ablation table, and a second model. Report failures honestly.
6. Everything is rerunnable on a new show with one command, and the model is a config line.

### 0.3 What changed since v2 (because I looked at your data)

| Finding | Effect on the plan |
|---|---|
| Only **100 scenes** across 50 episodes (25 episodes are a single scene) | Scene boundaries are useless for snapping. Cut at block level. |
| Only **9 of 50** episodes end on a spoken line ending in `?` or `!` (41 end on a full stop) | Punctuation heuristics for cliffhangers are weak. Cliffhanger detection must be semantic plus positional. |
| **46 of 50** episodes end on a CAMERA block, a median 5.5 s after the last spoken line | The cliffhanger is a final visual beat. The clip must end at the end of that block, not the last line of speech. |
| **17 of 50** episodes open with no speech or sound in the first 3 s | The hook is sometimes visual. CAMERA and ACTION text must reach the model. |
| `SOUND FX` shows up as a "speaker" (114 blocks) and `JULIANA` / `LADY JULIANA` are the same person | The parser needs a speaker-normalisation step and an audio-cue type. |
| The whole show is only about **68k tokens** of text (about 5k for the logline and continuity notes of all 50 episodes) | The LLM can afford to read **every** episode. This enables the "LLM proposer" source and makes cost small. |
| My own first keyword count was wrong (substring matches: "ring" inside other words gave 361; the real count is 35) | Logged as a real AI mistake (Section 13). Sanity checks are part of the method. |

### 0.4 How to use this document

- Sections 1 to 5: understanding (task, data, research, assumptions, architecture).
- **Section 6: the step-by-step workflow. This is the part to follow while building.**
- Sections 7 to 11: the specifications behind the steps (prompts, evaluation, cost, risks, privacy).
- Sections 12 to 16: your checklist, the worklog protocol, the doc and video blueprints, and the submission checklist.
- Appendices: sources, config, schemas, pseudocode.

### 0.5 Honest scope note

The brief suggests 2 to 3 hours. This plan is larger. Section 12.3 defines an **MVP path** (about 3.5 to 4 hours of your hands-on time, with me doing the heavy lifting) and a **Full path** (about 5 hours). Both are above the brief's suggested 2 to 3 hours, so decide early how far to go. If time is short, cut at the marked lines. A simple, honest submission that runs beats a large one that doesn't.

---

## 1. The assignment in one page

### 1.1 What is asked

Build a tool that reads microdrama screenplays and finds the best promos. For each promo: episode, start and end timestamp of **every segment, in order**, the hook, the cliffhanger, and one line on why it works. Then **rank** them (what to post first and why), and **check quality** (where does the tool pick badly?).

### 1.2 Operational definition of a promo (used by the validators)

Hard constraints (the code rejects anything that fails):

| ID | Rule |
|---|---|
| HC1 | Total duration of all segments is between **20 and 60 seconds** |
| HC2 | Every segment lies inside one episode and uses real, existing timestamps |
| HC3 | Segments are listed in order (chronological within an episode, ascending by episode number across episodes) |
| HC4 | No cut lands **inside** a spoken line or sound cue |
| HC5 | At most 3 segments per promo |
| HC6 | No near-duplicate of a higher-ranked promo (same episode, time overlap above 30%) |

Soft qualities (scored): a **hook** in the first ~3 seconds, a **cliffhanger** ending (unresolved), **standalone clarity** for someone who has never seen the show.

### 1.3 How we'll be judged and where each lens is answered

| Lens (from the brief) | What they want | Our evidence | Artifact |
|---|---|---|---|
| Problem choice and framing | Why this problem, scoping, assumptions | Sections 1, 4, doc page 1 | Assumptions register |
| Approach and scale | What is AI vs code vs human; cost at volume | Sections 5, 9 | Architecture, cost model |
| Quality checking | Real runs, honest failures | Sections 8, 10 | Golden-set metrics, ablation table, failure log |
| The prototype | Runs on real inputs, usable output | Steps 11 to 12 | Colab notebook, repo, ranked output |
| Communication | Clear, specific, short | Sections 14, 15 | 2-page PDF, 3-minute video |

### 1.4 Constraints to respect

48-hour deadline (late = not reviewed) · free tiers are enough · must be **rerunnable on a new input in the interview** · model should be **easy to swap** · tell them which AI tools you used and **one place they got it wrong** · the pack is confidential (use with AI tools is allowed, **publishing or sharing it is not**) · submit once, one problem.

---

## 2. The data: measured facts ✅

All numbers below were computed from your uploaded zip in this chat.

### 2.1 File grammar

```
EPISODE NUMBER: Episode N
EPISODE LOGLINE: one sentence summary
CONTINUITY NOTES: what this episode sets up
(blank)
--- SCRIPT START ---
SCENE NN
Scene heading: INT./EXT. LOCATION – TIME
Scene start: mm:ss.ss
Scene end: mm:ss.ss
Actions and dialogue:

**CAMERA:**
Start: (mm:ss.ss) | End: (mm:ss.ss)
<shot description>

**ACTION:**
Start: (mm:ss.ss) | End: (mm:ss.ss)
<what happens>

**SPEAKER NAME (Emotion, Emotion):**
Start: (mm:ss.ss) | End: (mm:ss.ss)
"<spoken line>"
```

- UTF-8, with accented characters and en dashes.
- Timestamps are **per episode**, starting at `00:00.00` in every file.
- File names are `episode-NNN-Episode <id>.txt`. The numeric `<id>` is **not** the episode number (see trap T6).

### 2.2 Measured statistics

| Measure | Value |
|---|---|
| Episodes | 50 (header number matches file prefix in all 50) |
| Total runtime | 6,163 s ≈ **102.7 min** |
| Episode length (s) | min 70.5 · p10 83.2 · **median 117.8** · p90 160.0 · max 200.8 |
| Scenes | **100 total**; per episode min 1, median 1.5, max 5; 25 episodes have exactly one scene |
| Scene length (s) | min 2.3 · median 45.9 · max 200.8; scenes are contiguous (max gap 0) |
| Blocks | **3,727** (CAMERA 1,754 · ACTION 372 · speaker blocks 1,601); per episode min 37, median 73, max 121 |
| Spoken-line length | median 5 words, p90 12, max 33; about 1.5 spoken words per second |
| Speaker labels | 65 distinct (SOUND FX counts as one); 11 appear exactly once; SOUND FX is 7.1% of speaker blocks |
| Emotion tags | **661** distinct (open vocabulary, not a fixed list) |
| Overlapping speech | 39 of 1,551 consecutive speech-or-sound block pairs overlap (about 2.5%) |
| Raw size | 528,811 characters ≈ 132k tokens (chars ÷ 4, includes timestamps and formatting); average 2,644 per episode, max about 4k |
| Text only (no formatting) | ≈ 68k tokens; CAMERA is 63% of characters, ACTION 14%, speech 23% |
| Series bible (logline + continuity for all 50) | ≈ 5k tokens |
| Timestamp anomalies | **0** (no end before start, no gaps between scenes) |

### 2.3 Openings and endings

| Measure | Value | Why it matters |
|---|---|---|
| First block of every episode | CAMERA (50/50) | Openings are described visually first |
| First spoken line starts at | median 1.9 s (range 0 to 18.3 s) | Most episodes get to speech fast |
| Speech or sound within first 3 s | 33 of 50; 17 have none | 34% of openings must hook visually |
| SOUND FX within first 3 s | 16 episodes | Audio stings are a hook signal |
| Last block kind | CAMERA 46 · ACTION 3 · SOUND FX 1 | Endings are visual |
| Gap between last spoken line and episode end | median **5.5 s**, max 16.8 s | End the clip at the real end, not the last word |
| Final spoken line ends with | `.` 41 · `?` 5 · `!` 4 | Punctuation rules would miss most cliffhangers |
| SOUND FX in the last 5 s | 17 episodes | Stings often close episodes |
| Final block mentions a close-up | 27 of 50 | Reaction close-ups are a common final beat |
| A 60 s clip as a share of an episode | 30% to 85% (median 51%) | A promo is often half an episode, so multi-segment stitching matters for skipping filler |

### 2.4 Keyword reality check (word-boundary counts, blocks / episodes)

`tears` 58/32 · `ring` 35/12 · `crown` 30/8 · `duke` 26/13 · `fire` 21/10 · `dead` 19/11 · `gasps` 11/11 · `poison` 11/7 · `faint` 10/10 · `truth` 10/8 · `blood` 9/5 · `slap` **1/1**.

Meaning: this show runs on identity, status and betrayal tension, not physical shock. A generic "slap / strike" lexicon would almost never fire here. **Rules must lean on structure** (timing, position, intensity, reaction beats), not on a violence word list. That also keeps the tool reusable on other shows.

### 2.5 Findings and design consequences

| # | Finding | Consequence |
|---|---|---|
| F1 | Scenes are too coarse (100 total) | Cut points are derived from blocks and silence gaps, never from scenes |
| F2 | 34% of openings have no early speech or sound | Hook scoring must read CAMERA and ACTION lines as well as dialogue |
| F3 | Endings are a final visual beat 5.5 s after the last line (median) | End-of-episode candidates extend to the end of the final block |
| F4 | Final lines rarely end in `?` or `!` | Cliffhanger = semantic judgment (LLM) plus position prior, not punctuation |
| F5 | SOUND FX is a speaker label | Treat as an `audio_cue` type, exclude it from "spoken line" counts, but keep it as a hook and cliffhanger signal |
| F6 | Speaker aliasing (`JULIANA` / `LADY JULIANA`; descriptive one-offs such as "MYSTERIOUS BEARDED MAN") | Normalisation table; also drives the "characters not introduced in the clip" penalty |
| F7 | 661 emotion tags | Map by keyword stems to intensity buckets (high / medium / low); unknown tags default to medium |
| F8 | 2.5% overlapping speech | Sort by start; a window's end is the maximum end of the blocks it includes |
| F9 | The full show is about 68k tokens | An LLM can read every episode: cheap, and enables the proposer source |
| F10 | Episodes run about 2 minutes, and promos are 20 to 60 s | Promo candidates overlap heavily within an episode. De-duplication (non-max suppression) is essential. |
| F11 | No audio or video in the pack | The tool judges **script only**. Acting, music and pacing are invisible. This is a stated limit. |
| F12 | File IDs jump (eps 1 to 20, 21 to 30, 31 to 38, 39 to 45, 46 to 49, and 50 sit in separate ID ranges, likely upload batches) | 🔬 Check whether style drifts across batches (a possible source of bias) |

### 2.6 Parser traps (all must be handled and tested)

| ID | Trap | Handling |
|---|---|---|
| T1 | Speaker blocks have the form `NAME (Emotion, Emotion)` | Regex `^(.*?)\s*\((.*?)\)$`; some labels have no emotion |
| T2 | `SOUND FX` masquerades as a speaker | Reclassify as `audio_cue` |
| T3 | Name aliases | Alias map, with automatic suggestions (strip `LADY`, `LORD` and so on) and your confirmation |
| T4 | Overlapping CAMERA, ACTION and speech blocks | Blocks are a timeline of intervals, not a sequence; sort by start, tie-break by kind |
| T5 | 2.5% speech overlap | End = max end of included blocks |
| T6 | The numeric file ID is not the episode number | Use the `NNN` prefix and the `EPISODE NUMBER` header, and assert they match |
| T7 | Non-ASCII characters | Open files as UTF-8 |
| T8 | Block text can contain colons or asterisks | Match block headers only with the strict pattern `^\*\*(.+?):\*\*\s*$` |
| T9 | A new show may deviate from this format | Parser fails loudly with file and line number, never silently skips; the parse report lists every anomaly |

---

## 3. Research digest

### 3.1 How much to trust each source

| Tier | Type | Use |
|---|---|---|
| A | Peer-reviewed or arXiv papers, official provider documentation | Methods and constraints. Highest trust. |
| B | Business press, company filings coverage | Context about Kuku and the market |
| C | Vendor and practitioner blogs (ad-tech, AI-video tools, writing sites) | **Hypotheses only.** Treated as testable ideas, not facts. |

Most of the **creative** guidance (hook formulas, ad structure, what makes a cliffhanger work) is Tier C. Most of the **method** guidance (judge bias, structured outputs, evaluation statistics) is Tier A or practitioner analysis backed by papers. Full list with URLs is in Appendix A.

### 3.2 Findings and the decision each one drives

| # | Finding | Tier | Decision |
|---|---|---|---|
| R1 | Microdrama ads typically open on conflict, give a short backstory recap, then end on a cliffhanger | C | Add a **stitched** candidate type: hook, then a recap beat, then a cliffhanger |
| R2 | One ad-intelligence snapshot of top DramaBox ads found several running about 46 to 64 s (a snapshot, not an experiment) | C | Soft length prior toward 40 to 60 s; the hard rule stays 20 to 60 s |
| R3 | The format treats an immediate hook as mandatory and every episode as ending on an unanswered question | B/C | Every episode end is a pre-built cliffhanger and every opening a pre-built hook, so seed candidates there and add a "last 45 s of each episode" **baseline** |
| R4 | Hook formulas named by practitioners: status reversal, impossible situation, hidden identity, ticking clock, shocking revelation | C | Used as an **enum** vocabulary so the model cannot invent categories. Two domain additions (`public_humiliation`, `confrontation`) are my own and are flagged as such. |
| R5 | Cliffhanger types: danger, revelation, decision, mystery, betrayal, ticking clock; repeating one type dulls the effect | C | Enum plus a **diversity rule** in the final list |
| R6 | One practitioner claims unresolved consequence beats pure surprise | C (anecdotal) | 🔬 Test: does `resolved_in_clip` correlate with your "No" labels? |
| R7 | Existing clip tools use transcript, LLM, then multi-signal scoring with a human deciding; one gives a score without showing why | C | Every score must carry **evidence IDs and a reason** |
| R8 | A 17-model highlight test found no single best model | C | Test **two** models; keep the model swappable |
| R9 | In one study pairwise LLM preferences flipped about 13.6% of the time on identical reruns, with first-position bias | A | Run every pairwise comparison in **both orders**; disagreement = tie |
| R10 | Open-ended 1 to 10 scoring is unstable; anchored rubrics and forced formats help; pairwise is more consistent but O(N²) | A/C | Anchored 1 to 5 rubric (pointwise), pairwise only on the top ~12 |
| R11 | Judges show verbosity bias (longer wins) | C | Report the correlation between score and clip length and word count |
| R12 | Averaging over shuffled orders improves agreement with humans; only a few permutations are needed | A | Two shuffled pointwise runs |
| R13 | G-Eval: chain-of-thought plus form-filling improves judge agreement; probability weighting adds little and needs logprobs most chat APIs hide | A | Short reasoning field **before** scores; no logprob weighting; **pin** (model, rubric version, prompt hash) in every output row |
| R14 | Rubric judges rated AI-written fiction above published human fiction, a "predict the endings" tension metric reversed it | A | Our scripts are probably AI-generated, so the judge may over-rate them. Use **relative** ranking (pairwise) and report score compression. Optional experimental "forecast spread" signal. |
| R15 | LLMs detect coarse suspense (over 78% binary accuracy in one study) but fail to localise the key rising and falling moments | A | LLM chooses and scores; **code** snaps cut points; **you** check boundaries |
| R16 | Schema enforcement guarantees structure, not truth; validate outputs in code; enums remove invented categories | A/C | IDs not timestamps; pydantic validation; retry with the error message; never trust a model-written time |
| R17 | Free-tier limits: Groq's free 70B model is listed at 30 requests/min, 12k tokens/min, 1k requests/day (tokens per minute is the real limit); Cerebras about 1M free tokens/day; Gemini limits are per project, shown in AI Studio, and sources conflict (reports from about 20 to 1,000 requests/day) | A/C ⚠️ | Never plan around a fixed number. Rate limiter, backoff, **disk cache**, resumable runs |
| R18 | These providers expose OpenAI-compatible endpoints: `api.groq.com/openai/v1`, `api.cerebras.ai/v1`, `generativelanguage.googleapis.com/v1beta/openai`, `openrouter.ai/api/v1`. Cerebras rotates its model catalogue. | A/C ⚠️ | One OpenAI-compatible client; list models at runtime; model name lives in config |
| R19 | One roundup says free-tier Gemini traffic is subject to Google's data-usage policies | C ⚠️ | Privacy decision D2 (Section 12.1) before any script leaves your machine |
| R20 | A hand-labelled set of 20 to 50 items gives very wide intervals; tight kappa intervals need roughly 200 to 400 labels; eval items from one episode are clustered, not independent | A/C | Report **precision@k with Wilson intervals** and **bootstrap by episode**; call results indicative, not significant |
| R21 | Ad platforms reject sexual, suggestive, graphic-violence and shocking content; rules vary by region and change | B/C ⚠️ | An advisory `policy_risk` flag per promo (never a filter) |
| R22 | Kuku TV episodes run up to about 2 minutes, with 50+ episodes per series and cliffhanger endings (matches the data); the Kuku TV app listing cites 5,000+ shows and 150,000+ episodes | B ⚠️ | Scale target for the cost model |

### 3.3 What the research did not settle (so we test it ourselves)

1. Whether stitched promos beat continuous ones for this show (🔬 Hypothesis H3).
2. Whether the screenplay's timestamps match the produced video exactly. We cannot check. Assumption A1.
3. Whether LLM judges can find a "hook" from text alone as well as an editor watching the video. We measure agreement with **your** labels.
4. Real free-tier limits today. Check in each provider's console.
5. What a high-performing promo is in live metrics (watch-through, installs). Out of scope; described in Section 9.4 as how we'd know it worked with a real team.

### 3.4 Context: who uses this

Kuku TV is Kuku's vertical microdrama service (parent: Kuku Technologies). Episodes run up to about 2 minutes and end on cliffhangers. The company is scaling AI-led production, and the brief says new shows are released every week. The user of this tool is a **promo editor** who today watches every episode. The tool's job is to hand them a **ranked shortlist with exact cut points**, not to replace their judgment.

---

## 4. Assumptions register

The brief says: make assumptions, write them down, keep going. Each assumption has a way to change it.

| ID | Assumption | Why | If wrong |
|---|---|---|---|
| A1 | The screenplay timestamps match the produced episode video closely (within about 0.5 s) | They are the only timing we have | Offsets would shift every cut. Add a per-show `time_offset` in config. Cannot be verified here. |
| A2 | Timestamps are episode-relative (each episode starts at 00:00.00) | ✅ Verified in all 50 files | n/a |
| A3 | "20 to 60 seconds" applies to the **sum of segment durations** (not elapsed time) and is inclusive | The brief defines a promo by its length on screen | One config line (`min_len`, `max_len`, `len_mode`) |
| A4 | Segments stay in chronological order (within an episode) and ascending by episode across episodes. No reordering ("cold open" tricks). | Brief says "in order" and "no editing" | Optional experimental flag `allow_reorder` (off) |
| A5 | A good promo must **not resolve its own cliffhanger** | Brief: "cuts at an unresolved moment" | Judged by the LLM (`resolved_in_clip`) and checked by you |
| A6 | "Makes sense on its own" is tested by a **cold-viewer** call that sees only the clip (no series knowledge) | Best available proxy for "someone who has never seen the show" | Replace with human panel at scale |
| A7 | Audience: English-speaking US viewers on Instagram, TikTok, YouTube Shorts | Stated in the brief | Other markets need localised rubrics |
| A8 | No audio or video is available, so hook strength is inferred from the script | Input pack is text only | Stated as a limit; multimodal check is future work |
| A9 | Output size: about 30 ranked promos for a 50-episode show, in three tiers (A post first, B maybe, C reserve) | Brief gives no count. 30 is about 0.6 promos per episode. | `final_n` in config |
| A10 | A cut may sit only where no spoken line or sound cue is in progress (HC4) | Cutting mid-sentence would look broken | Config `cut_margin_sec` |
| A11 | English only | Pack is English; multilingual scaling is discussed, not built | Section 9 |
| A12 | The human editor makes the final call; the tool proposes | Matches the brief's framing | n/a |
| A13 | Spoiler risk can only be estimated from the 50 episodes we have, not the rest of the show | Pack is the first 50 episodes | Flagged as `spoiler_risk`, advisory |
| A14 | Free-tier models are good enough to *rank*, not to be the final authority | Free tiers only | Optional stronger model in the interview (swappable) |

---

## 5. Architecture

### 5.1 Pipeline

```
  episodes (.txt)
        │
  [1] PARSE            plain code → blocks with IDs, times, kinds, speakers, intensity
        │
  [2] NORMALISE        speaker aliases, audio cues, first-appearance index
        │
  ┌─────┼───────────────────────┬───────────────────────────┐
  │     │                       │                           │
 [3a] WINDOWS          [3b] LLM PROPOSER            [3c] STITCHED
 rule-built             1 call per episode:          hook + recap + cliff,
 continuous clips       model picks block IDs        plus a few cross-episode
 (20-60 s)              for up to 3 spans            joins (capped)
  │                       │                           │
  └─────────────┬─────────┴───────────────────────────┘
                │
  [4] SNAP + VALIDATE   IDs → times, snap cuts to silence, enforce HC1-HC6
                │
  [5] DEDUPE            non-max suppression (time overlap), keep best per region
                │
  [6] RULE SCORE        cheap structural signals → shortlist (K≈150) + baselines
                │
  [7] LLM POINTWISE     anchored rubric, 2 shuffled runs + cold-viewer call
                │
  [8] LLM PAIRWISE      top ~12, both orders, ties on disagreement
                │
  [9] SELECT            diversity rule, tiers A/B/C, "post first" reasons
                │
  [10] VALIDATE + EVALUATE   hard checks; your blind labels; ablations; stability
                │
  promos.json · promos.csv · ranked_promos.md · eval/ · WORKLOG.md
```

### 5.2 Why three candidate sources

| Source | Strength | Weakness | What we learn by comparing |
|---|---|---|---|
| Rule windows (3a) | Deterministic, exhaustive, free | Cannot judge meaning | Recall ceiling |
| LLM proposer (3b) | Understands story; cheap because the show is small | Can pick weak boundaries or hallucinate IDs | Does the model find moments the rules miss? |
| Stitched (3c) | Matches the "conflict, recap, cliffhanger" ad shape and can skip filler | Combinatorial; recap beats are hard to choose | Do stitched promos beat continuous ones? (H3) |

The final list records which source each promo came from. That is evidence for the doc.

### 5.3 Data contracts (what each file holds)

**Block** (one line of the screenplay's timeline)
```json
{"id":"E07-L012","episode":7,"scene":2,"kind":"speech|audio_cue|camera|action",
 "speaker":"JULIANA","speaker_raw":"LADY JULIANA","emotion_raw":"Desperate, Unbelieving",
 "intensity":"high|medium|low|none","start":13.50,"end":14.30,"text":"..."}
```

**Candidate**
```json
{"cand_id":"C-000123","source":"window|proposer|stitched",
 "segments":[{"episode":7,"start_id":"E07-L021","end_id":"E07-L058","start":41.2,"end":88.5}],
 "duration":47.3,"features":{...},"rule_score":0.0}
```

**Score record** (one per candidate per run)
```json
{"cand_id":"C-000123","judge":{"provider":"groq","model":"...","rubric":"v1","prompt_hash":"..."},
 "hook":{"score":4,"type":"confrontation","evidence_ids":["E07-L021"]},
 "cliffhanger":{"score":5,"type":"revelation","evidence_ids":["E07-L058"],"unanswered_question":"..."},
 "clarity":{"score":3,"confusions":["..."]},"intensity":4,
 "flags":{"resolved_in_clip":false,"needs_prior_context":true,"spoiler_risk":"low","policy_risk":"none"},
 "why_it_works":"..."}
```

**Final promo** (what the editor sees)
```json
{"rank":1,"tier":"A","promo_id":"P001","duration_sec":47.3,
 "segments":[{"episode":7,"start":"00:41.20","end":"01:28.50"}],
 "hook":{"text":"<paraphrase>","type":"...","at":"E07-L021"},
 "cliffhanger":{"text":"<paraphrase>","type":"...","at":"E07-L058"},
 "why_it_works":"...","post_first_reason":"...","source":"proposer",
 "scores":{...},"flags":{...}}
```

### 5.4 Repository layout

```
promo-finder/
├── README.md                 run steps (Colab and local)
├── WORKLOG.md                every wall, retry, wrong guess, fix
├── PROMO_FINDER_MASTER_PLAN.md   this file
├── config.yaml               model/provider, limits, weights, paths
├── .env.example              GROQ_API_KEY=  GEMINI_API_KEY=  etc. (never commit .env)
├── .gitignore                data/, .cache/, .env, outputs with verbatim script text
├── requirements.txt
├── run.py                    one command: parse → ... → outputs
├── src/
│   ├── parse.py              episodes → blocks
│   ├── normalise.py          aliases, audio cues, first-appearance index
│   ├── cuts.py               valid cut points, snapping, HC checks
│   ├── cand_windows.py       source 3a
│   ├── cand_proposer.py      source 3b (LLM)
│   ├── cand_stitched.py      source 3c
│   ├── dedupe.py             non-max suppression, diversity
│   ├── score_rules.py        structural signals, baselines
│   ├── llm_client.py         swappable client: cache, rate limit, retry, usage log
│   ├── score_pointwise.py    rubric + cold-viewer
│   ├── score_pairwise.py     both-order comparisons, tie logic, win rates
│   ├── select_final.py       tiers, diversity, post-first reasons
│   ├── validate.py           hard checks (fail loudly)
│   └── evaluate.py           golden-set metrics, ablations, stability, bias diagnostics
├── prompts/                  rubric_v1.md, proposer_v1.md, pairwise_v1.md, cold_v1.md
├── eval/                     golden_labels.csv, metrics.json, ablation.md, failure_log.md
├── outputs/                  untouched raw run outputs (run_<date>_<model>/)
├── notebooks/promo_finder.ipynb   Colab entry point
└── app.py                    optional viewer
```

### 5.5 Configuration (all knobs in one file; full draft in Appendix B)

Key settings: `provider`, `base_url`, `model`, `api_key_env`, `rpm`, `tpm`, `max_calls`, `min_len`, `max_len`, `target_len_prior`, `shortlist_k`, `pairwise_top`, `final_n`, `weights`, `cut_margin_sec`, `seed`, `rubric_version`.

### 5.6 The LLM client (the part that makes the model swappable)

| Feature | Behaviour |
|---|---|
| One interface | `complete(prompt, schema, temperature, seed) → validated object` |
| OpenAI-compatible adapter | Works for Groq, Cerebras, Gemini (compat layer), OpenRouter, and any URL the interviewers provide |
| Optional second adapter | Anthropic Messages API (the one external API my sandbox can reach) |
| JSON handling | Request JSON mode where supported; always validate with pydantic; on failure retry up to 2 times, feeding back the validation error; after that mark the item `failed` and fall back to its rule score. **Never crash a run.** |
| Cache | Key = hash(provider, model, rubric version, prompt text). Reruns cost nothing; interrupted runs resume. Cache is git-ignored (it contains script text). |
| Rate limiting | Token-bucket on requests and tokens per minute; exponential backoff with jitter on 429 and 5xx; honours `Retry-After` |
| Budget guard | `max_calls` per run; stop cleanly and report what remains |
| Model discovery | If the provider lists models (needed for Cerebras), call it at start; pick the configured model or the closest allowed fallback and log the choice |
| Usage log | `usage.csv`: calls, tokens in and out, latency, cache hits, per stage. This is the data for the cost model. |
| Stub model | Returns canned valid JSON so the whole pipeline can be tested with no key and no network |
| Pinning | Every output row stores `(provider, model, rubric_version, prompt_hash)` |

---

## 6. The step-by-step workflow

Each step has the same layout: **Goal · Inputs · Do · Produces · What we will find · Gate (pass criteria) · Walls and fallbacks · Your part**. Never skip a gate. When a gate fails, log it in `WORKLOG.md` (📝), fix, rerun.

**Step overview**

| # | Step | Mainly | Your time |
|---|---|---|---|
| 0 | Ground truth and decisions | 🛑 you | 45 min |
| 1 | Repo and plumbing | 🤖 | 0 |
| 2 | Parse and audit | 🤖 | 5 min |
| 3 | Normalise | 🤖 + 🛑 | 5 min |
| 4 | Candidate generation (rule windows, stitched) | 🤖 | 0 |
| 5 | Rule scoring, baselines, shortlist | 🤖 + 🛑 checkpoint 1 | 15 min |
| 6 | LLM proposer and union | 🤖 | 0 |
| 7 | LLM pointwise scoring and cold-viewer test | 🤖 + 🛑 pilot check | 10 min |
| 8 | LLM pairwise ranking and final selection | 🤖 | 0 |
| 9 | Validate and evaluate | 🤖 + 🛑 checkpoint 2 | 60 min |
| 10 | Failure analysis, ablations, model swap | 🤖 + 🛑 | 20 min |
| 11 | Raw outputs and prototype packaging | 🤖 + 🛑 test | 10 min |
| 12 | Solution doc and video | 🤖 draft + 🛑 you | 90 min |
| 13 | Publish and submit | 🛑 you | 30 min |

---

### Step 0. Ground truth and decisions 🛑

**Goal.** Replace my guesses about "what a good promo looks like" with real examples, and settle the decisions only you can make.

**Do (you).**
1. Watch **5 to 8 real promos** from ReelShort, DramaBox or similar (TikTok, YouTube Shorts, Instagram). If Kuku already runs promos for this show, watch those first.
2. For each, fill one row in `ground_truth_notes.md`:

| Field | Question |
|---|---|
| Length | How many seconds? |
| First 3 s | What is on screen and said? (slap? reveal? line? silent shot?) |
| Structure | Straight clip, or conflict then recap then cliffhanger? Number of cuts? |
| Ending | Where does it stop? What question is left open? |
| Standalone | Could you follow it with no context? What was confusing? |
| Source | Opening of an episode, middle, or the end? |

3. Answer the decisions D1 to D7 in Section 12.1.

**Produces.** `ground_truth_notes.md`, decisions D1 to D7.

**What we will find.** The real length range, how often recaps appear, and what hooks look like in practice. This **calibrates**: the `target_len_prior`, the rubric anchors, whether stitched candidates deserve more weight, and the hook enum.

**Gate.** At least 5 promos noted; D1 to D3 and D7 answered.

**Walls and fallbacks.** If you cannot find promos for this show, use any ReelShort or DramaBox promos for similar shows. If you cannot watch any, note this in the doc: the rubric then rests on Tier C sources only (Section 3.1), which weakens the claim that it matches what editors want.

---

### Step 1. Repo and plumbing 🤖

**Goal.** A repository that runs end to end on one episode with a stub model, before any real model is involved.

**Do.**
1. Create the layout in Section 5.4, `config.yaml`, `.env.example`, `.gitignore`, `requirements.txt`, `WORKLOG.md` with the entry template (Section 13).
2. Build `llm_client.py` (Section 5.6) including the stub model.
3. Add smoke tests: the stub returns canned JSON for each prompt type; the pipeline runs on episode 1 and writes outputs.
4. Dependencies are plain: `pydantic`, `pyyaml`, `pandas`, `numpy`, `scipy`, `tenacity` (or hand-written backoff), `openai` (used only as an HTTP client for compatible endpoints), `streamlit` (optional).

**Produces.** A runnable skeleton; `tests/` passing.

**What we will find.** Bugs in plumbing while it is cheap to fix them.

**Gate.** `python run.py --episodes 1 --model stub` completes and writes a valid (fake-scored) `promos.json`.

**Walls and fallbacks.** Library versions or sandbox install issues: pin versions, log the fix (📝).

**Your part.** Nothing.

---

### Step 2. Parse and audit 🤖

**Goal.** Turn 50 files into one clean table of blocks, and **prove** the parser is right by reproducing the numbers in Section 2.

**Do.**
1. Parse headers (episode number, logline, continuity) and scenes. Parse each block with the strict pattern from trap T8. Assign IDs `E{ep:02d}-L{n:03d}` in time order (ties: camera, action, speech).
2. Cut-point map: compute the set of times where **no speech or audio cue is in progress** (with `cut_margin_sec`). These are the only valid clip starts and ends (HC4).
3. Write `reports/parse_report.md`: counts per episode; anomalies (end before start, missing fields, header mismatch); token estimate per episode; distribution of block kinds.
4. **Regression test against Section 2.2**: the parser must give exactly 50 episodes, 100 scenes, 3,727 blocks (CAMERA 1,754, ACTION 372, speech and audio 1,601), 6,163 s total runtime. If any number differs, find out why before moving on.

**Produces.** `parsed/blocks.jsonl`, `parsed/episodes.json`, `reports/parse_report.md`, `tests/test_parse.py`.

**What we will find.** Whether the format is as clean as it looks (so far: zero anomalies), and the real token counts that drive the cost model.

**Gate.** All 50 parsed; zero silent skips; the regression numbers match.

**Walls and fallbacks.** A mismatch usually means a parsing bug (for example splitting on colons). Fix, log what went wrong (📝). If a new show breaks the format, the report names the file and line and the parser's strictness level can be relaxed per `config.yaml`.

**Your part.** 🛑 Skim `parse_report.md` (5 min) and confirm nothing looks off.

---

### Step 3. Normalise 🤖 + 🛑

**Goal.** Make speakers, sounds and emotions comparable.

**Do.**
1. **Speaker aliases.** Auto-suggest merges (strip `LADY`, `LORD`, `DUKE` prefixes; same surname; one label a prefix of another). Produce `alias_map.csv` with proposed merges.
2. **Audio cues.** Reclassify `SOUND FX` blocks as `audio_cue`. Exclude them from spoken-line counts. Keep them as features (a sting in the first 3 s or last 5 s).
3. **Emotion intensity.** Map the 661 raw tags to `high`, `medium`, `low` by keyword stems (for example *scream, shout, fury, panic, desperate* high; *cold, firm, defiant, mocking* medium; *soft, gentle, quiet, whisper* low). Unknown tags default to medium.
4. **First appearance index.** For each normalised speaker, record the first episode and time they speak. Used later to flag clips that feature characters introduced elsewhere.
5. **Episode continuity link.** Compare the last scene heading of episode N with the first of N+1 (same location → "continuous"). Used for cross-episode joins.

**Produces.** `parsed/alias_map.csv`, `parsed/characters.json`, `parsed/emotion_map.csv`, updated `blocks.jsonl`.

**What we will find.** How many of the 65 labels collapse into real characters, and how many are one-off descriptive labels (11 appear once).

**Gate.** Alias map covers every label; intensity assigned to every block that has an emotion tag.

**Walls and fallbacks.** Over-merging (two different characters sharing a title). Never merge automatically beyond the safe prefix rule: the final map is **confirmed by you**.

**Your part.** 🛑 Review `alias_map.csv` (about 10 to 15 rows to confirm). Each correction is credited in the log.

---

### Step 4. Candidate generation: rule windows and stitched 🤖

**Goal.** A large, valid pool of candidate clips from sources 3a and 3c. (Source 3b, the LLM proposer, is Step 6.)

**Do.**
1. **Rule windows (3a).** For each episode, for every valid cut start, every valid cut end such that 20 s ≤ duration ≤ 60 s. If a window ends at an episode end, extend to the end of the final block so the closing visual beat is included (finding F3). Starting points are limited to a speech, audio cue or ACTION block start, so the clip opens on an event.
2. **Stitched (3c).** Build up to 3-segment candidates inside one episode: *hook segment* (3 to 12 s, a high-intensity opening unit) + optional *bridge* (5 to 15 s, a context beat) + *cliffhanger segment* (5 to 20 s, the episode ending or a high-intensity peak). Chronological order only (A4). Total must satisfy HC1.
3. **Cross-episode joins (small, capped).** Tail of episode N + head of episode N+1 **only if** the two are marked "continuous" (Step 3) and the join does not resolve the cliffhanger. Cap at 15% of candidates.
4. **Baselines** (created now, scored later): `random` (random valid windows) and `last45` (the final 45 s of each episode).
5. Run validators HC1 to HC5 on every candidate. Drop and count failures.

**Produces.** `candidates/windows.jsonl`, `candidates/stitched.jsonl`, `candidates/baselines.jsonl`, `reports/candidate_report.md`.

**What we will find.** Candidate counts per source and per episode. In my exploration, start-at-spoken-line to end-at-spoken-line windows already give about **11,000** 20 to 60 s windows, and about **4,600** when restricted to crude "strong" ends. Expect this step to produce thousands before de-duplication, which is why Steps 5 and 6 exist.

**Gate.** 100% of kept candidates pass HC1 to HC5; at least 5 candidates exist for every episode.

**Walls and fallbacks.** Explosion in count: raise the minimum spacing between starts (for example 3 s) before rule scoring. Too few stitched candidates: relax bridge length. Log the counts (📝).

**Your part.** Nothing.

---

### Step 5. Rule scoring, baselines and shortlist 🤖 + 🛑 Checkpoint 1

**Goal.** A cheap, explainable score that picks a shortlist of about 150 candidates for the LLM, and gives the "rules only" system for the ablation.

**Do.**
1. **Hook features (first ~3 s of the clip):** speech or audio cue within 3 s; first line short (at most 8 words) and high intensity; question or accusation marks (second-person address, imperative, `?`); a non-establishing opening (shot-type words such as *wide*, *establishing*, *tracking* lower the score; *close-up*, *extreme close-up* raise it); an ACTION event in the first 3 s.
2. **Cliffhanger features (last ~5 s):** the clip ends at an episode end (strong position prior, finding R3); ends on an interrupted line (dash or ellipsis) or an unanswered question; ends on a reaction close-up or an audio sting; high-intensity last line; reveal vocabulary (*truth, secret, alive, dead, betray…*, low weight and configurable).
3. **Negative features:** calm last line (low intensity); resolution words; very low speech density; long exposition in the first 8 s.
4. **Clarity proxy:** number of distinct named speakers (fewer is better); characters whose first appearance is **not** inside the clip (penalty).
5. **Length prior:** soft preference for 35 to 60 s (adjust after Step 0).
6. Combine with weights in `config.yaml` into `rule_score`. Keep every feature value in the output for explainability.
7. **Shortlist.** De-duplicate with non-max suppression (same episode, time overlap above 60% → keep the higher score). Then take the top K=150 **stratified**: at most 6 per episode and at least 1 for every episode that has any valid candidate. Add the baselines to the scoring pool for fair comparison later.
8. **Bias check.** Report the share of shortlisted clips that end at an episode end. If it is above 70%, the "position prior" dominates: widen stratification.

**Produces.** `scores/rules.jsonl`, `candidates/shortlist.jsonl`, `reports/rules_report.md` (feature distributions, top 10 with explanations).

**What we will find.** Whether structural rules alone recover obvious moments, and how strongly end-of-episode clips dominate (they will, by construction).

**Gate.** Every shortlisted clip has a feature-level explanation; the shortlist covers at least 40 of 50 episodes.

**Walls and fallbacks.** Rules too generous in one place: tune the single weight, log the change (📝). Do **not** tune to make this show look good at the expense of generality; keep show-specific vocabulary in config only.

**Your part.** 🛑 **Checkpoint 1.** I show you 10 clips (5 top-rated, 5 low-rated) with feature explanations. For each wrong call, tell me *why* in one sentence. Each reason becomes a rule change, credited to you in the log. About 15 minutes.

---

### Step 6. LLM proposer and union 🤖

**Goal.** Let a model read each episode and propose the best spans, then merge with the rule candidates.

**Do.**
1. For each episode, send one call: a compact view of the episode (lines such as `E07-L012 00:11.3 MATRIARCH (Cold): "..."`, plus ACTION and CAMERA lines, logline and continuity notes) and ask for **up to 3** promo spans, each as `start_id`, `end_id` (plus optional second and third segment), `hook_id`, `hook_type`, `cliff_id`, `cliff_type`, and a 30-word reason. Enums only; model may not output times. For cross-episode context include the logline and continuity notes of the previous two episodes only.
2. Code converts IDs to times, snaps to valid cuts, checks HC1 to HC5, and extends end-of-episode spans to the final beat. Anything invalid is **counted** (hallucination rate) and dropped, never silently repaired beyond snapping.
3. **Union** with the rule shortlist. Match overlapping clips (time overlap above 50%) and mark them `found_by: [rules, proposer]`. The remaining unique proposals join the pool.
4. Cost: 50 calls at roughly 2.5k tokens in and 0.6k out each, about 130k tokens in total.

**Produces.** `candidates/proposer.jsonl`, `candidates/pool.jsonl` (union), `reports/proposer_report.md`.

**What we will find.**
- **Agreement:** how many proposals match rule-shortlist clips (high agreement = rules and model see the same moments).
- **Recall gaps:** moments the model finds that rules never ranked (the value of the LLM).
- **Hallucination rate:** share of proposed IDs that don't exist or violate hard rules.
- Whether the model favours episode starts or ends (position bias).

**Gate.** At least 40 of 50 episodes return a valid proposal; invalid ID rate is reported (not hidden).

**Walls and fallbacks.** Rate limits: the cache and resume let you continue. Model returns prose instead of JSON: validation error is fed back, two retries, then the episode is skipped and logged. A weak model proposing the same span for every episode: lower temperature variance, add "different moment from the first/last 20 seconds" instruction, log the fix.

**Your part.** Nothing, unless the proposer fails to run (see the network note in Section 12.1, D1).

---

### Step 7. LLM pointwise scoring and cold-viewer test 🤖 + 🛑 pilot check

**Goal.** Score the shortlisted pool on the anchored rubric (Section 7), and test "makes sense on its own".

**Do.**
1. **Pilot first.** Run 10 clips only. I show you the raw JSON, token usage and score spread before the full run. This protects free-tier quota if the rubric or prompt is wrong.
2. **Full pointwise run.** One candidate per call (no batching, so one clip cannot bias another). Fixed system prompt `rubric_v1`, temperature 0, **two runs with shuffled candidate order** (R12). Output must follow the JSON schema in Section 7.3 (short reasoning *before* scores, evidence IDs required).
3. **Cold-viewer call.** A separate call that sees **only the clip text** (no logline, no series bible, no episode number) and returns: a two-sentence summary, the main conflict, the unresolved question, and a list of confusions. A clip passes the clarity gate if `confusions ≤ 1` and an unresolved question is stated.
4. **Aggregate.** Per clip: mean of the two runs for each rubric dimension; disagreement (absolute difference between runs) is kept as an uncertainty signal.
5. **Gates applied here:** hook ≥ 3, cliffhanger ≥ 3, cold-viewer pass, `resolved_in_clip = false`. Clips failing a gate stay in the data but cannot reach tier A.
6. **Diagnostics.** Score histogram (is everything 4 or 5?), rank correlation between runs, correlation of score with clip length and word count (verbosity bias, R11), correlation between rule score and LLM score.

**Produces.** `scores/pointwise_run1.jsonl`, `scores/pointwise_run2.jsonl`, `scores/cold_viewer.jsonl`, `reports/pointwise_report.md`, `usage.csv` rows.

**What we will find.**
- **Score compression.** Likely most clips score 3 to 5 (judges are generous, and AI-written scripts may be over-rated, R14). If so, the ranking relies on relative comparison in Step 8.
- Which hook and cliffhanger types dominate.
- How stable the model is across the two shuffled runs.
- Whether longer clips score higher regardless of quality.

**Gate.** At least 95% of calls return valid JSON (after retries); run-to-run rank correlation reported; no evidence ID that is not in the clip (code check, invalid ones counted).

**Walls and fallbacks.**

| Wall | Fallback |
|---|---|
| Everything scored 4 to 5 | Tighten anchors; add a forced-distribution instruction ("at most 2 of 10 can be 5"); rely on pairwise |
| Invalid JSON | Feed the error back, retry twice, then fall back to rule score for that clip, logged |
| Rate limits (429) | Backoff, resume from cache; switch provider via config |
| Model invents evidence IDs | Code rejects them; count and report |
| Hit daily quota | Reduce `shortlist_k` (150 → 100) or run across two days or two providers |

**Your part.** 🛑 Look at the 10-clip pilot output and say whether the reasoning makes sense (10 minutes).

---

### Step 8. LLM pairwise ranking and final selection 🤖

**Goal.** A robust relative ranking of the best clips, and the final tiered list.

**Do.**
1. Take the top **12** by pointwise mean (after gates). Build all 66 pairs. For each pair call the judge **twice** with the order swapped (132 calls). Outcome per pair: win for A, win for B, or **tie** (if the two orders disagree, or either says tie).
2. Rank by win rate (tie = 0.5); break ties by the pointwise mean. If time allows, fit Bradley-Terry scores for a smoother ordering.
3. **Final score** for the top 12 = 0.5 × normalised pairwise win rate + 0.5 × normalised pointwise mean. Others (rank 13+) use pointwise mean only.
4. **Diversity selection** to build the final list of `final_n` (default 30): at most 2 per episode, no overlap above 30% with a higher-ranked promo (HC6), and a soft penalty when the same hook or cliffhanger type has already been used three times in a row.
5. **Tiers.** A = top 10 that pass all gates; B = next 10; C = remaining reserves.
6. **"Post first" reasons.** For the top 5, one line each explaining why it should go out first (standalone clarity, early episode so new viewers need no context, distinct hook type, low spoiler and policy risk). The order of posting prefers clips that are clear alone and avoid spoilers, even over a slightly higher raw score.
7. Add the `policy_risk` flag (advisory) and `spoiler_risk` (low / high) to each promo.

**Produces.** `scores/pairwise.jsonl`, `scores/final_ranking.csv`, `outputs/<run>/promos.json`, `promos.csv`, `ranked_promos.md`, `reports/pairwise_report.md`.

**What we will find.**
- **Order-flip rate.** The literature reports about 13.6% of pairs flipping (R9). If ours is far higher, the judge is weak for this task.
- **Position bias.** Share of "A wins" over all pairs; near 50% is healthy.
- Whether pairwise reorders the top 12 relative to pointwise (the value of Step 8).
- Which candidate source (windows, proposer, stitched) produced the winners.

**Gate.** Each of the final promos passes HC1 to HC6; the ranked list has at least 10 tier A entries, or the report says why not.

**Walls and fallbacks.** Too many ties: lower pairwise pool to the top 10; still report tie rate. Quota too low for 132 calls: run the top 8 (56 calls).

**Your part.** Nothing.

---

### Step 9. Validate and evaluate 🤖 + 🛑 Checkpoint 2

**Goal.** Know how good the output really is, against **your** judgment and honest baselines.

**Do.**
1. **Hard validation (code).** Every final promo: durations in range, timestamps exist, segments in order, cuts not inside speech, no duplicates. Report counts; target is **0 violations**.
2. **Build the blind golden set** (24 clips; 15 in MVP): 8 from the final top 12, 6 from mid-ranked clips, 4 random valid windows, 3 `last45` baseline clips, 3 rule-only top picks. Shuffle. Hide scores, source and rank. Present each as text with timestamps.
3. 🛑 **You label each clip** `Post / Maybe / No`, plus three optional ticks: *strong hook / real cliffhanger / clear alone*.
4. **Re-label 6 clips later** (after a break) to measure your own consistency (intra-rater agreement).
5. Run `evaluate.py` (metrics in Section 8): P@5 and P@10 (strict and lenient) with Wilson intervals, rank correlation with your labels, bootstrap by episode, stability across two full runs, bias diagnostics, ablation table.
6. **Read the bottom** too: show you the 5 lowest-scored clips that you labelled *Post* (misses) and the 5 highest-scored that you labelled *No* (false alarms).

**Produces.** `eval/golden_labels.csv`, `eval/metrics.json`, `eval/ablation.md`, `eval/stability.md`, `eval/bias.md`.

**What we will find.** The numbers the doc needs: how many of the tool's top picks you would post, whether the full system beats `last45` and random, what each layer adds, and where the judge and you disagree.

**Gate.** 0 hard-validation violations; labels complete; every metric reported with an interval or a plain note that the sample is too small for one.

**Walls and fallbacks.** If the tool does **not** beat `last45`, say so. That is a finding, not a failure of honesty. Diagnose (probably the position prior dominates), log it, and report it in the doc.

**Your part.** 🛑 **Checkpoint 2:** label 24 clips (about 45 minutes), re-label 6, confirm the misses and false alarms.

---

### Step 10. Failure analysis, ablations and model swap 🤖 + 🛑

**Goal.** Explain *why* it fails, and show the model is truly swappable.

**Do.**
1. **Failure taxonomy.** Tag every miss and false alarm with one cause (Section 10.2). Count them and attach one concrete example each (timestamps, not script text, if the doc will be public).
2. **Hypotheses H1 to H8** (Section 10.1): test each with the data we already have; report supported, not supported, or inconclusive.
3. **Sensitivity.** Perturb the scoring weights ±20%; report how much the top 10 changes (Kendall tau). A ranking that collapses under small weight changes is fragile.
4. **Model swap.** Rerun Steps 6 to 8 with a second model (a different provider or size). Report top-10 overlap with the first run, and how both compare to your labels. This proves the swappable design and shows whether the conclusions depend on one model.
5. **Optional experimental signal (🔬, only if time allows): forecast spread.** For the top 12, sample 5 short continuations from the clip alone (temperature 1.0) and have the judge count distinct outcomes. A true cliffhanger should spread (many outcomes); a resolved clip should converge. Inspired by the "predict the endings" tension metric (R14). Report its correlation with your labels. If it does not help, say so and drop it.

**Produces.** `eval/failure_log.md`, `eval/hypotheses.md`, `eval/sensitivity.md`, `eval/model_swap.md`.

**What we will find.** The honest "where it picks badly" section: probably clips that depend on earlier episodes, clips whose cliffhanger is weak but ends an episode, and clips where the hook is visual and the screenplay under-describes it.

**Gate.** At least 5 concrete, confirmed failures; every hypothesis has a verdict.

**Walls and fallbacks.** Second provider quota too tight: run the second model on the proposer and pointwise stages for the top 40 only, and say so.

**Your part.** 🛑 Confirm each failure in your own words (20 minutes).

---

### Step 11. Raw outputs and prototype packaging 🤖 + 🛑

**Goal.** Something Kuku can rerun on a new show in the interview.

**Do.**
1. **Raw outputs.** One folder per run, `outputs/run_<date>_<model>/`, containing exactly what the pipeline wrote: `promos.json`, `promos.csv`, `ranked_promos.md`, all intermediate files, `usage.csv`, and `MANIFEST.md` with file hashes and the config used. **Nothing hand-edited.**
2. **One command:** `python run.py --input <folder_or_zip> --provider groq --model <name> --out outputs/<name>`. Useful flags: `--episodes 1-10`, `--model stub`, `--no-cache`, `--resume`, `--dry-run`.
3. **Colab notebook** (`notebooks/promo_finder.ipynb`): installs requirements, asks for a key via Colab secrets, mounts or uploads the input zip, runs `run.py`, shows the ranked promos. This is the **primary prototype link** because it is free and rerunnable.
4. **README.md**: five-minute quickstart for Colab and local; how to swap the model; how to read the outputs; known limits.
5. **Optional viewer** (`app.py`, Streamlit): browse by episode, read each clip's text with timestamps, filter by tier. Only if the core is done.
6. **New-input rehearsal.** Run on a different input (for example, only 10 episodes, or a hand-modified copy) to check the "run on a new input" requirement. Fix whatever breaks.
7. Confirm `.gitignore` excludes the scripts, `.cache/` and `.env`.

**Produces.** The repo, the notebook, the raw output folder.

**What we will find.** Hidden assumptions that only break on new input (hard-coded paths, show-specific words, format surprises).

**Gate.** A fresh Colab session runs the notebook start to finish on 10 episodes with your own key.

**Walls and fallbacks.** Colab session limits: the cache lets a run resume. No Colab: local run steps in the README.

**Your part.** 🛑 Run the Colab once yourself with your own key (10 minutes).

---

### Step 12. Solution doc and video 🤖 draft + 🛑 you

**Goal.** A 2-page PDF and a 3-minute video that are clearly **yours**.

**Do.**
1. I draft the doc from Section 14 using real numbers from `eval/`.
2. 🛑 You rewrite in your voice, keep only what you can explain without notes, and cut anything you do not understand. The interview is about your decisions.
3. 🤖 Export to PDF, verify **2 pages or fewer** (render and count).
4. 🛑 Record the video following Section 15 (screen recording, your own voice, up to 3 minutes).

**Produces.** `doc/solution.pdf`, the video link.

**Gate.** Doc is 2 pages; it names the AI tools used and one concrete AI mistake (Section 13); the numbers match `eval/metrics.json`.

**Your part.** 🛑 About 90 minutes.

---

### Step 13. Publish and submit 🛑

**Goal.** Everything opens for anyone with the link, before the deadline.

**Do (you).**
1. Push the code (via the GitHub connector if available, otherwise upload my zip through the GitHub web page). **I list every file before it goes up and check that no episode script is among them.**
2. Put raw outputs where D3 says (Section 12.1).
3. Open every link in an **incognito window**: repo, Colab, outputs, doc, video.
4. Submit the form: name, roll number, branch, problem chosen, links.
5. Do it **at least 2 hours before the deadline.**

**Gate.** All links verified from a logged-out browser; the form confirmation received.

---

## 7. Rubric and prompts

### 7.1 Principles

- **Generic, not show-specific.** No character names or plot in the prompts. The same prompts must work on next week's show.
- **Versioned.** Prompts live in `prompts/` with a version tag. Every output row stores `(provider, model, rubric_version, prompt_hash)` so a score can never be separated from the judge that gave it (R13).
- **Evidence or it doesn't count.** The model may only cite block IDs that appear in the clip. Code rejects anything else.
- **Reasoning before scores, kept short** (at most 60 words), for form-filling stability (R13). No logprob tricks.
- **Temperature 0** for scoring; higher only for the optional forecast samples.
- **One clip per call** for pointwise scoring (no cross-contamination); pairwise sees exactly two clips in randomised A/B order.
- **Never leak** scores, ranks, or the other judge's answer into a prompt.
- Anchor examples are **synthetic** (invented mini-scenes), never taken from the pack.

### 7.2 Rubric v1 (anchored 1 to 5)

| Dimension | 5 | 3 | 1 |
|---|---|---|---|
| **Hook** (first ~3 s of the clip) | A concrete, high-stakes event or line in the first 3 s (confrontation, reveal, threat, humiliation, impossible situation) that raises a question and needs no context | Interesting premise, but it takes 5+ s to land or relies on knowing the characters | Establishing shot, small talk, or no conflict in the first 3 s |
| **Cliffhanger** (last ~5 s) | Ends mid-crisis on a specific unanswered question with high stakes; the viewer can name what they want to find out | Unresolved but low stakes or predictable | Fully resolved, or ends on filler |
| **Clarity** (stands alone) | A stranger understands who is in conflict and why within ~10 s | Gist clear, relationships fuzzy | Impossible to follow without earlier episodes |
| **Intensity** (overall) | Sustained emotional or dramatic pressure | Moderate | Flat |

Anchors for 2 and 4 are interpolated in the prompt. Flags: `resolved_in_clip`, `needs_prior_context`, `spoiler_risk` (none/low/high), `policy_risk` (none/low/medium/high, advisory only).

**Weights (config, default):** hook 0.35 · cliffhanger 0.35 · clarity 0.20 · intensity 0.10. Gates: hook ≥ 3, cliffhanger ≥ 3, cold-viewer pass, not resolved.

**Hook and cliffhanger vocabularies (enums):**

- `hook_type`: status_reversal, impossible_situation, hidden_identity, ticking_clock, shocking_revelation, public_humiliation, confrontation, betrayal, other. *(`public_humiliation` and `confrontation` are my additions based on how these dramas are built; flagged as such in the doc.)*
- `cliff_type`: danger, revelation, decision, mystery, betrayal, ticking_clock, unresolved_confrontation, none.

### 7.3 Pointwise output schema

```json
{
  "reasoning": "<= 60 words",
  "hook": {"score": 1, "type": "enum", "evidence_ids": ["E07-L021"]},
  "cliffhanger": {"score": 1, "type": "enum", "evidence_ids": ["E07-L058"],
                  "unanswered_question": "<= 20 words"},
  "clarity": {"score": 1, "confusions": ["short phrases"]},
  "intensity": 1,
  "flags": {"resolved_in_clip": false, "needs_prior_context": false,
            "spoiler_risk": "none", "policy_risk": "none"},
  "why_it_works": "<= 25 words"
}
```

### 7.4 Prompt skeletons

**Proposer (per episode)**
```
SYSTEM: You are a promo editor for vertical microdramas. You pick moments from a
screenplay to use as 20-60 second social promos. A good promo opens on a hook within
3 seconds, ends unresolved on a cliffhanger, and makes sense to someone who has never
seen the show. You may ONLY reference block IDs that appear in the script below. Do not
output times. Return JSON only, matching the schema.

USER: [episode logline + continuity notes (this episode and the previous two)]
      [numbered blocks: E07-L001 00:00.0 CAMERA: ... / E07-L002 00:01.0 ACTION: ...
       / E07-L003 00:11.3 MATRIARCH (Cold): "..." ]
      Propose up to 3 promos. Each: segments[{start_id,end_id}] (max 3), hook_id,
      hook_type (enum), cliff_id, cliff_type (enum), reason (<=30 words). Prefer
      different moments. Say "none" if no moment qualifies.
```

**Pointwise (per clip)**
```
SYSTEM: You grade candidate promos for vertical microdramas using the rubric below.
[rubric v1 with anchors] Judge only the clip text. Cite only block IDs shown.
Do not assume knowledge of the series. Be strict: a 5 should be rare. Return JSON only.
USER: [duration] [numbered blocks of the clip]
```

**Cold-viewer (per clip, separate call, clip text only)**
```
SYSTEM: You have never seen this show. Read the clip and answer honestly.
Return JSON: {summary (2 sentences), main_conflict, unresolved_question or null,
confusions[] (things you could not understand), would_keep_watching (true/false)}.
```

**Pairwise (per pair, twice with A/B swapped)**
```
SYSTEM: Two candidate promos, A and B. Which would stop a scrolling viewer in the
first 3 seconds AND make them want the next episode? Judge hook, cliffhanger and clarity.
Do not prefer a clip because it is longer or listed first. Return JSON:
{"winner":"A"|"B"|"tie","reason":"<=25 words"}
```

### 7.5 What each prompt is *not* allowed to do

| Prompt | Forbidden |
|---|---|
| All | Output a timestamp; cite an ID not in the input; use outside knowledge of the show |
| Proposer | Return more than 3 promos or any segment beyond 3 |
| Pointwise | Give a 5 without evidence IDs |
| Cold-viewer | See the logline, series bible, or episode number |
| Pairwise | See scores or ranks |

---

## 8. Evaluation design

### 8.1 Systems compared (the ablation ladder)

| System | What it is | Why it is in the table |
|---|---|---|
| S0 `random` | Random valid windows | Floor |
| S1 `last45` | Final 45 s of each episode | The dumb-but-strong baseline (every episode ends on a built-in cliffhanger) |
| S2 `rules` | Rule score only | Value of structure without AI |
| S3 `proposer` | LLM-proposed spans only | Value of the LLM reading the story |
| S4 `pointwise` | Rule shortlist + proposer union, pointwise rubric | Value of scoring |
| S5 `full` | S4 + cold-viewer gate + pairwise + diversity | The submitted system |
| S6 `full-model2` | S5 with a second model | Robustness to model swap |

The doc reports one table: for each system, P@5, P@10 (strict and lenient) with intervals. If S5 does not beat S1, we say so.

### 8.2 Golden set protocol

| Item | Rule |
|---|---|
| Size | **24 clips** (15 in the MVP path) |
| Composition | 8 from the final top 12 · 6 mid-ranked · 4 random valid windows · 3 `last45` clips · 3 rule-only top picks |
| Blindness | Shuffled; no scores, rank, source or tier shown; clip text plus timestamps only |
| Labels | `Post` / `Maybe` / `No`; optional ticks: strong hook, real cliffhanger, clear alone |
| Consistency check | You re-label 6 clips after a break; report your agreement with yourself |
| Rater | Single rater (you). Stated as a limit. A second rater for 10 clips is a bonus. |

### 8.3 Metrics

| Metric | Definition | Note |
|---|---|---|
| P@k strict | Share of the system's top k clips you labelled `Post` | k = 5 and 10 |
| P@k lenient | Share labelled `Post` or `Maybe` | |
| Interval | Wilson 95% interval on each proportion | Honest with tiny samples |
| Rank agreement | Spearman between system score and your ordinal label (No 0, Maybe 1, Post 2) on the golden set | Bootstrap **by episode** (clips from one episode are not independent, R20) |
| Hard-check violations | Count of HC1 to HC6 failures in the final list | Target 0 |
| JSON failure rate | Share of calls needing a retry; share that failed | Reliability |
| Hallucinated IDs | Share of proposer or evidence IDs that don't exist | Reported, not hidden |
| Stability | Overlap (Jaccard) of top 10 across two full runs; pairwise order-flip rate | Compare to the ~13.6% literature figure |
| Position bias | Share of pairwise "A wins" | Healthy ≈ 50% |
| Length bias | Spearman(score, duration) and (score, word count) | |
| Score compression | Share of scores ≥ 4; compare with your `Post` rate | H8 |
| Source mix | Share of final top 12 from windows / proposer / stitched | Which source earns its place |
| Sensitivity | Kendall tau of the top 10 when weights change ±20% | Fragility |
| Cold-viewer agreement | Agreement between the cold-viewer pass and your "clear alone" tick | Is the proxy any good? |

### 8.4 What the statistics can and cannot say

- 24 labels cannot establish a precise kappa (published guidance suggests hundreds of labels for a tight interval). So we report **proportions with Wilson intervals and a plain note** that results are indicative.
- Do not claim significance. Claim direction, with caveats.
- A judge that agrees well with a single human is still agreeing with **one person's taste**. State it.

### 8.5 Qualitative checks that matter more than the numbers

1. You read the top 10 end to end and mark where the tool misread the story.
2. You read 5 misses and 5 false alarms.
3. I spot-check 10 judge rationales against the script for invented events.
4. Cut boundaries are inspected on 5 clips (are they sensible, not just valid?).
5. At least one case where the **rules** got it right and the LLM got it wrong, and one the other way round, with timestamps.

---

## 9. Scale and cost

### 9.1 Per-show token and call estimate (⚠️ to be replaced with measured values from `usage.csv`)

| Stage | Calls | Tokens in (each) | Tokens out (each) | Total in | Total out |
|---|---|---|---|---|---|
| 6 Proposer | 50 | 2.7k | 0.6k | 135k | 30k |
| 7 Pointwise (150 clips × 2 runs) | 300 | 1.8k | 0.3k | 540k | 90k |
| 7 Cold-viewer | 150 | 0.9k | 0.25k | 135k | 37k |
| 8 Pairwise (66 pairs × 2 orders) | 132 | 2.2k | 0.1k | 290k | 13k |
| 10 Forecast (optional) | 72 | 0.9k | 0.15k | 65k | 11k |
| **Total** | **≈ 700** | | | **≈ 1.17M** | **≈ 0.18M** |

### 9.2 Cost (illustrative only)

Using one source's July 2026 pay-as-you-go example of about $0.30 per million input tokens and $2.50 per million output tokens for a Flash-class model (⚠️ pricing is unsettled and sources conflict; plug in your provider's current price in `cost_model.py`): about **$0.35 + $0.45 ≈ $0.80 per 50-episode show**, roughly half with a batch discount (one source cites 50%). Order of magnitude: **under a dollar per show**.

### 9.3 Fit to the free tier

- About 700 calls fits a 1,000 requests/day limit (if that limit still holds for your provider ⚠️). Tokens per minute is the tighter constraint: about 1.35M total tokens at 12k per minute is roughly **110 minutes** of background running.
- The cache makes the run **resumable** across days or providers. A crashed or throttled run loses nothing.
- Reduce load in order: drop the forecast stage → shortlist 100 instead of 150 → one pointwise run instead of two → pairwise top 8.

### 9.4 Scaling to every show

| Concern | Design |
|---|---|
| Volume | Kuku TV's app listing cites 5,000+ shows and 150,000+ episodes (⚠️ marketing figure), and new shows launch weekly. Each show is an independent, idempotent job (cache-keyed), so a queue plus parallel workers scales linearly. |
| Cost growth | Proposer and pointwise scale with episodes; pairwise cost is **constant** (top 12 only). The shortlist funnel keeps expensive calls few. |
| Rough total | Under a dollar per 50-episode show means a few thousand dollars for thousands of shows, tiny next to editor time (⚠️ illustrative; the real figure comes from `usage.csv`). |
| Throughput | Batch APIs for non-urgent shows; rate-limit aware workers; stronger models only on the top 12. |
| Human in the loop | Editor reviews a ranked list of about 10 to 15 clips with exact cuts (about 10 to 15 minutes) instead of watching about 100 minutes of video per 50 episodes (⚠️ estimate, to be validated). Accept, reject and boundary edits are logged as labels. |
| Drift | Keep one frozen "regression show" and its golden labels. Rerun it whenever the model or prompt changes; alert if P@10 or stability drops. |
| Feedback loop | Each week's editor decisions become new labelled data, used to adjust weights and anchor examples, with versioned rubrics. |
| Languages | Kuku produces in many languages. The structure (blocks, IDs, cut logic) is language-agnostic; the rubric can stay English while the model reads the source language, but quality in other languages must be spot-checked with native speakers. Not built here. |
| Format drift | Parser fails loudly and reports line numbers; a per-show override file adapts regex without code changes. |
| New models | Config line plus rerun of the regression show. |

### 9.5 How we'd know it worked with a real editorial team

| Signal | Target to agree with the team | How measured |
|---|---|---|
| Acceptance rate | Share of tier A promos the editor posts without changes | Editor decisions logged |
| Boundary edit distance | Average seconds the editor moves start and end | Compare tool cuts with the published cut |
| Time saved | Editor minutes per show, before vs after | Time sheets or tool timers |
| Recall | Did the editor's own favourite appear in the top 15? | Ask after the first few shows |
| Live performance | Watch-through, 3-second hold, installs per promo; does tool rank correlate with real performance? | Platform analytics, after a few weeks |
| Stability | Same show, rerun, similar list | Jaccard on top 10 |
| Trust | Editors stop re-watching everything | Qualitative feedback |

---

## 10. Hypotheses, failure modes and risks

### 10.1 Pre-registered hypotheses (tested in Step 10)

| ID | Hypothesis | How we test it |
|---|---|---|
| H1 | The end-of-episode position prior dominates the final list | Share of final top 12 ending at an episode end vs share in the pool; compare with your labels |
| H2 | Early episodes give clearer standalone clips than later ones (also check by the upload-batch ID ranges, finding F12) | Cold-viewer pass rate and clarity by episode bucket |
| H3 | Stitched promos win on hook, lose on clarity | Scores and your labels by candidate source |
| H4 | Longer clips score higher regardless of quality | Spearman(score, duration) |
| H5 | The LLM adds more to **cliffhanger** detection than to **hook** detection | Ablation by dimension |
| H6 | Visual-only openings (17 episodes) are under-scored by dialogue-centric rules | Hook scores for those episodes vs the rest |
| H7 | Pairwise materially reorders the top 5 compared with pointwise | Kendall tau |
| H8 | The judge inflates scores (AI-written scripts, R14) | Share of scores ≥ 4 vs your `Post` rate |

### 10.2 Failure taxonomy (every miss or false alarm gets exactly one tag)

| ID | Failure | Example symptom |
|---|---|---|
| FT1 | Needs prior context | Cold-viewer lists 2+ confusions; characters unintroduced |
| FT2 | Slow open | Nothing happens in the first 3 s |
| FT3 | Cliffhanger already resolved inside the clip | `resolved_in_clip` true but missed |
| FT4 | Ends an episode but nothing is at stake | Position prior fooled the judge |
| FT5 | Valid but ugly cut | Starts or ends mid-thought though HC4 passes |
| FT6 | Near-duplicate of a higher-ranked promo | Same moment, shifted by a few seconds |
| FT7 | Spoils a major twist | `spoiler_risk` high |
| FT8 | Hook is visual and under-described in the script | Screenplay text is bland but the shot would hold viewers |
| FT9 | Over-reliance on emotion tags | "Screaming" tag on a bland line |
| FT10 | Policy-risky content ranked high | Sexual, suggestive or graphic content |
| FT11 | Judge hallucination | Reasoning cites events not in the clip |

### 10.3 Risk register

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| X1 | I can't reach the LLM provider from my sandbox (network allowlist) | High unless you allow the domain | High | D1 options: allow domain; or hybrid with you running scoring in Colab; or rules-only fallback |
| X2 | Free-tier quota too low | Medium | Medium | Cache, resume, reduce `shortlist_k`, two providers |
| X3 | Judge inflates scores and ranks poorly | High | Medium | Anchors, forced distribution, pairwise, `last45` comparison, honest reporting |
| X4 | Tool fails to beat `last45` | Medium | Medium (but honest) | Report it; diagnose position prior |
| X5 | Timestamps don't match the real video | Unknown | High in production | Assumption A1; per-show offset; verify with an editor |
| X6 | Scripts leak via a public repo or cache | Low if careful | **Severe** | `.gitignore`, file listing before every push, outputs on an unlisted link (Section 11) |
| X7 | Time overrun | High (plan is larger than 2 to 3 hours) | High | MVP path (Section 12.3) with explicit cut lines |
| X8 | Doc not in your own words | Medium | High (interview) | You rewrite and own every sentence |
| X9 | Overfitting rules to this show | Medium | Medium | Structural rules; show-specific words only in config; new-input rehearsal in Step 11 |
| X10 | A new input breaks the parser in the interview | Medium | High | Loud errors with line numbers; rehearsal on modified input |

### 10.4 Honest limits to state in the doc

1. Text only: no acting, music, pacing or on-screen text.
2. Timestamps assumed to match the video.
3. One human rater and about two dozen labels: indicative, not statistically conclusive.
4. Judge models are free-tier and may over-rate AI-written scripts.
5. Hook and cliffhanger heuristics come from practitioner sources (Tier C), checked only against your judgment.
6. Spoiler risk can only be judged within the 50 episodes we have.

---

## 11. Privacy, confidentiality, security and policy

| Topic | Decision |
|---|---|
| The brief | You may use the pack with AI tools; you **must not publish or share it** |
| Where scripts go | Only to the LLM provider you choose (D2). ⚠️ One roundup says free-tier traffic may fall under the provider's data-use policies, which can include model improvement. Read the terms of your provider before sending anything. If unsure, run rules-only, or use a provider whose terms exclude training. |
| What we commit to GitHub | Code, prompts, config, README, WORKLOG (without script text). **Never** the scripts, `.cache/`, `.env`, or outputs containing verbatim dialogue. |
| Raw outputs | They hold clip text. Recommended: host the outputs folder on an **unlisted link** (for example Drive "anyone with the link") instead of a public repo. Outputs in the repo should contain IDs, timestamps and **paraphrased** hooks only. Decision D3. |
| This plan file | Contains a few character names, counts and the show title. Fine to keep private. Remove or generalise them before putting this file in a public repo. |
| Pre-push check | `git ls-files` must show no `episode-*.txt`; grep for long verbatim lines in committed files; I list every file before you push. |
| Keys | In `.env` or Colab secrets only; never in notebooks, logs or screenshots; use a throwaway free key; revoke it after the build. |
| Doc and video | Describe clips by timestamp and paraphrase; do not scroll through full scripts on screen. |
| Ad policy | Meta and TikTok reject sexual, suggestive, graphic or shocking creative, and rules vary by region and change (⚠️ secondary sources). `policy_risk` is an **advisory** flag; the editor checks the current platform policy before posting. |
| AI disclosure | The doc names the tools used and one real AI mistake (Section 13). |

---

## 12. Your decisions, checklist and timeline

### 12.1 Decisions to make before Step 1 🛑

| ID | Decision | Options | My recommendation |
|---|---|---|---|
| D1 | **How the LLM stages get run.** My sandbox can reach only a short allowlist (Anthropic's API, GitHub, package registries). Groq, Gemini, Cerebras and OpenRouter are **not** on it. | (1) You allow the provider's API domain in your Claude network settings, and share a throwaway free key so I run it here. (2) Hybrid: I build and test everything except the live LLM calls (stub model), and **you run Steps 6 to 8 in the Colab notebook** with your own key. (3) Rules-only. | Option 1 if the setting is available (cleanest raw outputs); otherwise option 2. Option 3 only as a last-resort fallback. Domains: `api.groq.com`, `generativelanguage.googleapis.com`, `api.cerebras.ai`, `openrouter.ai` (⚠️ confirm in the provider docs). |
| D2 | **Privacy.** Are you comfortable sending the scripts to a free-tier API? Read the provider's data terms first. | Yes / No | If No: option 3 (rules-only), or a provider whose terms exclude training. |
| D3 | **Where raw outputs live** | Public repo / unlisted Drive link / private | Unlisted Drive link ("anyone with the link"); the public repo has code only |
| D4 | **How many promos to list** | 20 / 30 / 40 | 30 (tiers A 10, B 10, C 10) |
| D5 | **Path** | MVP (about 3.5 to 4 h of your time) / Full (about 5 h) | MVP first; add Full items if time remains |
| D6 | **GitHub** | Connector (if you find one in your connector settings; my directory search did not surface one) / manual upload of my zip | Whichever works; manual upload is fine |
| D7 | **Your deadline** | Exact date and time | Needed to set the T-minus schedule below |

### 12.2 Master checklist of everything that needs **you**

| When | Action | Time |
|---|---|---|
| Step 0 | Watch 5 to 8 real promos and fill the notes sheet | 45 min |
| Step 0 | Answer D1 to D7; create a free API key; check your provider's limits and data terms | 20 min |
| Step 2 | Skim the parse report | 5 min |
| Step 3 | Confirm the alias map (about 10 to 15 rows) | 5 min |
| Step 5 | **Checkpoint 1**: judge 10 clips, give one-line reasons | 15 min |
| Step 7 | Look at the 10-clip pilot output | 10 min |
| Step 9 | **Checkpoint 2**: label 24 clips (15 in MVP), re-label 6 | 45 to 60 min |
| Step 10 | Confirm each failure in your own words | 20 min |
| Step 11 | Run the Colab once with your key | 10 min |
| Step 12 | Rewrite the doc in your voice; record the 3-minute video | 90 min |
| Step 13 | Push, open all links in incognito, submit | 30 min |
| **Total (Full)** | | **about 5 hours** |
| **Total (MVP)** | | **about 3.5 to 4 hours** |

### 12.3 MVP path vs Full path (cut lines)

| Item | MVP | Full |
|---|---|---|
| Parse, normalise, rule windows, baselines, rule scoring | ✅ | ✅ |
| LLM proposer (Step 6) | ✅ | ✅ |
| Stitched and cross-episode candidates | ❌ (drop) | ✅ |
| Pointwise scoring | 1 run | 2 shuffled runs |
| Cold-viewer test | ✅ | ✅ |
| Pairwise | top 8 (56 calls) | top 12 (132 calls) |
| Golden set | 15 clips, no re-label | 24 clips + 6 re-labels |
| Ablation table | S0, S1, S2, S5 | S0 to S6 |
| Second model (swap proof) | 1 small run if quota allows | full rerun |
| Forecast-spread experiment | ❌ | optional |
| Sensitivity analysis | ❌ | ✅ |
| Viewer app | ❌ | optional |
| Colab notebook, README, raw outputs, doc, video | ✅ | ✅ |

**Cut order if time runs out:** viewer app → forecast → sensitivity → second rater → stitched → second pointwise run → second model → pairwise top 12 down to 8.

**Ultra-lean version (closest to the brief's 2 to 3 hours):** golden set of 10 clips, Step 0 with 3 promos, 60-second video, doc written from the template in Section 14. State plainly in the doc that the evaluation is small.

### 12.4 Timeline relative to your deadline (T)

| When | Goal |
|---|---|
| T − 44 h to T − 36 h | Step 0 done, decisions made, keys ready; Steps 1 to 3 built |
| T − 36 h to T − 26 h | Steps 4 to 6 (checkpoint 1); proposer run |
| T − 26 h to T − 18 h | Steps 7 to 8 (pilot, then full run) |
| T − 18 h to T − 10 h | Step 9 (labels), Step 10 (failures) |
| T − 10 h to T − 6 h | Step 11 (outputs, Colab rehearsal) |
| T − 6 h to T − 3 h | Step 12 (doc and video) |
| **T − 3 h** | Step 13 starts; submit by **T − 2 h** at the latest |

Free-tier background runs (about 2 hours of wall clock) should start early, not at the end.

---

## 13. WORKLOG protocol and pre-logged entries

### 13.1 What goes in `WORKLOG.md`

Every time something goes wrong, changes direction, or is retried a different way. Also every place you or I disagree with the AI.

```
### W-0xx · <step> · <date and time>
- What I tried:
- What went wrong (symptom, evidence):
- Why (root cause, if known):
- What I did instead:
- Result:
- Counts as: [AI mistake | data surprise | tool or limit wall | my decision | retry]
- Used in the doc? [Y/N]
```

### 13.2 Entries already earned in this chat

| ID | Step | What happened | Counts as |
|---|---|---|---|
| W-001 | Research | A fetch of the NativeX page returned no usable content; I relied on search excerpts for the ad-structure claim | Tool wall (low impact) |
| W-002 | Research | Gemini free-tier limits conflict across sources (from about 20 to 1,000 requests/day); decided not to hard-code a number | Data conflict |
| W-003 | Plan v1/v2 | I planned to seed and snap candidates at **scene** boundaries. The data has 100 scenes in 50 episodes (25 single-scene episodes). Replaced with block-level cut points. | **AI assumption wrong** |
| W-004 | Plan v2 | I implied cliffhangers could be spotted by a trailing question or interruption. Only **9 of 50** final lines end in `?` or `!`; 41 end in a full stop. Cliffhanger detection became semantic plus positional. | **AI assumption wrong** |
| W-005 | Data exploration | My first keyword counter used substring matching: "ring" returned 361 blocks (the real count is **35**), "stab" and others were inflated the same way. Caught by a sanity check; fixed with word boundaries. | **AI code bug** |
| W-006 | Plan v2 | I expected a violence word list (slap, strike) to help the hook rules. `slap` appears in **one** block. Rules moved to structural signals. | **AI assumption wrong** |
| W-007 | Setup | My sandbox's network allowlist excludes the free LLM providers; two connector-directory searches did not surface a GitHub connector. Decision D1 and D6 created. | Tool and limit wall |

**For the doc's required "one place the AI got it wrong":** W-004 is the most meaningful (it changed the design), W-005 is the most concrete (a real bug with before/after numbers: 361 vs 35). Add any others you notice yourself during the build; your own catches carry more weight than mine.

### 13.3 AI tools disclosure (fill in at the end)

| Tool | Used for |
|---|---|
| Claude (chat, with web search and code execution) | Planning, research, data exploration, code, drafting |
| Scoring model(s) (provider and model name, TBD) | Proposer, pointwise, cold-viewer, pairwise |
| Libraries | pydantic, pandas, numpy, scipy, pyyaml (and any others added) |

---

## 14. Solution doc blueprint (PDF, 2 pages max)

| Section | Budget | Content |
|---|---|---|
| Header | 40 words | Problem 1, name, links |
| 1. Why this problem and how I scoped it | 100 | Input pack fits; output is checkable; one-sentence success definition |
| 2. Assumptions | 90 | The 5 that matter most (A1, A3, A4, A5, A8) |
| 3. How it works | 200 | One small diagram: parse → three candidate sources → filter → rubric scoring → pairwise → final. Name the "IDs not timestamps" decision. |
| 4. What AI does, what code does, where the human stays | 120 | A 3-column table |
| 5. Results | 150 | Ablation table (S0 to S5): P@5, P@10 with intervals; one sentence on whether we beat `last45` |
| 6. Where it fails | 180 | Five confirmed failures with timestamps and the taxonomy tag; one case where rules beat the LLM and one the reverse |
| 7. Scale and cost | 120 | Tokens and calls per show, cost per show, human review time, what changes for thousands of shows |
| 8. Tools used and one AI mistake | 80 | W-004 or W-005 with numbers |
| 9. Limits and next steps | 60 | Text-only, timestamp assumption, one rater, next: multimodal check and editor feedback loop |

~1,100 words plus 2 small tables fits two pages. **Every number comes from `eval/` and `usage.csv`.** If a number is not measured, the doc says so.

---

## 15. Walkthrough video script (3 minutes)

| Time | Show | Say |
|---|---|---|
| 0:00 to 0:20 | Title and the ranked output | "Editors watch every episode to pick promos. This reads the screenplays and hands them a ranked shortlist with exact cuts." |
| 0:20 to 0:50 | The parse report or one slide | One surprising data fact: "Only 9 of 50 episodes end on a question; the real cliffhanger is a final visual beat 5 seconds after the last line. So I cut on blocks, not punctuation or scenes." |
| 0:50 to 1:40 | Run it live (10 episodes) | Command, progress, the three candidate sources, the final table: hook, cliffhanger, why it works |
| 1:40 to 2:15 | Eval table, one failure | "Against my blind labels: [numbers]. It beats or doesn't beat the last-45-seconds baseline. Here's a clip it gets wrong and why." |
| 2:15 to 2:40 | `config.yaml` | Change one line (model), rerun a few episodes, show the same format |
| 2:40 to 3:00 | Limits | "Text only; one rater; what I'd test next with an editor." |

Do not scroll through full scripts on screen (confidentiality).

---

## 16. Submission checklist

| Item | Check |
|---|---|
| Form fields | Name · roll number · branch · "Problem 1" · all links |
| Solution doc | PDF, ≤ 2 pages, opens logged-out |
| Prototype link | Colab notebook (primary) and repo; the Colab runs from a fresh session |
| Raw outputs | Unedited folder from the full 50-episode run; `MANIFEST.md` present; link opens logged-out |
| Walkthrough video | ≤ 3 min, your voice, unlisted link opens |
| Confidentiality | No episode scripts in the repo; `git ls-files` checked; keys not committed |
| AI disclosure | Tools named; one real mistake explained |
| Timing | Submitted at least 2 hours before the deadline; confirmation saved |

---

## 17. Interview readiness (be able to answer these without notes)

| Question | Short answer |
|---|---|
| Why not just take the last 45 seconds of every episode? | That is **baseline S1**, and I measured the full system against it. (State the actual result.) Episodes end on built-in cliffhangers, so it is strong; the tool must add something beyond position. |
| Why block IDs instead of letting the model write timestamps? | Models invent plausible times. With IDs, a hallucinated time cannot exist; code maps IDs to real timestamps and rejects bad IDs. |
| Why three candidate sources? | Rules give an exhaustive recall ceiling; the LLM understands story; stitching matches the real ad shape and skips filler. Comparing them shows which earns its place. |
| Why pairwise only on 12 clips? | Pairwise is more consistent but costs N². Pointwise narrows; pairwise orders the finalists. Cost stays constant per show. |
| How do you handle judge bias? | Both orders (disagreement = tie), shuffled runs, anchored rubric, evidence IDs, length-bias check, and your own labels as ground truth. |
| What if the model changes? | One config line; the regression show and its labels tell us whether quality moved. |
| How does it scale to every show? | Independent idempotent jobs, funnelled cost, batch APIs, constant pairwise cost; human reviews 10 to 15 clips per show instead of watching everything. |
| How would you know it works with a real team? | Acceptance rate, boundary edit distance, time saved, recall of the editor's favourites, live watch-through; Section 9.5. |
| Where does it fail? | The taxonomy in Section 10.2, with the counts and examples from my run. |
| What would you do with a stronger model? | Swap it in config; compare against the first model on the same golden set; use it only for the proposer and pairwise stages to save cost. |
| What did the AI get wrong while you built this? | W-004 and W-005 (Section 13.2). |
| What is your biggest limitation? | Script-only judgment and a single rater; I'd validate against video and an editor panel next. |

---

## 18. What happens next

1. You answer **D1, D2, D3, D7** (and D4 to D6 if you have a view), and do the Step 0 viewing.
2. Say **"start"**. I begin Step 1 and Step 2, and report back with the parse report that reproduces the numbers in Section 2.
3. I stop at every 🛑 and tell you exactly what I need.

---

# Appendices

## Appendix A. Sources

⚠️ **Most sources were read as search excerpts, not as full pages.** Verify any claim before quoting it in the doc. Tier: A = papers and official docs, B = business press, C = vendor and practitioner blogs (hypotheses only).

| Topic | Source | Tier | Used for |
|---|---|---|---|
| Ad structure | https://nativex.com/en/blog/short-drama-primer | C | R1: conflict, recap, cliffhanger |
| Ad durations | https://www.admapix.com/blog/ad-intelligence/dramabox-ad-strategy-2026 | C | R2: lengths of top ads (snapshot) |
| Format conventions | https://www.tovima.com/culture/the-rise-of-micro-dramas/ | B | R3: hook mandatory, episode ends on a question |
| Hook formulas | https://genra.ai/blog/ai-short-drama-script-formula-hooks-cliffhangers | C | R4 |
| Cliffhanger types | https://quillbot.com/blog/creative-writing/cliffhanger/ · https://blog.chapter.pub/how-to-write-a-cliffhanger/ | C | R5 |
| Unresolved consequence | https://dev.to/cartney/how-to-write-cliffhangers-for-short-drama-that-hook-viewers-2jb8 | C | R6 (anecdotal) |
| Clip-finding tools | https://autoclip.dev/blog/how-ai-detects-viral-moments · https://chatcut.io/blog/turn-long-videos-into-shorts | C | R7 |
| Model comparison for highlights | https://contenthub.meetyoo.com/resources/best-ai-video-highlights | C | R8 |
| Judge flip rate and position bias | https://arxiv.org/pdf/2606.13685 · https://arxiv.org/abs/2602.02219v1 | A | R9, R12 |
| Pairwise vs pointwise, biases | https://www.zeroentropy.dev/concepts/llm-as-judge/ · https://memx.app/blog/llm-as-a-judge-biases-and-fixes/ | C | R10, R11 |
| Permutation averaging | https://aclanthology.org/2026.findings-emnlp.1444/ | A | R12 |
| G-Eval | https://arxiv.org/abs/2303.16634 · https://futureagi.com/blog/g-eval-definitive-guide-2026/ · https://www.cekura.ai/discover/g-eval | A / C | R13 |
| Suspense modelling | https://arxiv.org/pdf/2004.14905 (ACL 2020) | A | Background: suspense as uncertainty about what happens next |
| LLM suspense detection | https://arxiv.org/pdf/2508.15794v1 (COLM 2025) | A | R15 |
| Narrative tension metric | https://arxiv.org/abs/2604.09854 | A | R14, optional forecast signal |
| Structured output | https://www.gmicloud.ai/en/blog/structured-output-for-llm-inference-json-schema-enforcement-constrained-decoding-and-parse-failure-rates · https://tianpan.co/blog/2026-03-03-structured-generation-reliable-llm-output | C | R16 |
| Free-tier limits ⚠️ | https://eesel.ai/blog/groq-pricing · https://www.gmicloud.ai/en/blog/best-gpu-cloud-free-trials-for-llm-inference-in-2026 · https://www.rapidevelopers.com/md/ai-api-limits-performance-matrix/gemini-1-5-flash · https://yingtu.ai/en/blog/google-gemini-api-free-tier-limits-2026 · https://openrouter.ai/blog/tutorials/free-llm-apis-compared/ | C | R17 (conflicting; verify in provider consoles) |
| Free-tier data terms ⚠️ | https://toolhalla.ai/blog/best-free-ai-apis-2026 | C | R19 |
| OpenAI-compatible base URLs | https://github.com/elliotboney/shelldon/wiki/Configuration · https://docs.rs/crate/heartbit-core/latest/source/src/llm/registry.rs · https://docs.rs/crate/tinyagents/latest/source/providers.env.example | C | R18 (third-party code listings; confirm in provider docs) |
| Eval set size, kappa, intervals | https://dev.to/maya_andersson_dev/your-llm-as-judge-eval-set-is-too-small-here-is-the-math-2iac · https://arxiv.org/pdf/2609.35815 · https://mlflow.org/articles/llm-judge-calibration/ | A / C | R20 |
| Ad platform policy | https://ads.tiktok.com/help/article/ad-policy-handbook-metap?lang=en · https://transparency.meta.com/policies/ad-standards/ · https://xmp.mobvista.com/en-blog/docs/Avoiding-Policy-Violations-in-Short-Drama-Ads-How-to-Keep-Your-Creatives-Compliant | official / C | R21 |
| Kuku context | https://www.afaqs.com/news/ott-streaming/kuku-fm-launches-vertical-microdrama-ott-platform-kuku-tv-8718086 · https://apps.apple.com/IN/app/id6737497276 · https://www.business-standard.com/companies/quarterly-results/kuku-revenue-jumps-sixfold-to-1-484-crore-as-ai-fuels-microdrama-expansion-126100300968_1.html | B | R22, Section 3.4 |

---

## Appendix B. `config.yaml` draft

```yaml
run:
  seed: 7
  input: data/                 # folder or zip of episode-NNN-*.txt
  out: outputs/
  rubric_version: v1

llm:
  provider: groq               # groq | gemini | cerebras | openrouter | custom | stub
  base_url: https://api.groq.com/openai/v1
  model: "<confirm current model name in provider console>"
  api_key_env: GROQ_API_KEY
  temperature: 0
  json_mode: true
  rpm: 25                      # stay below the provider limit
  tpm: 10000
  max_calls: 900
  retries: 2
  list_models_at_start: true   # needed for providers that rotate catalogues

cuts:
  min_len: 20
  max_len: 60
  len_mode: sum_of_segments
  target_len_prior: [35, 60]
  cut_margin_sec: 0.15
  snap_tolerance_sec: 1.5
  end_tail_max_sec: 8
  max_segments: 3
  time_offset_sec: 0           # assumption A1 escape hatch

candidates:
  min_start_spacing_sec: 2.0
  stitched: {hook_len: [3, 12], bridge_len: [5, 15], cliff_len: [5, 20]}
  cross_episode_cap: 0.15
  baselines: {random: 40, last45: true}

shortlist:
  k: 150
  max_per_episode: 6
  nms_overlap: 0.6

scoring:
  weights: {hook: 0.35, cliffhanger: 0.35, clarity: 0.20, intensity: 0.10}
  gates: {hook_min: 3, cliffhanger_min: 3, confusions_max: 1}
  pointwise_runs: 2
  shuffle: true

pairwise:
  top_n: 12
  both_orders: true

select:
  final_n: 30
  max_per_episode: 2
  max_overlap: 0.30
  tiers: {A: 10, B: 10}
  type_repeat_penalty_after: 3

rules:                         # structural signals; show-specific words go in overrides/
  weights: see Appendix D
  intensity_stems:
    high: [scream, shout, fury, furious, panic, desperat, horrif, rage, enrag]
    low:  [soft, gentle, quiet, whisper, calm, tender]
```

---

## Appendix C. Reference logic (pseudocode)

**Block ID and cut points**
```
blocks = sort by (start, kind_order[camera, action, speech])
id = f"E{ep:02d}-L{n:03d}"
speech_spans = [(b.start, b.end) for b in blocks if b.kind in (speech, audio_cue)]
valid_cut(t) = not any(s + margin < t < e - margin for (s, e) in speech_spans)
```

**IDs to times (proposer and evidence)**
```
start = block[start_id].start
end   = max(b.end for b in blocks if start_id <= b.id <= end_id)
if end >= ep_end - end_tail_max_sec: end = ep_end        # include the final visual beat
start = nearest valid cut <= start within snap_tolerance, else reject
end   = nearest valid cut >= end   within snap_tolerance, else reject
check HC1..HC5; count and report every rejection
```

**Rule windows**
```
for each episode:
  starts = [b.start for b in blocks if b.kind in (speech, audio_cue, action) and valid_cut(b.start)]
  ends   = sorted(set(b.end for b in blocks if valid_cut(b.end)) | {ep_end})
  for s in thinned(starts, min_start_spacing):
    for e in ends:
      if min_len <= e - s <= max_len: yield (s, e)
```

**Non-max suppression**
```
sort candidates by score descending
keep = []
for c in candidates:
    if all(overlap_fraction(c, k) <= thr for k in keep if k.episode == c.episode):
        keep.append(c)
```

**Pairwise aggregation**
```
for each pair (i, j):
    r1 = judge(A=i, B=j); r2 = judge(A=j, B=i)
    w1 = i if r1 == "A" else j if r1 == "B" else None
    w2 = j if r2 == "A" else i if r2 == "B" else None
    if w1 is not None and w1 == w2: wins[w1] += 1
    else: wins[i] += 0.5; wins[j] += 0.5          # order flip or tie
win_rate = wins / (n - 1)
# optional: Bradley-Terry via iterative MM updates for a smoother ordering
```

**Wilson interval (for P@k)**
```
p = successes / n;  z = 1.96
centre = (p + z²/(2n)) / (1 + z²/n)
half   = z * sqrt(p(1-p)/n + z²/(4n²)) / (1 + z²/n)
interval = [centre - half, centre + half]
```

**Bootstrap by episode (rank agreement)**
```
repeat 2000 times: resample episodes with replacement,
                   take all golden clips from those episodes,
                   compute Spearman; report the 2.5th and 97.5th percentiles
```

---

## Appendix D. Rule features (initial weights, tuned only through Checkpoint 1)

| Feature | Window | Effect | Initial weight |
|---|---|---|---|
| Speech or audio cue within first 3 s | first 3 s | + | 0.08 |
| ACTION event within first 3 s | first 3 s | + | 0.08 |
| First spoken line short (≤ 8 words) and high intensity | first 3 s | + | 0.10 |
| Non-establishing opening (close-up over wide or tracking) | first 3 s | + | 0.05 |
| Accusation, question or imperative in first line | first 3 s | + | 0.05 |
| Clip ends at episode end (includes the final beat) | end | + | 0.14 |
| Ends on an interrupted line or an unanswered question | last 5 s | + | 0.08 |
| Ends on a reaction close-up or audio sting | last 5 s | + | 0.06 |
| High-intensity last spoken line | last 5 s | + | 0.06 |
| Reveal vocabulary (configurable, low weight) | whole clip | + | 0.03 |
| Speech density (words per second) near the show median | whole clip | + | 0.05 |
| Few distinct named speakers (≤ 3) | whole clip | + | 0.05 |
| Characters first appearing **outside** the clip | whole clip | − | 0.06 |
| Calm, low-intensity last line | last 5 s | − | 0.08 |
| Exposition-heavy first 8 s (long lines, no conflict cues) | first 8 s | − | 0.06 |
| Length inside 35 to 60 s | whole clip | + | 0.07 |

Weights are a starting guess and will be reported as such. Show-specific vocabulary lives in `overrides/<show>.yaml`, never in code.

---

## Appendix E. Templates

**`ground_truth_notes.csv` header**
```
source_url_or_show,platform,length_sec,first_3s_description,structure(straight|recap|montage),
num_cuts,ending_description,standalone_clear(y/n),what_was_confusing,source_position(open|mid|end),notes
```

**`eval/golden_labels.csv` header**
```
clip_id,segments,duration,label(Post|Maybe|No),strong_hook(y/n),real_cliffhanger(y/n),
clear_alone(y/n),relabel_label,notes
```

**`eval/failure_log.md` row**
```
| clip_id | segments | failure tag (FT1..FT11) | what the tool said | what's actually wrong | judge/rules/proposer |
```

---

## Appendix F. Glossary

| Term | Meaning |
|---|---|
| Block | One timed line of the screenplay timeline: CAMERA, ACTION, speech or audio cue |
| Cut point | A time at which no speech or sound cue is in progress; the only legal place to start or end a clip |
| Candidate | A possible promo (one to three segments) before scoring |
| Source | Where a candidate came from: rule window, LLM proposer, or stitched |
| Pointwise | Score each clip alone against a rubric |
| Pairwise | Compare two clips directly |
| Bradley-Terry | A model that turns pairwise wins into a smooth ranking |
| NMS | Non-max suppression: keep the best of overlapping candidates |
| Cold-viewer test | A model sees only the clip and says what it understood |
| P@k | Precision at k: share of the top k that you would post |
| Wilson interval | A confidence interval for a proportion that behaves with tiny samples |
| Tier A / B / C | Post first / maybe / reserve |
| Position prior | The built-in tendency to favour clips that end at an episode end |

---

## Appendix G. Things I have not verified (be honest about these)

1. Whether the screenplay timestamps match the produced video (A1).
2. Current free-tier limits and model names for every provider (sources conflict).
3. Whether free-tier data terms permit sending confidential scripts (D2).
4. Whether a GitHub connector is available to you (my directory search found none).
5. Whether the hook and cliffhanger heuristics from practitioner blogs hold for Kuku's audience. We only test them against **your** judgment.
6. Real pricing for any model at the time of use.
7. The cost, call and time estimates in Section 9; they are planning figures until `usage.csv` replaces them.
8. Whether Kuku already has promos for this show (comparing with them would be a strong extra check).
