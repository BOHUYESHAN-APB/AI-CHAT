import React, { useState, useEffect } from "react";
import RoundTableGame from "./RoundTableGame";

const ROLES = ["werewolf", "seer", "witch", "villager"];

/*
  说明：
  - 该文件实现三个主界面标签：房间列表（只读/控制），API Key 编辑器，玩家与职业偏好配置。
  - API:
    GET  /config/api_keys
    POST /config/api_keys
    GET  /config/players
    POST /config/players
  - 后端如果尚未实现这些端点，保存/加载会返回网络错误；先实现前端后再同步后端。
*/

function ApiKeysEditor() {
  const [providers, setProviders] = useState({}); // name -> { api_key, model, model_url }
  const [status, setStatus] = useState("");
  const [editing, setEditing] = useState(null); // name being edited
  const [form, setForm] = useState({ name: "", api_key: "", model: "", model_url: "" });

  async function load() {
    setStatus("加载中...");
    try {
      const res = await fetch("/config/api_keys");
      if (!res.ok) {
        setProviders({});
        setStatus("未找到 api 配置，展示空白");
        return;
      }
      const data = await res.json();
      // normalize structure:
      // preferred shape: { "providers": { name: {api_key, model, model_url}, ... }, ... }
      // fallback: top-level dict where some keys are provider objects; ignore unrelated keys like "player_map"
      let p = {};
      if (data && typeof data === "object") {
        if (data.providers && typeof data.providers === "object") {
          p = data.providers;
        } else {
          // pick only entries that look like provider objects
          Object.entries(data).forEach(([k, v]) => {
            if (v && typeof v === "object") {
              const hasApiKey = "api_key" in v || "key" in v || "secret" in v;
              const hasModel = "model" in v || "model_url" in v;
              if (hasApiKey || hasModel) {
                p[k] = v;
              }
            }
          });
        }
      }
      setProviders(p || {});
      setStatus("已加载");
    } catch (e) {
      setProviders({});
      setStatus("加载失败（请确保后端提供 /config/api_keys）");
    }
  }

  function startEdit(name) {
    const val = providers[name] || { api_key: "", model: "", model_url: "" };
    setEditing(name);
    setForm({ name, api_key: val.api_key || "", model: val.model || "", model_url: val.model_url || "" });
  }

  function cancelEdit() {
    setEditing(null);
    setForm({ name: "", api_key: "", model: "", model_url: "" });
  }

  function applyForm() {
    const name = form.name.trim();
    if (!name) {
      setStatus("Provider 名称不能为空");
      return;
    }
    setProviders((s) => ({ ...s, [name]: { api_key: form.api_key, model: form.model, model_url: form.model_url } }));
    setEditing(null);
    setForm({ name: "", api_key: "", model: "", model_url: "" });
    setStatus("已更新本地配置（需保存到后端）");
  }

  function deleteProvider(name) {
    setProviders((s) => {
      const copy = { ...s };
      delete copy[name];
      return copy;
    });
    setStatus("已删除 provider（需保存到后端）");
  }

  async function save() {
    setStatus("保存中...");
    try {
      const body = { providers: providers, updated_at: new Date().toISOString() };
      const res = await fetch("/config/api_keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        setStatus("保存失败");
        return;
      }
      setStatus("已保存");
    } catch (e) {
      setStatus("保存失败（网络错误）");
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div style={{ padding: 12 }}>
      <h3>可视化 API Providers 编辑</h3>
      <div style={{ marginBottom: 8, color: "#666" }}>
        管理 providers（名称、api_key、默认 model / model_url）。保存后会写入项目根目录的 <code>api_keys.json</code>。
      </div>

      <div style={{ display: "flex", gap: 12 }}>
        <div style={{ flex: 1 }}>
          <div style={{ marginBottom: 8 }}>
            <button onClick={() => startEdit("")}>新增 Provider</button>{" "}
            <button onClick={save}>保存到后端</button>{" "}
            <button onClick={load}>重新加载</button>
            <span style={{ marginLeft: 8, color: "#333" }}>{status}</span>
          </div>

          <div style={{ border: "1px solid #eee", borderRadius: 8, padding: 8 }}>
            {Object.keys(providers).length === 0 && <div style={{ color: "#666" }}>暂无 provider 配置</div>}
            {Object.entries(providers).map(([name, val]) => (
              <div key={name} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: 6 }}>
                <div>
                  <strong>{name}</strong>
                  <div style={{ color: "#666", fontSize: 12 }}>
                    model: {val.model || "-"} {val.model_url ? `(url)` : ""}
                  </div>
                </div>
                <div style={{ display: "flex", gap: 8, flexDirection: "column", alignItems: "flex-end" }}>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button onClick={() => startEdit(name)}>编辑</button>
                    <button onClick={() => deleteProvider(name)}>删除</button>
                    <button
                      onClick={async () => {
                        setStatus("测试中...");
                        try {
                          const res = await fetch(`/config/api_keys/test?provider=${encodeURIComponent(name)}`);
                          if (!res.ok) {
                            const d = await res.json().catch(() => ({}));
                            setStatus(`测试失败: ${d.error || res.status}`);
                          } else {
                            const d = await res.json();
                            setStatus(`测试结果: has_key=${d.has_key}, reachable=${d.reachable}`);
                          }
                        } catch (e) {
                          setStatus(`测试错误: ${e.message}`);
                        }
                        // reload providers to ensure no stale state
                        load();
                      }}
                    >
                      联通测试
                    </button>
                  </div>
                  <div style={{ fontSize: 12, color: "#444" }}>{/* status per-row is global status shown top */}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ width: 360 }}>
          <div style={{ padding: 8, border: "1px solid #eee", borderRadius: 8 }}>
            <h4 style={{ marginTop: 0 }}>{editing === null ? "编辑" : editing === "" ? "新增 Provider" : `编辑: ${editing}`}</h4>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <input placeholder="Provider 名称" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              <input placeholder="API Key" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} />
              <input placeholder="模型名 (可选)" value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} />
              <input placeholder="模型 URL (可选)" value={form.model_url} onChange={(e) => setForm({ ...form, model_url: e.target.value })} />
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={applyForm}>应用</button>
                <button onClick={cancelEdit}>取消</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function PlayersConfig() {
  const [cfg, setCfg] = useState({ players: [], role_preferences: {}, player_map: {} });
  const [providers, setProviders] = useState({});
  const [status, setStatus] = useState("");

  async function load() {
    setStatus("加载中...");
    try {
      const [pRes, aRes] = await Promise.all([fetch("/config/players"), fetch("/config/api_keys")]);
      let playersCfg = { players: [], role_preferences: {}, player_map: {} };
      if (pRes.ok) {
        playersCfg = await pRes.json();
      }
      let apiCfg = {};
      if (aRes.ok) {
        const apiData = await aRes.json();
        apiCfg = (apiData && apiData.providers) || apiData || {};
      }
      // ensure player_map exists
      playersCfg.player_map = playersCfg.player_map || {};
      // if no mapping for a player and providers exist, assign first provider as default mapping
      const providerNames = Object.keys(apiCfg);
      for (const p of (playersCfg.players || [])) {
        if (!playersCfg.player_map[p] && providerNames.length > 0) {
          playersCfg.player_map[p] = providerNames[0];
        }
      }
      setCfg(playersCfg);
      setProviders(apiCfg);
      setStatus("已加载");
    } catch (e) {
      setCfg({ players: [], role_preferences: {}, player_map: {} });
      setProviders({});
      setStatus("加载失败（请确保后端提供 /config/players 与 /config/api_keys）");
    }
  }

  useEffect(() => {
    load();
  }, []);

  function addPlayer() {
    const name = `AI_${cfg.players.length + 1}`;
    setCfg((s) => {
      const players = [...s.players, name];
      const player_map = { ...(s.player_map || {}) };
      const first = Object.keys(providers)[0] || null;
      if (first) player_map[name] = first;
      return { ...s, players, player_map };
    });
  }

  function removePlayer(idx) {
    setCfg((s) => {
      const players = s.players.slice();
      const removed = players.splice(idx, 1)[0];
      const role_preferences = { ...s.role_preferences };
      if (role_preferences[removed]) delete role_preferences[removed];
      const player_map = { ...(s.player_map || {}) };
      if (player_map[removed]) delete player_map[removed];
      return { ...s, players, role_preferences, player_map };
    });
  }

  function setPreference(player, role) {
    setCfg((s) => {
      const rp = { ...s.role_preferences };
      if (role) rp[player] = role;
      else delete rp[player];
      return { ...s, role_preferences: rp };
    });
  }

  function setPlayerProvider(player, providerName) {
    setCfg((s) => {
      const pm = { ...(s.player_map || {}) };
      if (providerName) pm[player] = providerName;
      else delete pm[player];
      return { ...s, player_map: pm };
    });
  }

  async function save() {
    setStatus("保存中...");
    try {
      const res = await fetch("/config/players", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cfg),
      });
      // try to parse response for diagnostics
      let data = null;
      try {
        data = await res.json();
      } catch (e) {
        data = null;
      }
      if (!res.ok) {
        const errMsg = (data && (data.error || data.message)) || `HTTP ${res.status}`;
        setStatus(`保存失败: ${errMsg}`);
        return;
      }
      // refresh local view to confirm persistence and default mappings
      await load();
      setStatus("已保存并已刷新");
    } catch (e) {
      setStatus("保存失败（网络错误）");
    }
  }

  return (
    <div style={{ padding: 12 }}>
      <h3>玩家 & 职业偏好</h3>
      <div style={{ marginBottom: 8, color: "#666" }}>
        配置 6–12 名玩家并为部分玩家设定职业偏好（有偏好则不随机）。为每位玩家选择使用的 provider（来自 API Keys → Providers）。
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {cfg.players.map((p, idx) => (
          <div
            key={p}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: 8,
              borderRadius: 8,
              background: "#fafafa",
              border: "1px solid #eee",
            }}
          >
            <div style={{ width: 120 }}>{p}</div>
            <select
              value={cfg.role_preferences[p] || ""}
              onChange={(e) => setPreference(p, e.target.value || null)}
            >
              <option value="">随机</option>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>

            <select
              value={(cfg.player_map && cfg.player_map[p]) || ""}
              onChange={(e) => setPlayerProvider(p, e.target.value || null)}
            >
              <option value="">默认</option>
              {Object.keys(providers).map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>

            <div style={{ flex: 1 }} />
            <button onClick={() => removePlayer(idx)}>移除</button>
          </div>
        ))}

        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={addPlayer}>添加 AI 玩家</button>
          <div style={{ alignSelf: "center", color: "#666" }}>{cfg.players.length} 个玩家</div>
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={save}>保存到 /config/players</button>
          <button onClick={load}>重新加载</button>
          <div style={{ color: "#333", alignSelf: "center" }}>{status}</div>
        </div>
      </div>
    </div>
  );
}

function RoomsPanel() {
  const [rooms, setRooms] = useState([]);
  const [status, setStatus] = useState("");
  const [joinName, setJoinName] = useState("AI_1");

  async function fetchRooms() {
    try {
      const res = await fetch("/rooms");
      const data = await res.json();
      setRooms(data.rooms || []);
      setStatus("");
    } catch (e) {
      setStatus("无法加载房间（请启动后端）");
    }
  }

  useEffect(() => {
    fetchRooms();
    // 每5秒自动刷新房间列表,确保状态同步
    const interval = setInterval(fetchRooms, 5000);
    return () => clearInterval(interval);
  }, []);

  async function createRoom() {
    setStatus("创建房间...");
    try {
      const res = await fetch("/rooms", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ owner: "UI_owner", max_players: 6 }),
      });
      // attempt to parse body for both legacy {room_id} and new {room, room_id}
      let data = null;
      try {
        data = await res.json();
      } catch (e) {
        data = null;
      }
      if (!res.ok) {
        setStatus(`创建失败: ${res.status} ${res.statusText}`);
        return;
      }
      // If backend returned full room object (new behavior), prefer it and update UI immediately
      if (data && data.room) {
        setStatus(`已创建房间 ${data.room.id} (或复用已存在房间)`);
        // 重要: 直接刷新房间列表,确保前端看到最新状态
        await fetchRooms();
      } else if (data && data.room_id) {
        setStatus(`已创建房间 ${data.room_id} (或复用已存在房间)`);
        // refresh rooms list to pick up server-side state
        await fetchRooms();
      } else {
        setStatus("已创建(响应格式异常,请刷新)");
        await fetchRooms();
      }
    } catch (e) {
      setStatus(`创建失败: ${e.message || "网络错误"}`);
    }
  }

  async function joinRoom(roomId) {
    setStatus(`加入 ${roomId}...`);
    try {
      const res = await fetch(`/rooms/${roomId}/join`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player: joinName }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setStatus(`加入失败: ${err.error || res.statusText}`);
        return;
      }
      setStatus(`已加入 ${roomId} 作为 ${joinName}`);
      await fetchRooms();
    } catch (e) {
      setStatus("加入失败（网络错误）");
    }
  }

  async function startRoom(roomId) {
    setStatus(`启动房局 ${roomId}...`);
    try {
      const res = await fetch(`/rooms/${roomId}/start`, { method: "POST" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setStatus(`启动失败: ${err.error || res.statusText}`);
        return;
      }
      setStatus(`房局 ${roomId} 已启动`);
      await fetchRooms();
    } catch (e) {
      setStatus("启动失败（网络错误）");
    }
  }

  return (
    <div style={{ padding: 12 }}>
      <h3>房间控制</h3>
      <div style={{ marginBottom: 8 }}>
        <button onClick={createRoom}>创建房间（6 人）</button>{" "}
        <button onClick={fetchRooms}>刷新</button>{" "}
        <span style={{ marginLeft: 12 }}>加入为玩家名:</span>
        <input style={{ marginLeft: 8, width: 100 }} value={joinName} onChange={(e) => setJoinName(e.target.value)} />
      </div>
      <div>
        {rooms.length === 0 && <div>无房间</div>}
        {rooms.map((r) => (
          <div key={r.id} style={{ padding: 8, borderBottom: "1px solid #eee", display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ flex: 1 }}>
              <strong>{r.id}</strong> — 主持: {r.owner} — 状态: {r.state} — 玩家: {r.players.join(", ")}
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={() => joinRoom(r.id)}>加入</button>
              <button onClick={() => startRoom(r.id)}>开始</button>
            </div>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 8, color: "#333" }}>{status}</div>
    </div>
  );
}

function GameViewer() {
  const [rooms, setRooms] = useState([]);
  const [selectedRoom, setSelectedRoom] = useState(null);
  const [status, setStatus] = useState("");

  async function fetchRooms() {
    try {
      const res = await fetch("/rooms");
      const data = await res.json();
      setRooms(data.rooms || []);
      setStatus("");
    } catch (e) {
      setStatus("无法加载房间列表(请启动后端)");
    }
  }

  useEffect(() => {
    fetchRooms();
    // 每5秒刷新房间列表
    const interval = setInterval(fetchRooms, 5000);
    // listen for external refreshRooms event
    const onRefresh = () => fetchRooms();
    window.addEventListener("refreshRooms", onRefresh);
    return () => {
      clearInterval(interval);
      window.removeEventListener("refreshRooms", onRefresh);
    };
  }, []);

  return (
    <div style={{ padding: 12 }}>
      {!selectedRoom && (
        <>
          <h3>游戏查看器（圆桌可视化）</h3>
          <div style={{ marginBottom: 8, color: "#666" }}>
            选择房间进入圆桌游戏可视化界面
          </div>

          <div style={{ marginBottom: 8 }}>
            <button onClick={fetchRooms}>🔄 刷新房间列表</button>
            <span style={{ color: "#333", marginLeft: 8 }}>{status}</span>
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
            {rooms.length === 0 && <div style={{ color: "#999" }}>暂无房间</div>}
            {rooms.map((r) => (
              <div
                key={r.id}
                onClick={() => setSelectedRoom(r.id)}
                style={{
                  padding: 16,
                  border: "2px solid #eee",
                  borderRadius: 12,
                  cursor: "pointer",
                  minWidth: 200,
                  transition: "all 0.3s",
                  background: r.state === "running" ? "#f0f9ff" : "#fff",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "#667eea";
                  e.currentTarget.style.boxShadow = "0 4px 12px rgba(102, 126, 234, 0.2)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "#eee";
                  e.currentTarget.style.boxShadow = "none";
                }}
              >
                <div style={{ fontSize: 16, fontWeight: "bold", marginBottom: 8 }}>
                  🎮 {r.id}
                </div>
                <div style={{ fontSize: 14, color: "#666", marginBottom: 4 }}>
                  状态: <strong>{r.state}</strong>
                </div>
                <div style={{ fontSize: 12, color: "#999" }}>
                  玩家: {r.players.length} 人
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {selectedRoom && (
        <>
          <button
            onClick={() => setSelectedRoom(null)}
            style={{
              marginBottom: 12,
              padding: "8px 16px",
              cursor: "pointer",
              background: "#667eea",
              color: "#fff",
              border: "none",
              borderRadius: 8,
            }}
          >
            ← 返回房间列表
          </button>
          <RoundTableGame roomId={selectedRoom} />
        </>
      )}
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState("rooms");
  // helper to switch tabs; when navigating to the game viewer, emit a refresh event so GameViewer updates immediately
  function handleTab(newTab) {
    setTab(newTab);
    if (newTab === "game") {
      // dispatch a global event that GameViewer listens to (ensures it refreshes when tab is opened)
      try {
        window.dispatchEvent(new CustomEvent("refreshRooms"));
      } catch (e) {
        // older browsers fallback
        const evt = document.createEvent("Event");
        evt.initEvent("refreshRooms", true, true);
        window.dispatchEvent(evt);
      }
    }
  }

  return (
    <div style={{ fontFamily: "Inter, Arial, sans-serif", padding: 20, maxWidth: 1000, margin: "0 auto" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h2 style={{ margin: 0 }}>狼人杀（AI 评测）控制台</h2>
        <nav style={{ display: "flex", gap: 8 }}>
          <button onClick={() => handleTab("rooms")} style={{ padding: 8 }}>
            房间
          </button>
          <button onClick={() => handleTab("api_keys")} style={{ padding: 8 }}>
            API Keys
          </button>
          <button onClick={() => handleTab("players")} style={{ padding: 8 }}>
            玩家配置
          </button>
          <button onClick={() => handleTab("game")} style={{ padding: 8 }}>
            游戏查看
          </button>
        </nav>
      </header>

      <main style={{ background: "#fff", borderRadius: 12, boxShadow: "0 6px 18px rgba(0,0,0,0.06)", padding: 12 }}>
        {tab === "rooms" && <RoomsPanel />}
        {tab === "api_keys" && <ApiKeysEditor />}
        {tab === "players" && <PlayersConfig />}
        {tab === "game" && <GameViewer />}
      </main>

      <footer style={{ marginTop: 12, color: "#666" }}>
        注意：API key 存在项目根目录（api_keys.json），请在运行前正确配置。前端会调用 /config/* 接口读取与保存配置。
      </footer>
    </div>
  );
}