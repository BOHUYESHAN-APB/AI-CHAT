import time
import csv
import json
import pathlib
import importlib.util
from statistics import mean
import copy

BASE = pathlib.Path(__file__).resolve().parent.parent
APP_PATH = BASE / "backend" / "app.py"

def load_app():
    spec = importlib.util.spec_from_file_location("ww_app", str(APP_PATH))
    ww = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ww)
    return ww

def analyze_history(game):
    # game is dict from get_room_state(... )['game']
    history = game.get("history", [])
    latencies = []
    model_calls = 0
    for h in history:
        if h.get("phase") == "night":
            for a in h.get("actions", []):
                meta = a.get("meta") or {}
                if meta.get("latency") is not None:
                    latencies.append(meta.get("latency"))
                    model_calls += 1
        if h.get("phase") == "day":
            for v in h.get("votes_meta", []):
                if v.get("latency") is not None:
                    latencies.append(v.get("latency"))
                    model_calls += 1
            for t in h.get("talks", []):
                if t.get("latency") is not None:
                    latencies.append(t.get("latency"))
                    model_calls += 1
    avg_latency = mean(latencies) if latencies else 0
    return {"model_calls": model_calls, "avg_latency": avg_latency, "raw_latencies": latencies}

def run_games(num_games=10, players=None, out_csv=None, out_jsonl=None):
    ww = load_app()
    ai_client = getattr(ww, "ai_client", None)
    results = []
    jsonl_path = out_jsonl or (BASE / "eval_results.jsonl")
    csv_path = out_csv or (BASE / "eval_results.csv")
    # initialize jsonl file
    with open(jsonl_path, "w", encoding="utf-8") as jf:
        pass

    for i in range(num_games):
        room_owner = f"Eval_{i}_owner"
        rid = ww.create_room(room_owner, max_players=(len(players) if players else 6))
        # join players
        if players:
            for p in players:
                if p != room_owner:
                    ww.join_room(rid, p)
        else:
            # add default AI_1..AI_5
            for j in range(1, 6):
                ww.join_room(rid, f"AI_{j}")
        # start game
        ww.start_room_game(rid)
        # step until end with safety limit
        for _ in range(1000):
            st = ww.get_room_state(rid)
            if st["state"] == "ended":
                break
            ww.rooms[rid]["game"].step()
        st = ww.get_room_state(rid)
        game = st.get("game") or {}
        # determine winner & days
        winner = None
        days = game.get("day", 0)
        for h in reversed(game.get("history", [])):
            if h.get("phase") == "end":
                winner = h.get("winner")
                break
        stats = analyze_history(game)
        row = {
            "game_index": i,
            "room_id": rid,
            "winner": winner,
            "days": days,
            "model_calls": stats["model_calls"],
            "avg_latency_sec": round(stats["avg_latency"], 4),
            "timestamp": time.time()
        }
        results.append(row)

        # snapshot ai_client last actions and api_keys mapping if available
        client_snapshot = {}
        api_map = {}
        try:
            if ai_client:
                client_snapshot = copy.deepcopy(getattr(ai_client, "_LAST_ACTIONS", {}))
                api_map = copy.deepcopy(ai_client.load_api_keys() if hasattr(ai_client, "load_api_keys") else {})
        except Exception:
            client_snapshot = {}
            api_map = {}

        # write jsonl entry (one JSON object per line)
        entry = {
            "meta": row,
            "game": game,
            "ai_client_last_actions": client_snapshot,
            "api_keys_snapshot": api_map
        }
        with open(jsonl_path, "a", encoding="utf-8") as jf:
            jf.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # write CSV
    fieldnames = ["game_index", "room_id", "winner", "days", "model_calls", "avg_latency_sec", "timestamp"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r)
    print(f"Wrote {len(results)} results to {csv_path} and {jsonl_path}")
    return results

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--games", type=int, default=10)
    p.add_argument("--out", type=str, default=None)
    p.add_argument("--jsonl", type=str, default=None)
    args = p.parse_args()
    run_games(num_games=args.games, out_csv=args.out, out_jsonl=args.jsonl)