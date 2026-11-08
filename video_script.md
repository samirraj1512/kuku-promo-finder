# 3-minute walkthrough script (record in YOUR voice; screen = terminal + ranked_promos.md)

**0:00-0:20 Problem.** "I picked Problem 1, Find the Promos. An editor watches every episode to pick 20-60 s promos. I built a tool that reads the screenplays and proposes ranked promos with timestamps, hook, cliffhanger and why it works. It only sees the script, no audio or video."

**0:20-1:05 How it works (show the README pipeline or run.py).** "Code does the safe parts: parse 50 episodes into 3,727 timestamped blocks, build 11,452 candidates (sliding windows plus joined hook-and-ending clips), and enforce six hard rules such as no cut in the middle of a line. A cheap rule score narrows that to 64 clips. The AI only judges those 64 against an anchored 1-5 rubric: hook, cliffhanger, clarity, plus a stranger-can-follow test. The model never writes timestamps; it cites block IDs and code converts them."

**1:05-1:45 Run it (screen).** Type: `python run.py --input data/show1 --model stub --out outputs/demo` (rules-only, no key). Then open `outputs/final/ranked_promos.md`. Show promo 1 (episode 3: bride dragged from her wedding, stranger kneels, 'accept my hand'): point at the hook line, the cliffhanger line, the segments. "The model is one config line, so a stronger model can be swapped in."

**1:45-2:30 Quality and failures.** "I compared against the last 45 seconds of each episode and random windows on a 12-clip sheet. My top 5 got 5 of 5 POST; the baseline got 0 of 4. But I have to be honest: Claude labelled that sheet and also judged the clips, so it is not independent, and 12 clips is tiny. Where it fails: the rules reward any clip ending at the episode end, even a cosy ending like episode 19; some clips end resolved; late-episode clips need earlier context and spoil twists."

**2:30-3:00 Limits and next step.** "In this build the judge was Claude in chat because my sandbox could not reach an LLM API, so the API path is tested with a stub only. I judged 36 of 64 shortlisted clips; pairwise ranking and an LLM proposer are not built. Next: a human editor labels the sheet, run the API judge in Colab, add pairwise comparison."
