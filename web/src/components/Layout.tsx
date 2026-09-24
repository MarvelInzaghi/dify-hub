import { NavLink, Outlet } from "react-router-dom";

const NAV = [
  { to: "/skills", label: "技能库" },
  { to: "/prompts", label: "提示词库" },
  { to: "/mcp", label: "MCP 服务" },
  { to: "/publications", label: "发布" },
  { to: "/api-keys", label: "API Keys" },
  { to: "/docs", label: "接口文档" },
];

export default function Layout() {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">dify-hub</div>
        <nav>
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} className={({ isActive }) => (isActive ? "nav active" : "nav")}>
              {n.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
