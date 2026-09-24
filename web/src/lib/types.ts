export type VariableType = "string" | "number" | "boolean";

export interface VariableSchema {
  name: string;
  label?: string | null;
  type: VariableType;
  description?: string | null;
  required: boolean;
  default?: string | null;
}

export interface Prompt {
  id: string;
  name: string;
  display_name: string;
  description: string;
  mode: string;
  content: string;
  variables: VariableSchema[];
  tags: string[];
  latest_published_version_id: string | null;
  dify_app_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface PromptList {
  data: Prompt[];
  page: number;
  limit: number;
  total: number;
}

export interface PromptVersion {
  id: string;
  prompt_id: string;
  version_number: number;
  content: string;
  variables: VariableSchema[];
  changelog: string;
  dify_app_id: string | null;
  created_at: string;
}

export interface Skill {
  id: string;
  dify_skill_id: string;
  name: string;
  display_name: string;
  description: string;
  category: string | null;
  tags: string[];
  latest_dify_skill_version_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Publication {
  id: string;
  slug: string;
  name: string;
  item_type: string;
  item_id: string;
  pinned_version_id: string | null;
  mode: string;
  dify_app_id: string | null;
  variable_schema: VariableSchema[];
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  quota: number;
  status: string;
  created_at: string;
  last_used_at: string | null;
}

export interface ApiKeyCreated extends ApiKey {
  api_key: string;
}

export interface PromptCreate {
  name: string;
  display_name: string;
  description?: string;
  mode?: "completion" | "chat";
  content?: string;
  variables?: VariableSchema[];
}

export interface PromptUpdate {
  display_name?: string;
  description?: string;
  mode?: "completion" | "chat";
  content?: string;
  variables?: VariableSchema[];
  tags?: string[];
}

export interface SkillCreate {
  name?: string;
  display_name: string;
  description?: string;
  category?: string;
  tags?: string[];
}

export interface PublicationPublish {
  prompt_id: string;
  slug: string;
  changelog?: string;
}

export interface ApiKeyCreate {
  name: string;
  scopes?: string[];
  quota?: number;
}

export interface SkillFile {
  id?: string | null;
  path: string;
  kind?: string;
  storage?: string | null;
  mime_type?: string | null;
  content?: string | null;
  tool_file_id?: string | null;
  size?: number | null;
  hash?: string | null;
}

export interface SkillDetail extends Skill {
  files: SkillFile[];
  latest_published_version_number?: number | null;
  latest_published_at?: number | null;
}

export interface SkillVersion {
  id: string;
  skill_id: string;
  version_number: number;
  version_name: string;
  publish_note: string;
  is_latest?: boolean;
  created_at: number; // Dify returns epoch seconds
}

export interface SkillVersionList {
  data: SkillVersion[];
}

export interface SkillList {
  data: Skill[];
  page: number;
  limit: number;
  total: number;
}

export interface SkillFileOp {
  operation: "upsert_text" | "mkdir" | "rename" | "delete";
  path: string;
  target_path?: string;
  content?: string;
}

export interface McpServerCreate {
  openapi_url: string;
  name: string;
  port?: number;
}

export interface McpServer {
  name: string;
  port: number;
  mcp_url: string;
  openapi_url: string;
  started_at: string;
}

