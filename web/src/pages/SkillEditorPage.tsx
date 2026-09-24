import { useEffect, useState } from "react";
import type { ReactElement } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import type { SkillDetail, SkillFile, SkillVersion } from "../lib/types";
import { ErrorBox } from "../components/Feedback";

interface TreeNode {
  name: string;
  path: string;
  kind: "directory" | "file";
  children: TreeNode[];
  file?: SkillFile;
}

function buildTree(files: SkillFile[]): TreeNode[] {
  const root: TreeNode[] = [];
  const dirMap = new Map<string, TreeNode>();
  const sorted = [...files].sort((a, b) => a.path.localeCompare(b.path));

  for (const f of sorted) {
    const parts = f.path.split("/").filter(Boolean);
    let parentChildren = root;
    let currentPath = "";
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      currentPath = currentPath ? `${currentPath}/${part}` : part;
      const isLast = i === parts.length - 1;
      if (isLast && f.kind !== "directory") {
        parentChildren.push({ name: part, path: f.path, kind: "file", children: [], file: f });
      } else {
        let dir = dirMap.get(currentPath);
        if (!dir) {
          dir = { name: part, path: currentPath, kind: "directory", children: [] };
          dirMap.set(currentPath, dir);
          parentChildren.push(dir);
        }
        parentChildren = dir.children;
      }
    }
  }

  const sortNodes = (nodes: TreeNode[]): void => {
    nodes.sort((a, b) => {
      if (a.kind !== b.kind) return a.kind === "directory" ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
    nodes.forEach((n) => sortNodes(n.children));
  };
  sortNodes(root);
  return root;
}

function collectDirs(nodes: TreeNode[]): string[] {
  const result: string[] = [];
  for (const n of nodes) {
    if (n.kind === "directory") {
      result.push(n.path);
      result.push(...collectDirs(n.children));
    }
  }
  return result;
}

export default function SkillEditorPage() {
  const { id } = useParams<{ id: string }>();
  const [skill, setSkill] = useState<SkillDetail | null>(null);
  const [files, setFiles] = useState<SkillFile[]>([]);
  const [activePath, setActivePath] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [newPath, setNewPath] = useState("");
  const [changelog, setChangelog] = useState("");
  const [versionName, setVersionName] = useState("");
  const [versions, setVersions] = useState<SkillVersion[]>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const tree = buildTree(files);

  const load = async (preferPath?: string) => {
    if (!id) return;
    try {
      setError("");
      const detail = await api.getSkill(id);
      setSkill(detail);
      const fs = detail.files ?? [];
      setFiles(fs);
      setExpanded(new Set(collectDirs(buildTree(fs))));
      const target = preferPath ?? "SKILL.md";
      const f = fs.find((x) => x.path === target) ?? fs.find((x) => x.kind !== "directory");
      setActivePath(f ? f.path : null);
      setContent(f ? f.content ?? "" : "");
      setVersions((await api.listSkillVersions(id)).data ?? []);
    } catch (e) {
      setError(String(e));
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const open = (f: SkillFile) => {
    if (f.kind === "directory") return;
    setActivePath(f.path);
    setContent(f.content ?? "");
  };

  const toggleDir = (path: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const activeFile = files.find((f) => f.path === activePath);
  const isBinary = !!activeFile && activeFile.content == null && !!activeFile.tool_file_id;

  const save = async () => {
    if (!activePath) return;
    try {
      setError("");
      await api.upsertSkillFile(id!, activePath, content);
      setNotice("已保存");
      void load(activePath);
    } catch (e) {
      setError(String(e));
    }
  };

  const createFile = async () => {
    if (!newPath) return;
    try {
      setError("");
      await api.upsertSkillFile(id!, newPath, "");
      setNewPath("");
      setNotice("已创建文件");
      void load(newPath);
    } catch (e) {
      setError(String(e));
    }
  };

  const removeFile = async (path: string) => {
    if (!confirm(`删除文件 ${path}？`)) return;
    try {
      setError("");
      await api.skillFileOp(id!, { operation: "delete", path });
      void load();
    } catch (e) {
      setError(String(e));
    }
  };

  const renameFile = async (path: string) => {
    const target = prompt("重命名为：", path);
    if (!target || target === path) return;
    try {
      setError("");
      await api.skillFileOp(id!, { operation: "rename", path, target_path: target });
      void load(target);
    } catch (e) {
      setError(String(e));
    }
  };

  const renderNode = (node: TreeNode, depth: number): ReactElement => {
    const pad = 8 + depth * 16;
    if (node.kind === "directory") {
      const isOpen = expanded.has(node.path);
      return (
        <div key={node.path}>
          <div className="file-node folder" style={{ paddingLeft: pad }} onClick={() => toggleDir(node.path)}>
            <span className="caret">{isOpen ? "▾" : "▸"}</span>
            <span className="icon">📁</span>
            <span className="name">{node.name}</span>
          </div>
          {isOpen && node.children.map((c) => renderNode(c, depth + 1))}
        </div>
      );
    }
    const f = node.file!;
    return (
      <div
        key={node.path}
        className={`file-node file ${node.path === activePath ? "active" : ""}`}
        style={{ paddingLeft: pad + 22 }}
        onClick={() => open(f)}
      >
        <span className="icon">📄</span>
        <span className="name">{node.name}</span>
        <span className="actions" onClick={(e) => e.stopPropagation()}>
          <button onClick={() => void renameFile(f.path)}>改名</button>
          <button className="danger" onClick={() => void removeFile(f.path)}>删</button>
        </span>
      </div>
    );
  };

  const publish = async () => {
    try {
      setError("");
      await api.publishSkill(id!, changelog, versionName || undefined);
      setNotice("已发布");
      setChangelog("");
      setVersionName("");
      void load();
    } catch (e) {
      setError(String(e));
    }
  };

  if (!skill) return <div className="muted">加载中…</div>;

  return (
    <div>
      <div className="toolbar">
        <Link to="/skills">← 返回</Link>
        <h1 style={{ margin: 0 }}>{skill.display_name}</h1>
        <span className="badge muted">{skill.name}</span>
        <button className="primary" onClick={() => (window.location.href = api.exportSkillUrl(id!))}>
          下载技能包
        </button>
      </div>
      <ErrorBox error={error} />
      {notice && <div className="notice">{notice}</div>}

      <div className="row" style={{ alignItems: "flex-end", marginBottom: 16 }}>
        <div className="field" style={{ width: 280, marginBottom: 0 }}>
          <label>新建文件（路径，如 scripts/run.py）</label>
          <input value={newPath} onChange={(e) => setNewPath(e.target.value)} placeholder="scripts/run.py" />
        </div>
        <button className="primary" onClick={() => void createFile()}>新建</button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: 16, alignItems: "start" }}>
        <div className="file-tree">
          {tree.length === 0 && <div className="empty">暂无文件</div>}
          {tree.map((n) => renderNode(n, 0))}
        </div>

        <div className="card" style={{ margin: 0 }}>
          <h2>{activePath ?? "未选择文件"}</h2>
          {isBinary ? (
            <div className="muted">二进制文件，不支持在线编辑。</div>
          ) : activePath ? (
            <>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                style={{ minHeight: 520, fontFamily: "ui-monospace, Menlo, Consolas, monospace" }}
              />
              <div style={{ marginTop: 10 }}>
                <button className="primary" onClick={() => void save()}>保存</button>
              </div>
            </>
          ) : (
            <div className="muted">在左侧选择文件</div>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h2>发布</h2>
        <div className="row" style={{ alignItems: "flex-end" }}>
          <div className="field" style={{ flex: 1, marginBottom: 0 }}>
            <label>版本名（可选）</label>
            <input value={versionName} onChange={(e) => setVersionName(e.target.value)} />
          </div>
          <div className="field" style={{ flex: 2, marginBottom: 0 }}>
            <label>发布说明</label>
            <input value={changelog} onChange={(e) => setChangelog(e.target.value)} />
          </div>
          <button className="primary" onClick={() => void publish()}>发布</button>
        </div>
      </div>

      <div className="card">
        <h2>版本历史</h2>
        {versions.length === 0 && <div className="muted">暂无已发布版本</div>}
        {versions.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>版本</th>
                <th>版本名</th>
                <th>发布说明</th>
                <th>时间</th>
              </tr>
            </thead>
            <tbody>
              {versions.map((v) => (
                <tr key={v.id}>
                  <td>
                    v{v.version_number} {v.is_latest && <span className="badge ok">latest</span>}
                  </td>
                  <td>{v.version_name || "-"}</td>
                  <td>{v.publish_note || "-"}</td>
                  <td className="muted">{new Date(v.created_at * 1000).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
