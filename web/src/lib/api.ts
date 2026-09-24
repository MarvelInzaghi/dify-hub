import type {
  ApiKey,
  ApiKeyCreate,
  ApiKeyCreated,
  McpServer,
  McpServerCreate,
  Prompt,
  PromptCreate,
  PromptList,
  PromptUpdate,
  PromptVersion,
  Publication,
  PublicationPublish,
  Skill,
  SkillCreate,
  SkillDetail,
  SkillFileOp,
  SkillList,
  SkillVersionList,
} from "./types";

const BASE = ((import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "") + "/api";

// FastAPI validation errors return `detail` as an array of {loc, msg}; other errors
// return a plain string. Render both into a readable message instead of `[object Object]`.
function formatErrorDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === "object") {
          const { loc, msg } = item as { loc?: unknown; msg?: unknown };
          const field = Array.isArray(loc)
            ? loc.filter((seg) => seg !== "body").join(".")
            : "";
          const text = typeof msg === "string" ? msg : JSON.stringify(item);
          return field ? `${field}: ${text}` : text;
        }
        return String(item);
      })
      .join("; ");
  }
  if (detail && typeof detail === "object") {
    try {
      return JSON.stringify(detail);
    } catch {
      return String(detail);
    }
  }
  return String(detail);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (res.status === 204) return undefined as T;
  if (!res.ok) {
    const text = await res.text();
    let message = text;
    try {
      const parsed = JSON.parse(text);
      message = formatErrorDetail(parsed.detail ?? parsed.message ?? text);
    } catch {
      /* not JSON */
    }
    throw new Error(`${res.status}: ${message}`);
  }
  return (await res.json()) as T;
}

async function requestForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "POST", body: form });
  if (!res.ok) {
    const text = await res.text();
    let message = text;
    try {
      const parsed = JSON.parse(text);
      message = formatErrorDetail(parsed.detail ?? parsed.message ?? text);
    } catch {
      /* not JSON */
    }
    throw new Error(`${res.status}: ${message}`);
  }
  return (await res.json()) as T;
}

export const api = {
  // --- Prompts ---
  listPrompts(params?: { page?: number; limit?: number; keyword?: string; tags?: string[] }): Promise<PromptList> {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.keyword) q.set("keyword", params.keyword);
    if (params?.tags?.length) {
      for (const t of params.tags) q.append("tags", t);
    }
    const qs = q.toString();
    return request<PromptList>(`/prompts${qs ? `?${qs}` : ""}`);
  },
  getPrompt(id: string): Promise<Prompt> {
    return request<Prompt>(`/prompts/${id}`);
  },
  createPrompt(body: PromptCreate): Promise<Prompt> {
    return request<Prompt>("/prompts", { method: "POST", body: JSON.stringify(body) });
  },
  updatePrompt(id: string, body: PromptUpdate): Promise<Prompt> {
    return request<Prompt>(`/prompts/${id}`, { method: "PATCH", body: JSON.stringify(body) });
  },
  deletePrompt(id: string): Promise<void> {
    return request<void>(`/prompts/${id}`, { method: "DELETE" });
  },
  listPromptVersions(id: string): Promise<PromptVersion[]> {
    return request<PromptVersion[]>(`/prompts/${id}/versions`);
  },
  restorePrompt(id: string, versionId: string): Promise<Prompt> {
    return request<Prompt>(`/prompts/${id}/restore`, {
      method: "POST",
      body: JSON.stringify({ version_id: versionId }),
    });
  },
  previewPrompt(id: string, values: Record<string, string>): Promise<{ rendered: string }> {
    return request<{ rendered: string }>(`/prompts/${id}/preview`, {
      method: "POST",
      body: JSON.stringify({ values }),
    });
  },

  // --- Skills ---
  listSkills(params?: { page?: number; limit?: number; keyword?: string; category?: string }): Promise<SkillList> {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    q.set("limit", String(params?.limit ?? 20));
    if (params?.keyword) q.set("keyword", params.keyword);
    if (params?.category) q.set("category", params.category);
    return request<SkillList>(`/skills?${q.toString()}`);
  },
  getSkill(id: string): Promise<SkillDetail> {
    return request<SkillDetail>(`/skills/${id}`);
  },
  createSkill(body: SkillCreate): Promise<Skill> {
    return request<Skill>("/skills", { method: "POST", body: JSON.stringify(body) });
  },
  importSkill(file: File): Promise<Skill> {
    const form = new FormData();
    form.append("file", file);
    return requestForm<Skill>("/skills/import", form);
  },
  exportSkillUrl(id: string): string {
    return `${BASE}/skills/${id}/export`;
  },
  deleteSkill(id: string): Promise<void> {
    return request<void>(`/skills/${id}`, { method: "DELETE" });
  },
  upsertSkillFile(id: string, path: string, content: string): Promise<unknown> {
    return request<unknown>(`/skills/${id}/files`, {
      method: "PUT",
      body: JSON.stringify({ path, content }),
    });
  },
  publishSkill(id: string, changelog?: string, versionName?: string): Promise<unknown> {
    return request<unknown>(`/skills/${id}/publish`, {
      method: "POST",
      body: JSON.stringify({ changelog: changelog ?? "", version_name: versionName ?? null }),
    });
  },
  listSkillVersions(id: string): Promise<SkillVersionList> {
    return request<SkillVersionList>(`/skills/${id}/versions`);
  },
  skillFileOp(id: string, op: SkillFileOp): Promise<unknown> {
    return request<unknown>(`/skills/${id}/file-op`, { method: "POST", body: JSON.stringify(op) });
  },

  // --- Publications ---
  listPublications(): Promise<Publication[]> {
    return request<Publication[]>("/publications");
  },
  publishPrompt(body: PublicationPublish): Promise<Publication> {
    return request<Publication>("/publications", { method: "POST", body: JSON.stringify(body) });
  },

  // --- API keys ---
  listApiKeys(): Promise<ApiKey[]> {
    return request<ApiKey[]>("/api-keys");
  },
  createApiKey(body: ApiKeyCreate): Promise<ApiKeyCreated> {
    return request<ApiKeyCreated>("/api-keys", { method: "POST", body: JSON.stringify(body) });
  },
  revokeApiKey(id: string): Promise<void> {
    return request<void>(`/api-keys/${id}/revoke`, { method: "POST" });
  },

  // --- MCP services ---
  listMcpServers(): Promise<McpServer[]> {
    return request<McpServer[]>("/mcp/servers");
  },
  createMcpServer(body: McpServerCreate): Promise<McpServer> {
    return request<McpServer>("/mcp/servers", { method: "POST", body: JSON.stringify(body) });
  },
  deleteMcpServer(name: string): Promise<void> {
    return request<void>(`/mcp/servers/${name}`, { method: "DELETE" });
  },
};
