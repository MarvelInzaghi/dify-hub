import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { copyText } from "../lib/clipboard";
import type { McpServer } from "../lib/types";
import { ErrorBox } from "../components/Feedback";

export default function McpPage() {
  const [items, setItems] = useState<McpServer[]>([]);
  const [openapiUrl, setOpenapiUrl] = useState("");
  const [name, setName] = useState("");
  const [port, setPort] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null);

  const load = async () => {
    try {
      setError("");
      setItems(await api.listMcpServers());
    } catch (e) {
      setError(String(e));
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const create = async () => {
    if (!openapiUrl || !name) return;
    try {
      setError("");
      const s = await api.createMcpServer({
        openapi_url: openapiUrl.trim(),
        name: name.trim(),
        port: port ? Number(port) : undefined,
      });
      setNotice(`已创建 MCP 服务「${s.name}」，地址：${s.mcp_url}`);
      setOpenapiUrl("");
      setName("");
      setPort("");
      void load();
    } catch (e) {
      setError(String(e));
    }
  };

  const stop = async (name: string) => {
    if (!confirm(`停止 MCP 服务「${name}」？`)) return;
    try {
      setError("");
      await api.deleteMcpServer(name);
      void load();
    } catch (e) {
      setError(String(e));
    }
  };

  const doCopy = async (url: string) => {
    if (await copyText(url)) {
      setCopiedUrl(url);
      window.setTimeout(() => setCopiedUrl((cur) => (cur === url ? null : cur)), 1500);
    }
  };

  return (
    <div>
      <h1>MCP 服务</h1>
      <ErrorBox error={error} />
      {notice && <div className="notice">{notice}</div>}

      <div className="card">
        <h2>快速构建 MCP 服务</h2>
        <div className="row" style={{ alignItems: "flex-end" }}>
          <div className="field" style={{ width: 320, marginBottom: 0 }}>
            <label>OpenAPI 地址</label>
            <input
              value={openapiUrl}
              onChange={(e) => setOpenapiUrl(e.target.value)}
              placeholder="http://localhost:8090/openapi.json"
            />
          </div>
          <div className="field" style={{ width: 200, marginBottom: 0 }}>
            <label>MCP 服务名</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="my-api-mcp" />
          </div>
          <div className="field" style={{ width: 120, marginBottom: 0 }}>
            <label>端口（可选）</label>
            <input value={port} onChange={(e) => setPort(e.target.value)} placeholder="自动" />
          </div>
          <button className="primary" onClick={() => void create()}>创建</button>
        </div>
        <p className="muted" style={{ margin: "8px 0 0", fontSize: 12 }}>
          输入一个 OpenAPI 地址，快速生成 MCP 服务（streamable-http）。创建后返回 MCP 地址，可用 MCP 客户端（如 Claude Desktop）连接。
        </p>
      </div>

      {items.length === 0 ? (
        <div className="empty">暂无 MCP 服务</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>名称</th>
              <th>端口</th>
              <th>MCP 地址</th>
              <th>OpenAPI 源</th>
              <th>启动时间</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((s) => (
              <tr key={s.name}>
                <td>{s.name}</td>
                <td>{s.port}</td>
                <td>
                  <code>{s.mcp_url}</code>{" "}
                  <button onClick={() => void doCopy(s.mcp_url)}>
                    {copiedUrl === s.mcp_url ? "已复制" : "复制"}
                  </button>
                </td>
                <td className="muted">{s.openapi_url}</td>
                <td className="muted">{new Date(s.started_at).toLocaleString()}</td>
                <td><button className="danger" onClick={() => void stop(s.name)}>停止</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
