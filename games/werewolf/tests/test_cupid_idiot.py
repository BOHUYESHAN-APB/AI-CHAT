import importlib.util
import pathlib

def load_app_module():
    base = pathlib.Path(__file__).resolve().parent.parent
    app_path = base / "backend" / "app.py"
    spec = importlib.util.spec_from_file_location("ww_app", str(app_path))
    ww = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ww)
    return ww

def test_cupid_lovers_win():
    ww = load_app_module()
    rid = ww.create_room("owner", max_players=4)
    for i in range(1, 4):
        ww.join_room(rid, f"AI_{i}")
    # start game and force roles to include cupid and ensure lovers win scenario
    ww.start_room_game(rid)
    game = ww.rooms[rid]["game"]
    # set roles: Cupid, Werewolf, Villager, Villager
    players = list(game.players)
    if len(players) < 4:
        return
    game.set_player_role(players[0], "cupid")
    game.set_player_role(players[1], "werewolf")
    game.set_player_role(players[2], "villager")
    game.set_player_role(players[3], "villager")
    # link lovers manually
    if game.gs and hasattr(game.gs, "link_lovers"):
        game.gs.link_lovers(players[2], players[3])
    # kill the werewolf(s) to let lovers be last two
    game._mark_dead(players[1], "test_kill")
    # now check win condition
    winner = game.check_win()
    assert winner == "lovers"

def test_idiot_survives_vote():
    ww = load_app_module()
    rid = ww.create_room("owner2", max_players=4)
    for i in range(1, 4):
        ww.join_room(rid, f"AI_{i}")
    ww.start_room_game(rid)
    game = ww.rooms[rid]["game"]
    players = list(game.players)
    # ensure someone is idiot
    game.set_player_role(players[0], "idiot")
    # simulate voting lynch on idiot
    game.current_votes = {players[0]: 3}
    game._finalize_vote()
    # idiot should be revealed but still alive
    if game.gs and hasattr(game.gs, "get_player"):
        p = game.gs.get_player(players[0])
        assert p.idiot_revealed is True
    assert players[0] in game.alive