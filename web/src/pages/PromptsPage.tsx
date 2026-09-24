import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { generateSlug, slugify } from "../lib/slug";
import type { Prompt } from "../lib/types";
import { Empty, ErrorBox, Loading, Pagination } from "../components/Feedback";

const LIMIT = 20;

export default function PromptsPage() {
  const [items, setItems] = useState<Prompt[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState("");
  const [tags, setTags] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [mode, setMode] = useState<"completion" | "chat">("completion");
  const navigate = useNavigate();

  const load = async (p: number, kw: string, tg: string) => {
    setLoading(true);
    try {
      setError("");
      const res = await api.listPrompts({
        page: p,
        limit: LIMIT,
        keyword: kw || undefined,
        tags: tg ? tg.split(",").map((s) => s.trim()).filter(Boolean) : undefined,
      });
      setItems(res.data);
      setTotal(res.total);
      setPage(res.page);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load(1, "", "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const create = async () => {
    if (!displayName) return;
    // 标识留空或仅含中文时自动生成合法 slug，避免 422。
    const slug = slugify(name) || generateSlug(displayName);
    try {
      const p = await api.createPrompt({ name: slug, display_name: displayName, mode });
      navigate(`/prompts/${p.id}`);
    } catch (e) {
      setError(String(e));
    }
  };

  const remove = async (id: string) => {
    if (!confirm("确认删除该提示词（含版本历史）？")) return;
    try {
      await api.deletePrompt(id);
      void load(page, keyword, tags);
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div>
      <h1>提示词库</h1>
      <ErrorBox error={error} />

      <div className="toolbar">
        <input
          placeholder="搜索名称/描述"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void load(1, e.currentTarget.value, tags)}
          style={{ width: 220 }}
        />
        <input
          placeholder="标签筛选（逗号分隔）"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void load(1, keyword, e.currentTarget.value)}
          style={{ width: 180 }}
        />
        <button onClick={() => void load(1, keyword, tags)}>搜索</button>
      </div>

      <div className="card">
        <h2>新建提示词</h2>
        <div className="row">
          <input placeholder="标识（英文，留空自动生成）" value={name} onChange={(e) => setName(e.target.value)} style={{ width: 260 }} />
          <input placeholder="显示名（必填）" value={displayName} onChange={(e) => setDisplayName(e.target.value)} style={{ width: 260 }} />
          <select value={mode} onChange={(e) => setMode(e.target.value as "completion" | "chat")} style={{ width: 140 }}>
            <option value="completion">completion</option>
            <option value="chat">chat</option>
          </select>
          <button className="primary" onClick={() => void create()}>创建</button>
        </div>
        <p className="muted" style={{ margin: "8px 0 0", fontSize: 12 }}>
          标识（slug）是唯一英文名称，用于系统内区分与 API 引用；仅支持小写字母/数字/-/_，留空会根据显示名自动生成。
        </p>
      </div>

      {loading ? (
        <Loading />
      ) : items.length === 0 ? (
        <Empty text="暂无提示词" />
      ) : (
        <>
          <table>
            <thead>
              <tr>
                <th>名称</th>
                <th>显示名</th>
                <th>模式</th>
                <th>标签</th>
                <th>状态</th>
                <th>更新时间</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.id}>
                  <td><Link to={`/prompts/${p.id}`}>{p.name}</Link></td>
                  <td>{p.display_name}</td>
                  <td><span className="badge muted">{p.mode}</span></td>
                  <td>
                    <span className="badges">
                      {p.tags?.length ? p.tags.map((t) => <span key={t} className="badge">{t}</span>) : "-"}
                    </span>
                  </td>
                  <td>
                    {p.latest_published_version_id ? <span className="badge ok">已发布</span> : <span className="badge warn">草稿</span>}
                  </td>
                  <td className="muted">{new Date(p.updated_at).toLocaleString()}</td>
                  <td><button className="danger" onClick={() => void remove(p.id)}>删除</button></td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination page={page} total={total} limit={LIMIT} onChange={(p) => void load(p, keyword, tags)} />
        </>
      )}
    </div>
  );
}
