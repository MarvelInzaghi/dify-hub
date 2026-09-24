import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import type { Prompt, PromptVersion, VariableSchema, VariableType } from "../lib/types";
import { ErrorBox } from "../components/Feedback";

const VAR_SPLIT_RE = /\{\{[a-zA-Z_][a-zA-Z0-9_]{0,29}\}\}/;
const VAR_GLOBAL_RE = /\{\{([a-zA-Z_][a-zA-Z0-9_]{0,29})\}\}/g;

function extractVars(content: string): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const m of content.matchAll(VAR_GLOBAL_RE)) {
    if (!seen.has(m[1])) {
      seen.add(m[1]);
      out.push(m[1]);
    }
  }
  return out;
}

function renderHighlighted(content: string) {
  return content.split(VAR_SPLIT_RE).map((part, i) =>
    VAR_SPLIT_RE.test(part) ? (
      <mark key={i} className="mark">
        {part}
      </mark>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

export default function PromptEditorPage() {
  const { id } = useParams<{ id: string }>();
  const [prompt, setPrompt] = useState<Prompt | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [description, setDescription] = useState("");
  const [mode, setMode] = useState<"completion" | "chat">("completion");
  const [content, setContent] = useState("");
  const [variables, setVariables] = useState<VariableSchema[]>([]);
  const [tags, setTags] = useState("");
  const [slug, setSlug] = useState("");
  const [changelog, setChangelog] = useState("");
  const [versions, setVersions] = useState<PromptVersion[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [publishedSlug, setPublishedSlug] = useState("");

  const load = async () => {
    if (!id) return;
    try {
      setError("");
      const p = await api.getPrompt(id);
      setPrompt(p);
      setDisplayName(p.display_name);
      setDescription(p.description);
      setMode(p.mode === "chat" ? "chat" : "completion");
      setContent(p.content);
      setVariables(p.variables ?? []);
      setTags((p.tags ?? []).join(", "));
      setSlug(p.name);
      setVersions(await api.listPromptVersions(id));
    } catch (e) {
      setError(String(e));
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Auto-add newly referenced variables when content changes.
  useEffect(() => {
    const names = extractVars(content);
    setVariables((prev) => {
      const existing = new Set(prev.map((v) => v.name));
      const added = names
        .filter((n) => !existing.has(n))
        .map((n) => ({ name: n, type: "string" as const, required: false, default: null, label: null, description: null }));
      return added.length ? [...prev, ...added] : prev;
    });
  }, [content]);

  const extracted = extractVars(content);

  const save = async () => {
    try {
      setError("");
      await api.updatePrompt(id!, {
        display_name: displayName,
        description,
        mode,
        content,
        variables,
        tags: tags.split(",").map((s) => s.trim()).filter(Boolean),
      });
      setNotice("已保存");
    } catch (e) {
      setError(String(e));
    }
  };

  const publish = async () => {
    try {
      setError("");
      const pub = await api.publishPrompt({ prompt_id: id!, slug: slug || prompt!.name, changelog });
      setPublishedSlug(pub.slug);
      setNotice(`已发布到 slug: ${pub.slug}`);
      setVersions(await api.listPromptVersions(id!));
    } catch (e) {
      setError(String(e));
    }
  };

  const restore = async (versionId: string) => {
    if (!confirm("回滚到该版本？将用该版本内容覆盖当前草稿。")) return;
    try {
      setError("");
      const p = await api.restorePrompt(id!, versionId);
      setContent(p.content);
      setVariables(p.variables ?? []);
      setNotice("已回滚（当前为草稿，需重新发布才生效）");
    } catch (e) {
      setError(String(e));
    }
  };

  const updateVar = (name: string, patch: Partial<VariableSchema>) => {
    setVariables((prev) => prev.map((v) => (v.name === name ? { ...v, ...patch } : v)));
  };

  if (!prompt) return <div className="muted">加载中…</div>;

  return (
    <div>
      <div className="toolbar">
        <Link to="/prompts">← 返回</Link>
        <h1 style={{ margin: 0 }}>{prompt.name}</h1>
      </div>
      <ErrorBox error={error} />
      {notice && <div className="notice">{notice}</div>}

      <div className="card">
        <div className="row" style={{ alignItems: "flex-end" }}>
          <div className="field" style={{ flex: 1 }}>
            <label>显示名</label>
            <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label>描述</label>
            <input value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <div className="field">
            <label>模式</label>
            <select value={mode} onChange={(e) => setMode(e.target.value as "completion" | "chat")} style={{ width: 140 }}>
              <option value="completion">completion</option>
              <option value="chat">chat</option>
            </select>
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label>标签（逗号分隔）</label>
            <input value={tags} onChange={(e) => setTags(e.target.value)} />
          </div>
          <button className="primary" onClick={() => void save()}>保存</button>
        </div>
      </div>

      <div className="grid2">
        <div className="card">
          <h2>内容（用 {"{{变量名}}"} 引用变量）</h2>
          <textarea value={content} onChange={(e) => setContent(e.target.value)} style={{ minHeight: 280 }} />
        </div>
        <div className="card">
          <h2>实时预览</h2>
          <div className="preview">{renderHighlighted(content)}</div>
        </div>
      </div>

      <div className="card">
        <h2>变量</h2>
        {extracted.length === 0 && <div className="muted">暂无变量</div>}
        {extracted.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>变量</th>
                <th>类型</th>
                <th>必填</th>
                <th>默认值</th>
                <th>标签</th>
                <th>描述</th>
              </tr>
            </thead>
            <tbody>
              {extracted.map((name) => {
                const v = variables.find((x) => x.name === name) ?? {
                  name,
                  type: "string" as VariableType,
                  required: false,
                  default: null,
                  label: null,
                  description: null,
                };
                return (
                  <tr key={name}>
                    <td><span className="mark">{`{{${name}}}`}</span></td>
                    <td>
                      <select
                        value={v.type}
                        onChange={(e) => updateVar(name, { type: e.target.value as VariableType })}
                        style={{ width: 100 }}
                      >
                        <option value="string">string</option>
                        <option value="number">number</option>
                        <option value="boolean">boolean</option>
                      </select>
                    </td>
                    <td>
                      <input type="checkbox" checked={!!v.required} onChange={(e) => updateVar(name, { required: e.target.checked })} />
                    </td>
                    <td><input value={v.default ?? ""} onChange={(e) => updateVar(name, { default: e.target.value })} style={{ width: 100 }} /></td>
                    <td><input value={v.label ?? ""} onChange={(e) => updateVar(name, { label: e.target.value })} /></td>
                    <td><input value={v.description ?? ""} onChange={(e) => updateVar(name, { description: e.target.value })} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <h2>发布</h2>
        <div className="row" style={{ alignItems: "flex-end" }}>
          <div className="field" style={{ width: 260 }}>
            <label>slug（对外标识）</label>
            <input value={slug} onChange={(e) => setSlug(e.target.value)} />
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label>发布说明</label>
            <input value={changelog} onChange={(e) => setChangelog(e.target.value)} />
          </div>
          <button className="primary" onClick={() => void publish()}>发布</button>
        </div>
        {publishedSlug && (
          <div className="notice" style={{ marginTop: 10 }}>
            已发布：<code>{publishedSlug}</code> —— 外部通过 <code>POST /v1/run/{publishedSlug}</code> 调用
          </div>
        )}
      </div>

      <div className="card">
        <h2>版本历史</h2>
        {versions.length === 0 && <div className="muted">暂无版本</div>}
        {versions.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>版本</th>
                <th>发布说明</th>
                <th>时间</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {versions.map((v) => (
                <tr key={v.id}>
                  <td>v{v.version_number}</td>
                  <td>{v.changelog || "-"}</td>
                  <td className="muted">{new Date(v.created_at).toLocaleString()}</td>
                  <td><button onClick={() => void restore(v.id)}>回滚到此版本</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
