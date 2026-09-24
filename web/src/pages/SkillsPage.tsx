import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { slugify } from "../lib/slug";
import type { Skill } from "../lib/types";
import { Empty, ErrorBox, Loading, Pagination } from "../components/Feedback";

const LIMIT = 20;

export default function SkillsPage() {
  const [items, setItems] = useState<Skill[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState("");
  const [category, setCategory] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [newCategory, setNewCategory] = useState("");
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = async (p: number, kw: string, cat: string) => {
    setLoading(true);
    try {
      setError("");
      const res = await api.listSkills({ page: p, limit: LIMIT, keyword: kw || undefined, category: cat || undefined });
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
    try {
      const slug = slugify(name);
      await api.createSkill({ name: slug || undefined, display_name: displayName, category: newCategory || undefined });
      setName("");
      setDisplayName("");
      setNewCategory("");
      void load(page, keyword, category);
    } catch (e) {
      setError(String(e));
    }
  };

  const remove = async (id: string) => {
    if (!confirm("确认删除该技能？")) return;
    try {
      await api.deleteSkill(id);
      void load(page, keyword, category);
    } catch (e) {
      setError(String(e));
    }
  };

  const doImport = async () => {
    if (!importFile) return;
    setImporting(true);
    try {
      setError("");
      await api.importSkill(importFile);
      setImportFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      void load(page, keyword, category);
    } catch (e) {
      setError(String(e));
    } finally {
      setImporting(false);
    }
  };

  return (
    <div>
      <h1>技能库</h1>
      <ErrorBox error={error} />

      <div className="toolbar">
        <input
          placeholder="搜索名称"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void load(1, e.currentTarget.value, category)}
          style={{ width: 200 }}
        />
        <input
          placeholder="分类筛选"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void load(1, keyword, e.currentTarget.value)}
          style={{ width: 140 }}
        />
        <button onClick={() => void load(1, keyword, category)}>搜索</button>
      </div>

      <div className="card">
        <h2>创建 / 导入技能</h2>
        <div className="grid2">
          <div>
            <h3>新建</h3>
            <div className="field">
              <input placeholder="标识（英文，留空自动生成）" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="field">
              <input placeholder="显示名（必填）" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
            </div>
            <div className="field">
              <input placeholder="分类" value={newCategory} onChange={(e) => setNewCategory(e.target.value)} />
            </div>
            <button className="primary" onClick={() => void create()}>创建</button>
            <p className="muted" style={{ margin: "8px 0 0", fontSize: 12 }}>
              标识（slug）是唯一英文名称，用于系统内区分；仅支持小写字母/数字/-/_，留空会由系统自动生成。
            </p>
          </div>
          <div style={{ borderLeft: "1px solid var(--border)", paddingLeft: 20 }}>
            <h3>导入</h3>
            <div className="field">
              <input ref={fileInputRef} type="file" accept=".zip" onChange={(e) => setImportFile(e.target.files?.[0] ?? null)} />
            </div>
            <button className="primary" onClick={() => void doImport()} disabled={!importFile || importing}>
              {importing ? "导入中…" : "导入 zip"}
            </button>
            <p className="muted" style={{ margin: "8px 0 0", fontSize: 12 }}>
              上传技能包（zip，需含 SKILL.md），可从 Dify 导出。
            </p>
          </div>
        </div>
      </div>

      {loading ? (
        <Loading />
      ) : items.length === 0 ? (
        <Empty text="暂无技能" />
      ) : (
        <>
          <table>
            <thead>
              <tr>
                <th>名称</th>
                <th>显示名</th>
                <th>分类</th>
                <th>更新时间</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((s) => (
                <tr key={s.id}>
                  <td><Link to={`/skills/${s.id}`}>{s.name}</Link></td>
                  <td>{s.display_name}</td>
                  <td>{s.category ? <span className="badge muted">{s.category}</span> : "-"}</td>
                  <td className="muted">{new Date(s.updated_at).toLocaleString()}</td>
                  <td><button className="danger" onClick={() => void remove(s.id)}>删除</button></td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination page={page} total={total} limit={LIMIT} onChange={(p) => void load(p, keyword, category)} />
        </>
      )}
    </div>
  );
}
