interface Param {
  name: string;
  type: string;
  desc: string;
}

interface Endpoint {
  method: string;
  path: string;
  desc: string;
  params?: Param[];
  response?: string;
}

interface Group {
  title: string;
  endpoints: Endpoint[];
}

const GROUPS: Group[] = [
  {
    title: "提示词库",
    endpoints: [
      {
        method: "GET",
        path: "/api/prompts",
        desc: "分页列出提示词，支持关键词搜索与标签过滤。",
        params: [
          { name: "page", type: "int", desc: "页码，默认 1" },
          { name: "limit", type: "int", desc: "每页数量，默认 20" },
          { name: "keyword", type: "string", desc: "按名称/显示名模糊搜索" },
          { name: "tags", type: "string[]", desc: "标签过滤，可传多个" },
        ],
        response: "{ data: PromptOut[], page, limit, total }",
      },
      {
        method: "GET",
        path: "/api/prompts/{id}",
        desc: "获取单个提示词详情。",
        response: "PromptOut：id、name、display_name、description、mode、content、variables、tags 等",
      },
      {
        method: "GET",
        path: "/api/prompts/{id}/versions",
        desc: "获取提示词的版本历史（倒序）。",
        response: "PromptVersionOut[]：version_number、content、variables、changelog、dify_app_id 等",
      },
      {
        method: "GET",
        path: "/api/prompts/{id}/versions/{version_id}",
        desc: "获取指定版本的详情。",
        response: "PromptVersionOut",
      },
      {
        method: "GET",
        path: "/api/prompts/{id}/variables",
        desc: "从提示词内容中提取的变量名列表。",
        response: "{ data: string[] }",
      },
    ],
  },
  {
    title: "技能库",
    endpoints: [
      {
        method: "GET",
        path: "/api/skills",
        desc: "分页列出技能，支持关键词搜索与分类过滤（列表与 Dify 自动同步）。",
        params: [
          { name: "page", type: "int", desc: "页码，默认 1" },
          { name: "limit", type: "int", desc: "每页数量，默认 20" },
          { name: "keyword", type: "string", desc: "按名称/显示名模糊搜索" },
          { name: "category", type: "string", desc: "按分类过滤" },
        ],
        response: "{ data: SkillOut[], page, limit, total }",
      },
      {
        method: "GET",
        path: "/api/skills/{id}",
        desc: "获取技能详情（含草稿文件列表与最新发布版本信息）。",
        response: "SkillDetailOut：id、dify_skill_id、name、display_name、category、tags、files、latest_published_version_number 等",
      },
      {
        method: "GET",
        path: "/api/skills/{id}/versions",
        desc: "获取技能的版本历史。",
        response: "{ data: SkillVersion[] }",
      },
    ],
  },
];

export default function DocsPage() {
  return (
    <div>
      <h1>接口文档</h1>
      <p className="muted" style={{ fontSize: 12, marginBottom: 12 }}>
        以下为读取提示词库与技能库的接口。所有接口均返回 JSON，基础地址为当前站点同源（如{" "}
        <code>http://localhost:18100</code>）。
      </p>

      {GROUPS.map((g) => (
        <div className="card" key={g.title}>
          <h2>{g.title}</h2>
          {g.endpoints.map((e) => (
            <div key={e.path} style={{ marginBottom: 22 }}>
              <div className="row" style={{ gap: 8, marginBottom: 4 }}>
                <span className="badge ok">{e.method}</span>
                <code>{e.path}</code>
              </div>
              <p className="muted" style={{ margin: "0 0 8px" }}>{e.desc}</p>
              {e.params && e.params.length > 0 && (
                <table style={{ marginBottom: 8 }}>
                  <thead>
                    <tr>
                      <th style={{ width: 140 }}>参数</th>
                      <th style={{ width: 120 }}>类型</th>
                      <th>说明</th>
                    </tr>
                  </thead>
                  <tbody>
                    {e.params.map((p) => (
                      <tr key={p.name}>
                        <td><code>{p.name}</code></td>
                        <td>{p.type}</td>
                        <td>{p.desc}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {e.response && (
                <div className="muted" style={{ fontSize: 12 }}>
                  响应：<code>{e.response}</code>
                </div>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
