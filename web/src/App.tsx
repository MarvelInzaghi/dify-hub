import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import PromptsPage from "./pages/PromptsPage";
import PromptEditorPage from "./pages/PromptEditorPage";
import SkillsPage from "./pages/SkillsPage";
import SkillEditorPage from "./pages/SkillEditorPage";
import PublicationsPage from "./pages/PublicationsPage";
import ApiKeysPage from "./pages/ApiKeysPage";
import DocsPage from "./pages/DocsPage";
import McpPage from "./pages/McpPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<SkillsPage />} />
        <Route path="/skills" element={<SkillsPage />} />
        <Route path="/skills/:id" element={<SkillEditorPage />} />
        <Route path="/prompts" element={<PromptsPage />} />
        <Route path="/prompts/:id" element={<PromptEditorPage />} />
        <Route path="/publications" element={<PublicationsPage />} />
        <Route path="/api-keys" element={<ApiKeysPage />} />
        <Route path="/docs" element={<DocsPage />} />
        <Route path="/mcp" element={<McpPage />} />
      </Route>
    </Routes>
  );
}
