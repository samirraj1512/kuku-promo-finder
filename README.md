# Promo Finder (Kuku AI Generalist, Problem 1)
Reads a microdrama screenplay (timestamped blocks), finds 20-60 s promo candidates (continuous or up to 3 joined segments), ranks them, and explains hook / cliffhanger / why it works.

## Run (no key needed: stub model, rules-only floor)
    pip install -r requirements.txt
    # put the episode-NNN-*.txt files in data/show1/  (scripts are confidential: never commit them)
    python run.py --input data/show1 --model stub --out outputs/run1
    python -m pytest -q tests

## Run with a real LLM judge (model is a config line; any OpenAI-compatible endpoint)
    export GEMINI_API_KEY=...            # or GROQ_API_KEY etc, see .env.example
    python run.py --input data/show1 --judge api --provider gemini --model <model name from the provider console> --out outputs/run_gemini
Colab: `notebooks/promo_finder.ipynb` does the same (key from Colab secrets). NOTE: the API judge path is implemented and exercised with the stub only; the submitted ranking was judged by Claude in chat (human-in-loop file `scores/judgments_v1.json`, same schema) because the build sandbox had no route to any LLM API.

## Pipeline
parse (code) -> normalise aliases/intensity (code) -> candidates: sliding windows + within-episode stitched joins, cut only at valid cut points (code) -> hard checks HC1-HC6 (code) -> rule score + NMS shortlist of 64 (code) -> pointwise rubric + cold-viewer test (LLM) -> gates -> diversity (<=2 per episode, <=30% overlap) -> tiers A/B/C. The model never writes timestamps: it cites block IDs and code converts them.

## Not built / limits (see doc)
Script-only (no audio/video). Proposer (LLM picks moments) and pairwise stage not run. Cross-episode joins not built. 36 of 64 shortlisted clips were judged. Weights are a starting guess. Evaluation is a 12-clip blind set from one rater.
