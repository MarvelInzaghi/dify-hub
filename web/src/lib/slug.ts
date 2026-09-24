// Normalize a free-form name into a URL-friendly slug (lowercase letters/digits/-/_).
export function slugify(s: string): string {
  return s
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9_-]/g, "")
    .replace(/^-+|-+$/g, "");
}

// Generate a unique, backend-valid slug, falling back to a generic prefix when the
// display name has no ASCII content (e.g. Chinese). The random suffix keeps it unique.
export function generateSlug(displayName: string): string {
  const base = slugify(displayName).slice(0, 48) || "prompt";
  const suffix = Math.random().toString(36).slice(2, 8);
  return `${base}-${suffix}`;
}
