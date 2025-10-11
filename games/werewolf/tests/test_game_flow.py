import importlib.util
import pathlib

def load_app_module():
    base = pathlib.Path(__file__).resolve().parent.parent
    app_path = base / "backend" / "app.py"
    spec = importlib.util.spec_from_file_location("ww_app", str(app_path))
    ww = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ww)
    return ww

def test_room_flow():
    ww = load_app_module()
    rid = ww.create_room("AI_owner", max_players=6)
    assert rid is not None
    # join players AI_1..AI_5
    for i in range(1, 6):
        err = ww.join_room(rid, f"AI_{i}")
        assert err is None
    err = ww.start_room_game(rid)
    assert err is None
    # step until ended or timeout
    for _ in range(200):
        st = ww.get_room_state(rid)
        if st["state"] == "ended":
            break
        ww.rooms[rid]["game"].step()
    st = ww.get_room_state(rid)
    assert st["state"] == "ended"
    game = st["game"]
    assert game is not None
    assert "history" in game and len(game["history"]) > 0
    assert any(h.get("phase") == "end" for h in game["history"])

def test_join_full_room():
    ww = load_app_module()
    rid = ww.create_room("ownerX", max_players=3)
    assert rid is not None
    assert ww.join_room(rid, "p2") is None
    assert ww.join_room(rid, "p3") is None
    err = ww.join_room(rid, "p4")
    assert err == "room_full"