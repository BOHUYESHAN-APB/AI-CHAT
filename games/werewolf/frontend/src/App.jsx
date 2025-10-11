import React, { useState, useEffect } from "react";

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
  const [text, setText] = useState("");
  const [status, setStatus] = useState("");

  async function load() {
    setStatus("加载中...");
    try {
      const res = await fetch("/config/api_keys");
      if (!res.ok) {
        setStatus("未找到 api 配置，展示空白");
        setText("{}");
        return;
      }
      const data = await res.json();
      setText(JSON.stringify(data || {}, null, 2));
      setStatus("已加载");
    } catch (e) {
      setText("{}");
      setStatus("加载失败（请确保后端提供 /config/api_keys）");
    }
  }

  async function save() {
    setStatus("保存中...");
    try {
      const parsed = JSON.parse(text || "{}");
      const res = await fetch("/config/api_keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(parsed),
      });
      if (!res.ok) {
        setStatus("保存失败");
        return;
      }
      setStatus("已保存");
    } catch (e) {
      setStatus("JSON 解析失败，无法保存");
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div style={{ padding: 12 }}>
      <h3>API Keys 编辑</h3>
      <div style={{ marginBottom: 8, color: "#666" }}>
        编辑项目根目录的 <code>api_keys.json</code>（或等价格式）。请勿提交 secret 到公共仓库。
      </div>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        style={{ width: "100%", height: 220, fontFamily: "monospace", fontSize: 13 }}
      />
      <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
        <button onClick={save}>保存到 /config/api_keys</button>
        <button onClick={load}>重新加载</button>
        <div style={{ marginLeft: 8, color: "#333", alignSelf: "center" }}>{status}</div>
      </div>
    </div>
  );
}

function PlayersConfig() {
  const [cfg, setCfg] = useState({ players: [], role_preferences: {} });
  const [status, setStatus] = useState("");

  async function load() {
    setStatus("加载中...");
    try {
      const res = await fetch("/config/players");
      if (!res.ok) {
        // default empty config
        setCfg({ players: [], role_preferences: {} });
        setStatus("无配置，使用默认");
        return;
      }
      const data = await res.json();
      setCfg(data || { players: [], role_preferences: {} });
      setStatus("已加载");
    } catch (e) {
      setCfg({ players: [], role_preferences: {} });
      setStatus("加载失败（请确保后端提供 /config/players）");
    }
  }

  useEffect(() => {
    load();
  }, []);

  function addPlayer() {
    const name = `AI_${cfg.players.length + 1}`;
    setCfg((s) => ({ ...s, players: [...s.players, name] }));
  }

  function removePlayer(idx) {
    setCfg((s) => {
      const players = s.players.slice();
      const removed = players.splice(idx, 1)[0];
      const role_preferences = { ...s.role_preferences };
      if (role_preferences[removed]) delete role_preferences[removed];
      return { players, role_preferences };
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

  async function save() {
    setStatus("保存中...");
    try {
      const res = await fetch("/config/players", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cfg),
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

  return (
    <div style={{ padding: 12 }}>
      <h3>玩家 & 职业偏好</h3>
      <div style={{ marginBottom: 8, color: "#666" }}>
        配置 6–12 名玩家并为部分玩家设定职业偏好（有偏好则不随机）。
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

  async function fetchRooms() {
    try {
      const res = await fetch("/rooms");
      const data = await res.json();
      setRooms(data.rooms || []);
    } catch (e) {
      setStatus("无法加载房间（请启动后端）");
    }
  }

  useEffect(() => {
    fetchRooms();
  }, []);

  async function createRoom() {
    setStatus("创建房间...");
    try {
      const res = await fetch("/rooms", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ owner: "UI_owner", max_players: 6 }),
      });
      await fetchRooms();
      setStatus("已创建");
    } catch {
      setStatus("创建失败");
    }
  }

  return (
    <div style={{ padding: 12 }}>
      <h3>房间控制</h3>
      <div style={{ marginBottom: 8 }}>
        <button onClick={createRoom}>创建房间（6 人）</button>{" "}
        <button onClick={fetchRooms}>刷新</button>
      </div>
      <div>
        {rooms.length === 0 && <div>无房间</div>}
        {rooms.map((r) => (
          <div key={r.id} style={{ padding: 8, borderBottom: "1px solid #eee" }}>
            <strong>{r.id}</strong> — 主持: {r.owner} — 状态: {r.state} — 玩家: {r.players.join(", ")}
          </div>
        ))}
      </div>
      <div style={{ marginTop: 8, color: "#333" }}>{status}</div>
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState("rooms");

  return (
    <div style={{ fontFamily: "Inter, Arial, sans-serif", padding: 20, maxWidth: 1000, margin: "0 auto" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h2 style={{ margin: 0 }}>狼人杀（AI 评测）控制台</h2>
        <nav style={{ display: "flex", gap: 8 }}>
          <button onClick={() => setTab("rooms")} style={{ padding: 8 }}>
            房间
          </button>
          <button onClick={() => setTab("api_keys")} style={{ padding: 8 }}>
            API Keys
          </button>
          <button onClick={() => setTab("players")} style={{ padding: 8 }}>
            玩家配置
          </button>
        </nav>
      </header>

      <main style={{ background: "#fff", borderRadius: 12, boxShadow: "0 6px 18px rgba(0,0,0,0.06)", padding: 12 }}>
        {tab === "rooms" && <RoomsPanel />}
        {tab === "api_keys" && <ApiKeysEditor />}
        {tab === "players" && <PlayersConfig />}
      </main>

      <footer style={{ marginTop: 12, color: "#666" }}>
        注意：API key 存在项目根目录（api_keys.json），请在运行前正确配置。前端会调用 /config/* 接口读取与保存配置。
      </footer>
    </div>
  );
}