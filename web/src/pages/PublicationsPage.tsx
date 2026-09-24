import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { copyText } from "../lib/clipboard";
import type { Publication } from "../lib/types";

function buildUrl(slug: string): string {
  return `${window.location.origin}/v1/run/${slug}`;
}

function buildCurl(p: Publication): string {
  const inputs: Record<string, string> = {};
  for (const v of p.variable_schema ?? []) {
    inputs[v.name] = v.default ?? "值";
  }
  const body: Record<string, unknown> = { inputs, response_mode: "blocking" };
  if (p.mode === "chat") body.query = "你的问题";
  const data = JSON.stringify(body);
  return [
    `curl -X POST '${buildUrl(p.slug)}'`,
    `  -H 'Authorization: Bearer 你的API_Key'`,
    `  -H 'Content-Type: application/json'`,
    `  -d '${data}'`,
  ].join(" \\\n");
}

export default function PublicationsPage() {
  const [items, setItems] = useState<Publication[]>([]);
  const [error, setError] = useState("");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const load = async () => {
    try {
      setError("");
      setItems(await api.listPublications());
    } catch (e) {
      setError(String(e));
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const doCopy = async (key: string, text: string) => {
    if (await copyText(text)) {
      setCopiedKey(key);
      window.setTimeout(() => setCopiedKey((cur) => (cur === key ? null : cur)), 1500);
    }
  };

  return (
    <div>
      <h1>发布</h1>
      {error && <div className="error">{error}</div>}
      <p className="muted" style={{ fontSize: 12, marginBottom: 12 }}>
        每个发布对应一个公开运行地址 <code>POST /v1/run/&lt;slug&gt;</code>。调用时需携带 API Key（请求头{" "}
        <code>Authorization: Bearer &lt;key&gt;</code>），Key 请在「API Keys」页创建。
      </p>

      <table>
        <thead>
          <tr>
            <th>slug</th>
            <th>名称</th>
            <th>模式</th>
            <th>状态</th>
            <th>访问地址</th>
            <th>使用方式</th>
            <th>更新时间</th>
          </tr>
        </thead>
        <tbody>
          {items.map((p) => {
            const url = buildUrl(p.slug);
            const curl = buildCurl(p);
            return (
              <tr key={p.id}>
                <td><code>{p.slug}</code></td>
                <td>{p.name}</td>
                <td><span className="badge muted">{p.mode}</span></td>
                <td><span className="badge ok">{p.status}</span></td>
                <td>
                  <code>{url}</code>{" "}
                  <button onClick={() => void doCopy(`${p.id}-url`, url)}>
                    {copiedKey === `${p.id}-url` ? "已复制" : "复制"}
                  </button>
                </td>
                <td>
                  <button className="primary" onClick={() => void doCopy(`${p.id}-curl`, curl)}>
                    {copiedKey === `${p.id}-curl` ? "已复制" : "复制 curl"}
                  </button>
                </td>
                <td className="muted">{new Date(p.updated_at).toLocaleString()}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
