import importlib.util, pathlib, time, json
base = pathlib.Path(__file__).resolve().parent.parent
app_path = base / "backend" / "app.py"
spec = importlib.util.spec_from_file_location("ww_app", str(app_path))
ww = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ww)

rid = ww.create_room("AI_owner", max_players=6)
for i in range(1,6):
    ww.join_room(rid, f"AI_{i}")
ww.start_room_game(rid)

print("Starting debug game:", rid)
for step in range(200):
    st = ww.get_room_state(rid)
    print(f"Step {step}: state={st['state']}, alive={st['game']['alive']}")
    if st["state"] == "ended":
        print("Game ended at step", step)
        print(json.dumps(st["game"], indent=2))
        break
    ww.rooms[rid]["game"].step()
else:
    print("Did not end within 200 steps. Final state:")
    st = ww.get_room_state(rid)
    print(json.dumps(st["game"], indent=2))