from src.validate import check, overlap_frac, check_final
CFG = {"min_len": 20, "max_len": 60, "max_segments": 3, "cut_margin_sec": 0.15}
B = {1: [{"id": "E01-L001", "episode": 1, "kind": "speech", "start": 10.0, "end": 14.0, "text": "x", "speaker": "A", "intensity": "high"}]}
D = {1: 100.0}
def seg(s, e): return {"episode": 1, "start": s, "end": e}
def test_hc1_too_short(): assert "HC1" in check({"segments": [seg(0, 10)]}, B, D, CFG)
def test_hc1_too_long(): assert "HC1" in check({"segments": [seg(0, 70)]}, B, D, CFG)
def test_hc4_cut_inside_speech(): assert "HC4" in check({"segments": [seg(12, 40)]}, B, D, CFG)
def test_hc5_too_many_segments(): assert "HC5" in check({"segments": [seg(0, 5), seg(20, 25), seg(30, 35), seg(40, 45)]}, B, D, CFG)
def test_hc3_order(): assert "HC3" in check({"segments": [seg(30, 40), seg(0, 10), seg(50, 60)]}, B, D, CFG)
def test_hc2_beyond_episode(): assert "HC2" in check({"segments": [seg(90, 110)]}, B, D, CFG)
def test_valid(): assert check({"segments": [seg(15, 45)]}, B, D, CFG) == []
def test_hc6_overlap():
    a = {"cand_id": "a", "segments": [seg(0, 30)]}; b = {"cand_id": "b", "segments": [seg(10, 40)]}
    assert overlap_frac(a, b) > 0.3 and check_final([a, b])
