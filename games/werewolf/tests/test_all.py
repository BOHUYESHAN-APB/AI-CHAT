import pytest
from uuid import UUID
from fastapi.testclient import TestClient
from games.werewolf.backend.models import Game, Player, Role
from games.werewolf.backend.app import app

client = TestClient(app)

def create_player(name, role=None, is_ai=False):
    p = Player(name=name, is_ai=is_ai)
    if role:
        p.role = role
    return p

def test_resolve_night_save_protects():
    g = Game(name="test1")
    wolf = create_player("wolf", Role.WEREWOLF, is_ai=True)
    victim = create_player("victim", Role.VILLAGER, is_ai=False)
    doc = create_player("doc", Role.DOCTOR, is_ai=False)
    g.add_player(wolf)
    g.add_player(victim)
    g.add_player(doc)
    g.state = g.state.NIGHT
    g.night = 1
    g.perform_night_action(actor_id=wolf.id, action_type="kill", target_id=victim.id)
    g.perform_night_action(actor_id=doc.id, action_type="save", target_id=victim.id)
    report = g.resolve_night()
    # victim should be alive
    assert any(p.name == "victim" and p.alive for p in g.players)
    assert report == [] or len(report) == 0

def test_resolve_night_kill_without_save():
    g = Game(name="test2")
    wolf = create_player("wolf", Role.WEREWOLF, is_ai=True)
    victim = create_player("victim", Role.VILLAGER, is_ai=False)
    g.add_player(wolf)
    g.add_player(victim)
    g.state = g.state.NIGHT
    g.night = 1
    g.perform_night_action(actor_id=wolf.id, action_type="kill", target_id=victim.id)
    report = g.resolve_night()
    # victim should be dead
    assert any(p.name == "victim" and not p.alive for p in g.players)
    assert any(isinstance(r, dict) and "killed" in r for r in report) or len(report) >= 1

def test_tally_votes_eliminates():
    g = Game(name="vote-test")
    p1 = create_player("p1", Role.VILLAGER)
    p2 = create_player("p2", Role.VILLAGER)
    p3 = create_player("p3", Role.WEREWOLF)
    g.add_player(p1)
    g.add_player(p2)
    g.add_player(p3)
    g.state = g.state.DAY
    g.day = 1
    # p1 and p3 vote for p2
    g.vote(actor_id=p1.id, target_id=p2.id)
    g.vote(actor_id=p3.id, target_id=p2.id)
    eliminated = g.tally_votes()
    assert eliminated is not None
    assert str(p2.id) == eliminated
    assert not p2.alive

def test_simulate_ai_game_endpoint_runs():
    resp = client.post("/simulate_ai_game?num_players=4")
    assert resp.status_code == 200
    data = resp.json()
    assert "game" in data
    assert "logs" in data
    game = data["game"]
    assert "state" in game
    assert isinstance(data["logs"], list)

if __name__ == "__main__":
    pytest.main(["-q", __file__])