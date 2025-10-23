import React, { useState, useEffect, useRef } from "react";

/**
 * 圆桌狼人杀游戏可视化组件
 * 特性：
 * - AI玩家围绕圆形桌面分布
 * - 气泡框显示发言
 * - 头像框显示玩家状态
 * - 中央显示游戏阶段和状态
 * - 可选显示角色职业
 */

const RoundTableGame = ({ roomId }) => {
  const [roomState, setRoomState] = useState(null);
  const [showRoles, setShowRoles] = useState(false);
  const [activeSpeech, setActiveSpeech] = useState(null);
  const [autoStep, setAutoStep] = useState(true);
  const [avatars, setAvatars] = useState({});
  const canvasRef = useRef(null);

  useEffect(() => {
    // 加载头像配置
    loadAvatars();
  }, []);

  useEffect(() => {
    if (!roomId) return;
    loadRoomState();
    const interval = setInterval(loadRoomState, 2000); // 每2秒刷新
    return () => clearInterval(interval);
  }, [roomId]);

  useEffect(() => {
    let tid = null;
    if (autoStep && roomState && roomState.game && roomState.game.state !== "ended") {
      tid = setInterval(() => {
        (async () => {
          try {
            await handleStep();
          } catch (e) {
            // ignore
          }
        })();
      }, 3000);
    }
    return () => tid && clearInterval(tid);
  }, [autoStep, roomState, roomId]);

  async function loadAvatars() {
    try {
      const res = await fetch("/config/players");
      if (!res.ok) return;
      const data = await res.json();
      setAvatars(data.avatars || {});
    } catch (e) {
      console.error("加载头像失败", e);
    }
  }

  async function loadRoomState() {
    try {
      const res = await fetch(`/rooms/${roomId}/state`);
      if (!res.ok) return;
      const data = await res.json();
      // detect new talks and auto-open latest speaker bubble briefly
      const prevTalks = (roomState && roomState.game && roomState.game.phase_context && roomState.game.phase_context.current_talks) || [];
      const newTalks = (data && data.game && data.game.phase_context && data.game.phase_context.current_talks) || [];
      if (newTalks.length > 0 && prevTalks.length !== newTalks.length) {
        const latest = newTalks[newTalks.length - 1];
        setActiveSpeech(latest.player);
        setTimeout(() => setActiveSpeech(null), 4000);
      }
      setRoomState(data);
    } catch (e) {
      console.error("加载房间状态失败", e);
    }
  }

  if (!roomState || !roomState.game) {
    return (
      <div style={{ padding: 40, textAlign: "center", color: "#999" }}>
        <div style={{ fontSize: 18, marginBottom: 12 }}>🎮 等待游戏开始...</div>
        <div>房间ID: {roomId || "未知"}</div>
      </div>
    );
  }

  const game = roomState.game;
  const players = game.players || [];
  const alive = game.alive || [];
  const roles = game.roles || {};
  const phase = game.state || "waiting";
  const day = game.day || 0;

  // 计算玩家在圆桌上的位置
  const centerX = 400;
  const centerY = 300;
  const radius = 200;
  const playerPositions = players.map((player, index) => {
    const angle = (index / players.length) * 2 * Math.PI - Math.PI / 2; // 从顶部开始
    return {
      player,
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
      angle,
      isAlive: alive.includes(player),
      role: roles[player] || "unknown",
    };
  });

  // 获取最近的发言（用于气泡显示），优先使用 phase_context.current_talks
  const recentTalks = (game.phase_context && game.phase_context.current_talks ? game.phase_context.current_talks : game.current_talks || []).slice(-6);

  // 阶段显示文本
  const phaseText = {
    waiting: "⏳ 等待中",
    lobby: "🏠 大厅",
    night: "🌙 夜间",
    day_morning: "🌅 破晓",
    day_discussion: "💬 讨论",
    day_voting: "🗳️ 投票",
    vote_reveal: "📊 揭晓",
    ended: "🏁 游戏结束",
  }[phase] || phase;

  async function handleStep() {
    try {
      if (!roomState || !roomState.game) {
        await loadRoomState();
        return;
      }
      if (roomState.game.state === "ended") {
        setAutoStep(false);
        return;
      }
      const before = (roomState && roomState.game && roomState.game.state) || null;
      await fetch(`/rooms/${roomId}/step`, { method: "POST" });
      const start = Date.now();
      let latest = null;
      while (Date.now() - start < 8000) {
        await new Promise((r) => setTimeout(r, 700));
        const res = await fetch(`/rooms/${roomId}/state`);
        if (!res.ok) continue;
        const data = await res.json();
        latest = data;
        const nowState = (data && data.game && data.game.state) || null;
        setRoomState(data);
        if (before !== nowState) {
          break;
        }
      }
      if (!latest) {
        await loadRoomState();
      }
    } catch (e) {
      console.error("推进游戏失败", e);
    }
  }

  return (
    <div style={{ padding: 20, background: "#f8f9fa", minHeight: "100vh" }}>
      {/* 顶部控制栏 */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <h2 style={{ margin: 0 }}>🐺 狼人杀 - 房间 {roomId}</h2>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <input type="checkbox" checked={showRoles} onChange={(e) => setShowRoles(e.target.checked)} />
            <span>显示职业</span>
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <input type="checkbox" checked={autoStep} onChange={(e) => setAutoStep(e.target.checked)} />
            <span>自动推进（调试）</span>
          </label>
          <button onClick={handleStep} style={{ padding: "8px 16px", cursor: "pointer" }}>
            ▶️ 推进游戏
          </button>
          <button onClick={loadRoomState} style={{ padding: "8px 16px", cursor: "pointer" }}>
            🔄 刷新
          </button>
        </div>
      </div>

      {/* 调试面板 */}
      <div style={{ marginTop: 18, padding: 12, background: "#fff", borderRadius: 8, boxShadow: "0 2px 8px rgba(0,0,0,0.06)" }}>
        <h4 style={{ margin: 0 }}>调试信息</h4>
        <div style={{ fontSize: 12, color: "#666", marginTop: 6 }}>完整 game 对象（便于观察 roles / alive / phase_context）</div>
        <pre style={{ maxHeight: 200, overflow: "auto", background: "#f7f7fb", padding: 8, borderRadius: 6 }}>{JSON.stringify(game, null, 2)}</pre>
      </div>

      {/* 游戏主画布 */}
      <div
        style={{
          position: "relative",
          width: 800,
          height: 600,
          margin: "0 auto",
          background: "#fff",
          borderRadius: 16,
          boxShadow: "0 4px 20px rgba(0,0,0,0.1)",
          overflow: "hidden",
        }}
      >
        {/* 中央桌面区域 */}
        <div
          style={{
            position: "absolute",
            left: centerX - 100,
            top: centerY - 100,
            width: 200,
            height: 200,
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            borderRadius: "50%",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            color: "#fff",
            boxShadow: "0 8px 32px rgba(102, 126, 234, 0.4)",
          }}
        >
          <div style={{ fontSize: 24, fontWeight: "bold", marginBottom: 8 }}>{phaseText}</div>
          <div style={{ fontSize: 16, opacity: 0.9 }}>第 {day} 天</div>
          <div style={{ fontSize: 12, opacity: 0.7, marginTop: 8 }}>
            存活: {alive.length}/{players.length}
          </div>
        </div>

        {/* 玩家位置 */}
        {playerPositions.map(({ player, x, y, isAlive, role }, index) => {
          const recentSpeech = recentTalks.find((t) => t.player === player);
          const showBubble = recentSpeech && activeSpeech === player;

          return (
            <div key={player} style={{ position: "absolute", left: x - 40, top: y - 40 }}>
              {/* 玩家头像框 */}
              <div
                onClick={() => setActiveSpeech(activeSpeech === player ? null : player)}
                style={{
                  width: 80,
                  height: 80,
                  borderRadius: "50%",
                  ...(avatars[player] 
                    ? {
                        backgroundImage: `url(${avatars[player]})`,
                        backgroundSize: "cover",
                        backgroundPosition: "center",
                      }
                    : {
                        background: isAlive ? "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)" : "#ccc",
                      }
                  ),
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: "pointer",
                  border: showBubble ? "3px solid #667eea" : "3px solid #fff",
                  boxShadow: isAlive ? "0 4px 12px rgba(240, 147, 251, 0.4)" : "0 2px 8px rgba(0,0,0,0.2)",
                  transition: "all 0.3s",
                  position: "relative",
                  opacity: isAlive ? 1 : 0.5,
                }}
              >
                {/* 玩家名称（如果没有头像才显示） */}
                {!avatars[player] && (
                  <div style={{ fontSize: 12, fontWeight: "bold", color: "#fff", textAlign: "center" }}>
                    {player.replace("AI_", "")}
                  </div>
                )}

                {/* 职业显示 */}
                {showRoles && (
                  <div
                    style={{
                      fontSize: 10,
                      color: "#fff",
                      background: "rgba(0,0,0,0.3)",
                      padding: "2px 6px",
                      borderRadius: 8,
                      marginTop: 4,
                    }}
                  >
                    {role}
                  </div>
                )}

                {/* 状态图标 */}
                {!isAlive && (
                  <div
                    style={{
                      position: "absolute",
                      top: -5,
                      right: -5,
                      background: "#f44336",
                      color: "#fff",
                      borderRadius: "50%",
                      width: 24,
                      height: 24,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 14,
                    }}
                  >
                    ☠️
                  </div>
                )}
              </div>

              {/* 气泡框（发言） */}
              {showBubble && recentSpeech && (
                <div
                  style={{
                    position: "absolute",
                    left: x > centerX ? -200 : 90,
                    top: -20,
                    width: 200,
                    background: "#fff",
                    border: "2px solid #667eea",
                    borderRadius: 12,
                    padding: 12,
                    boxShadow: "0 4px 16px rgba(0,0,0,0.15)",
                    fontSize: 12,
                    color: "#333",
                    zIndex: 1000,
                  }}
                >
                  <div style={{ fontWeight: "bold", marginBottom: 4, color: "#667eea" }}>
                    {player} 说:
                  </div>
                  <div style={{ lineHeight: 1.4 }}>
                    {recentSpeech.speech?.substring(0, 100) || "..."}
                  </div>
                  {/* 气泡三角 */}
                  <div
                    style={{
                      position: "absolute",
                      [x > centerX ? "right" : "left"]: -10,
                      top: 20,
                      width: 0,
                      height: 0,
                      borderTop: "8px solid transparent",
                      borderBottom: "8px solid transparent",
                      [x > centerX ? "borderLeft" : "borderRight"]: "10px solid #667eea",
                    }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* 底部信息栏 */}
      <div
        style={{
          marginTop: 20,
          padding: 16,
          background: "#fff",
          borderRadius: 12,
          boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
        }}
      >
        <h3 style={{ margin: "0 0 12px 0" }}>💬 最近发言</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {recentTalks.length === 0 && <div style={{ color: "#999" }}>暂无发言</div>}
          {recentTalks.map((talk, idx) => (
            <div
              key={idx}
              style={{
                padding: 10,
                background: "#f8f9fa",
                borderRadius: 8,
                borderLeft: "3px solid #667eea",
              }}
            >
              <strong>{talk.player}</strong>: {talk.speech}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default RoundTableGame;
