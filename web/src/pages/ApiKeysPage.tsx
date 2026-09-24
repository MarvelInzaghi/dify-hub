import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { copyText } from "../lib/clipboard";
import type { ApiKey } from "../lib/types";

export default function ApiKeysPage() {
  const [items, setItems] = useState<ApiKey[]>([]);
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState("");
  const [quota, setQuota] = useState("");
  const [newKey, setNewKey] = useState("");
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      setError("");
      setItems(await api.listApiKeys());
    } catch (e) {
      setError(String(e));
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const create = async () => {
    if (!name) return;
    try {
      const created = await api.createApiKey({
        name,
        scopes: scopes ? scopes.split(",").map((s) => s.trim()).filter(Boolean) : undefined,
        quota: quota ? Number(quota) : undefined,
      });
      setNewKey(created.api_key);
      setName("");
      setScopes("");
      setQuota("");
      void load();
    } catch (e) {
      setError(String(e));
    }
  };

  const revoke = async (id: string) => {
    try {
      await api.revokeApiKey(id);
      void load();
    } catch (e) {
      setError(String(e));
    }
  };

  const copyKey = async (text: string) => {
    if (await copyText(text)) {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    }
  };

  return (
    <div>
      <h1>API Keys</h1>
      {error && <div className="error">{error}</div>}
      {newKey && (
        <div className="notice">
          <div>新 API Key（仅显示一次，请立即复制保存）：</div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 6 }}>
            <code style={{ wordBreak: "break-all", flex: 1 }}>{newKey}</code>
            <button onClick={() => void copyKey(newKey)}>{copied ? "已复制" : "复制"}</button>
          </div>
        </div>
      )}

      <div className="card">
        <h2>新建 Key</h2>
        <div className="row">
          <input placeholder="名称" value={name} onChange={(e) => setName(e.target.value)} style={{ width: 160 }} />
          <input placeholder="scope（逗号分隔，留空=全部）" value={scopes} onChange={(e) => setScopes(e.target.value)} style={{ width: 260 }} />
          <input placeholder="配额（-1=不限）" value={quota} onChange={(e) => setQuota(e.target.value)} style={{ width: 120 }} />
          <button className="primary" onClick={() => void create()}>创建</button>
        </div>
      </div>

      <p className="muted" style={{ fontSize: 12, margin: "0 0 12px" }}>
        完整 Key 出于安全只在创建时显示一次（服务端仅保存哈希，无法找回），列表仅显示前缀。
      </p>

      <table>
        <thead>
          <tr>
            <th>名称</th>
            <th>前缀</th>
            <th>scope</th>
            <th>配额</th>
            <th>状态</th>
            <th>最后使用</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {items.map((k) => (
            <tr key={k.id}>
              <td>{k.name}</td>
              <td className="muted">{k.key_prefix}…</td>
              <td>{k.scopes.join(", ")}</td>
              <td>{k.quota < 0 ? "不限" : k.quota}</td>
              <td>{k.status === "active" ? <span className="badge ok">active</span> : <span className="badge muted">revoked</span>}</td>
              <td className="muted">{k.last_used_at ? new Date(k.last_used_at).toLocaleString() : "-"}</td>
              <td>{k.status === "active" && <button className="danger" onClick={() => void revoke(k.id)}>吊销</button>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
