import React, { useState, useEffect, useRef } from "react";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

/*
Frontend with WebSocket integration and voting UI.
Filename: [`games/werewolf/frontend/src/App.jsx`](games/werewolf/frontend/src/App.jsx:1)
*/

export default function App() {
  const [gameId, setGameId] = useState("");
  const [game, setGame] = useState(null);
  const [log, setLog] = useState([]);
  const [numAI, setNumAI] = useState(5);
  const [simulating, setSimulating] = useState(false);
  const [myPlayerId, setMyPlayerId] = useState("");
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);

  const appendLog = (s) => {
    setLog((l) => [s, ...l]);
  };

  // -- REST helpers --
  async function createGame() {
    const res = await axios.post(`${API_BASE}/games`, { name: "werewolf-match" });
    setGameId(res.data.game_id);
    setGame(res.data.game);
    appendLog(`Created game ${res.data.game_id}`);
  }

  async function addAIPlayers(n) {
    if (!gameId) return;
    for (let i = 0; i < n; i++) {
      const name = `AI_${Math.floor(Math.random() * 10000)}`;
      await axios.post(`${API_BASE}/games/${gameId}/join`, {
        name,
        is_ai: true,
        ai_provider: "openai",
      });
      appendLog(`Added ${name}`);
    }
    await fetchGame();
  }

  async function joinAsHuman(name) {
    if (!gameId) return;
    const res = await axios.post(`${API_BASE}/games/${gameId}/join`, {
      name,
      is_ai: false,
    });
    setMyPlayerId(res.player_id || res.data?.player_id || "");
    appendLog(`Joined as ${name}`);
    await fetchGame();
  }

  async function startGame() {
    if (!gameId) return;
    const res = await axios.post(`${API_BASE}/games/${gameId}/start`);
    setGame(res.data.game);
    appendLog("Game started");
    // notify via WS broadcast will update clients
  }

  async function fetchGame() {
    if (!gameId) return;
    try {
      const res = await axios.get(`${API_BASE}/games/${gameId}`);
      setGame(res.data);
    } catch (e) {
      appendLog("Failed to fetch game: " + (e?.message || e));
    }
  }

  async function triggerAITurn() {
    if (!gameId) return;
    const res = await axios.post(`${API_BASE}/games/${gameId}/ai_turn`);
    setGame(res.data.game);
    appendLog("AI turn executed");
  }

  async function resolveNight() {
    if (!gameId) return;
    const res = await axios.post(`${API_BASE}/games/${gameId}/resolve_night`);
    setGame(res.data.game);
    appendLog("Night resolved");
  }

  async function simulateAI(n) {
    setSimulating(true);
    try {
      const res = await axios.post(`${API_BASE}/simulate_ai_game?num_players=${n}`);
      setGame(res.data.game);
      appendLog("AI simulation complete");
      if (res.data.logs) {
        res.data.logs.forEach((l) => appendLog(l));
      }
    } catch (e) {
      appendLog("Simulation failed: " + (e?.message || e));
    } finally {
      setSimulating(false);
    }
  }

  // Vote action
  async function vote(actorId, targetId) {
    if (!gameId) return;
    try {
      await axios.post(`${API_BASE}/games/${gameId}/vote?actor_id=${actorId}&target_id=${targetId}`);
      appendLog(`Vote cast: ${actorId} -> ${targetId}`);
      // after vote, fetch or rely on WS to update
      await fetchGame();
    } catch (e) {
      appendLog("Vote failed: " + (e?.message || e));
    }
  }

  // Tally votes (admin action)
  async function tallyVotes() {
    if (!gameId) return;
    try {
      const res = await axios.post(`${API_BASE}/games/${gameId}/tally_votes`);
      setGame(res.data.game);
      appendLog("Votes tallied");
    } catch (e) {
      appendLog("Tally failed: " + (e?.message || e));
    }
  }

  // -- WebSocket handling --
  useEffect(() => {
    // open WS when gameId present
    if (!gameId) return;
    let ws;
    const url = (import.meta.env.VITE_WS_BASE || API_BASE).replace(/^http/, "ws") + `/ws/${gameId}`;
    try {
      ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onopen = () => {
        appendLog("WS connected");
        // request current state explicitly
        ws.send("get_state");
      };
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data.type === "game_state") {
            setGame(data.game);
            appendLog("Game state updated (ws)");
          } else if (data.type === "game_created") {
            appendLog("Game created (ws)");
          } else if (data.type === "ack") {
            // ignore
          } else {
            appendLog(`WS msg: ${JSON.stringify(data)}`);
          }
        } catch (err) {
          // plain text
          appendLog(`WS: ${ev.data}`);
        }
      };
      ws.onclose = () => {
        appendLog("WS closed, will attempt reconnect");
        // reconnect with backoff
        if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
        reconnectTimer.current = setTimeout(() => {
          if (gameId) {
            // re-run effect by toggling state (fetchGame will open new ws on next render)
            fetchGame();
          }
        }, 1500);
      };
      ws.onerror = (e) => {
        appendLog("WS error");
      };
    } catch (e) {
      appendLog("WS connect failed: " + (e?.message || e));
    }
    return () => {
      if (ws && ws.readyState === WebSocket.OPEN) ws.close();
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gameId]);

  // select my player from list
  useEffect(() => {
    if (!game || !game.players) return;
    // auto-select a non-ai alive player if exists and myPlayerId not set
    if (!myPlayerId) {
      const human = game.players.find((p) => !p.is_ai && p.alive);
      if (human) setMyPlayerId(human.id);
    }
  }, [game, myPlayerId]);

  return (
    <div style={{ padding: 20, fontFamily: "Arial, sans-serif" }}>
      <h1>Werewolf AI Arena</h1>
      <div style={{ marginBottom: 10 }}>
        <button onClick={createGame}>Create Game</button>
        <input
          placeholder="Game ID (or auto)"
          value={gameId}
          onChange={(e) => setGameId(e.target.value)}
          style={{ marginLeft: 8, padding: 6 }}
        />
        <span style={{ marginLeft: 10 }}>{gameId && `Game: ${gameId}`}</span>
      </div>

      <div style={{ marginBottom: 10 }}>
        <label>AI to add: </label>
        <input
          type="number"
          value={numAI}
          onChange={(e) => setNumAI(Number(e.target.value))}
          style={{ width: 60 }}
        />
        <button onClick={() => addAIPlayers(numAI)} style={{ marginLeft: 8 }}>
          Add AI Players
        </button>
        <button onClick={() => joinAsHuman(prompt("Enter your player name:", `Human_${Math.floor(Math.random()*1000)}`) || "Human")} style={{ marginLeft: 8 }}>
          Join as Human
        </button>
      </div>

      <div style={{ marginBottom: 10 }}>
        <button onClick={startGame}>Start Game</button>
        <button onClick={triggerAITurn} style={{ marginLeft: 8 }}>
          AI Night Turn
        </button>
        <button onClick={resolveNight} style={{ marginLeft: 8 }}>
          Resolve Night
        </button>
        <button onClick={() => simulateAI(6)} style={{ marginLeft: 8 }} disabled={simulating}>
          Simulate 6-AI Game
        </button>
        <button onClick={tallyVotes} style={{ marginLeft: 8 }}>
          Tally Votes
        </button>
      </div>

      <div style={{ display: "flex", gap: 20 }}>
        <div style={{ flex: 1 }}>
          <h3>Players</h3>
          <div style={{ background: "#f5f5f5", padding: 10, borderRadius: 6 }}>
            {!game && <div>No game loaded</div>}
            {game && game.players && (
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: "left" }}>Name</th>
                    <th>Role</th>
                    <th>Alive</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {game.players.map((p) => (
                    <tr key={p.id} style={{ background: p.alive ? "transparent" : "#fdd" }}>
                      <td>{p.name}</td>
                      <td>{p.role || "-"}</td>
                      <td>{p.alive ? "✅" : "❌"}</td>
                      <td>
                        {game.state === "day" && p.alive && myPlayerId && (
                          <button
                            onClick={() => vote(myPlayerId, p.id)}
                            disabled={myPlayerId === p.id}
                            title={myPlayerId === p.id ? "Cannot vote yourself" : `Vote ${p.name}`}
                          >
                            Vote
                          </button>
                        )}
                        {p.is_ai && <span style={{ marginLeft: 8, color: "#666" }}>AI</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <h3 style={{ marginTop: 16 }}>Game State</h3>
          <pre style={{ background: "#f9f9f9", padding: 10, borderRadius: 6 }}>{JSON.stringify(game, null, 2)}</pre>
        </div>

        <div style={{ width: 420 }}>
          <h3>Logs</h3>
          <div style={{ maxHeight: 520, overflow: "auto", background: "#fafafa", padding: 10 }}>
            {log.map((l, i) => (
              <div key={i} style={{ padding: "4px 0", borderBottom: "1px solid #eee" }}>
                {l}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}