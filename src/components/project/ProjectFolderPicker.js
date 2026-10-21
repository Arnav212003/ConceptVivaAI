"use client";

export const MAX_PROJECT_SOURCE_CHARS = 2_200_000;
const MAX_PROJECT_FILES = 250;
const MAX_SINGLE_FILE_BYTES = 300_000;

const IGNORED_PROJECT_DIRS = new Set([
  "node_modules", ".git", ".next", "dist", "build", "coverage",
  "venv", ".venv", "env", "__pycache__", ".idea", ".vscode",
  "target", "out", ".pytest_cache", ".mypy_cache",
]);

const SOURCE_EXTENSIONS = new Set([
  ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".cpp", ".cc", ".c",
  ".h", ".hpp", ".cs", ".go", ".rs", ".php", ".rb", ".swift", ".kt",
  ".kts", ".scala", ".sql", ".html", ".css", ".scss", ".sass", ".less",
  ".vue", ".svelte", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
  ".conf", ".xml", ".md", ".txt", ".sh", ".bash", ".ps1", ".bat",
  ".gradle", ".properties", ".graphql", ".gql", ".proto",
]);

const SOURCE_FILENAMES = new Set([
  "dockerfile", "makefile", "procfile", "requirements.txt", "package.json",
  "pyproject.toml", "pom.xml", "build.gradle", "settings.gradle", "readme.md", ".env.example",
]);

// Lock files are large and carry no reviewable logic.
const SKIPPED_FILENAMES = new Set(["package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock"]);

export function isReadableProjectFile(file) {
  const relativePath = file.webkitRelativePath || file.name;
  const parts = relativePath.split("/").map((part) => part.toLowerCase());
  if (parts.some((part) => IGNORED_PROJECT_DIRS.has(part))) return false;

  const lowerName = file.name.toLowerCase();
  if (SKIPPED_FILENAMES.has(lowerName)) return false;
  // Secret files are never uploaded, only the example template.
  if (lowerName === ".env" || lowerName.startsWith(".env.")) return lowerName === ".env.example";
  if (SOURCE_FILENAMES.has(lowerName)) return true;

  const dotIndex = lowerName.lastIndexOf(".");
  return SOURCE_EXTENSIONS.has(dotIndex >= 0 ? lowerName.slice(dotIndex) : "");
}

export async function readProjectFolder(fileList) {
  const selected = Array.from(fileList || []);
  const readable = selected
    .filter(isReadableProjectFile)
    .filter((file) => file.size <= MAX_SINGLE_FILE_BYTES)
    .slice(0, MAX_PROJECT_FILES);

  if (!readable.length) {
    throw new Error("No readable source files found. Select the project source folder, not a build or dependency folder.");
  }

  const files = [];
  let totalChars = 0;
  for (const file of readable) {
    const content = await file.text();
    totalChars += content.length;
    if (totalChars > MAX_PROJECT_SOURCE_CHARS) {
      throw new Error(
        "Project source is too large for one review. Remove generated or data files and keep the source under 2.2M characters."
      );
    }
    files.push({ path: file.webkitRelativePath || file.name, content });
  }
  return { files, info: { files: files.length, totalChars, skipped: selected.length - files.length } };
}

export default function ProjectFolderPicker({ files, info, error, onChange }) {
  return (
    <>
      <div className="mt-4 rounded-2xl border border-dashed border-emerald-400/40 bg-emerald-950/10 p-5">
        <label htmlFor="project-folder" className="block text-sm font-semibold text-emerald-200">
          Full Project Folder
        </label>
        <input
          id="project-folder"
          type="file"
          multiple
          webkitdirectory=""
          directory=""
          onChange={onChange}
          className="mt-3 block w-full text-sm text-slate-300 file:mr-4 file:rounded-lg file:border-0 file:bg-emerald-500 file:px-4 file:py-2 file:font-semibold file:text-white hover:file:bg-emerald-600"
        />
        <p className="mt-3 text-xs leading-5 text-slate-400">
          Dependencies and build output (node_modules, .git, .next, venv, dist), lock files and binaries are
          skipped automatically. Secret .env files are never included.
        </p>

        {info && (
          <div className="mt-4 rounded-xl border border-emerald-400/30 bg-slate-950/50 p-3 text-sm text-emerald-100">
            Ready for full review: <strong>{info.files}</strong> source files · {info.totalChars.toLocaleString()} characters
            {info.skipped > 0 ? ` · ${info.skipped} dependency/binary/large files skipped` : ""}
          </div>
        )}

        {error && (
          <p role="alert" className="mt-4 rounded-xl border border-red-400/30 bg-red-950/20 p-3 text-sm text-red-200">
            {error}
          </p>
        )}
      </div>

      {files.length > 0 && (
        <div className="mt-4 max-h-48 overflow-y-auto rounded-xl border border-slate-700 bg-slate-950/50 p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Included source files</p>
          {files.map((file) => (
            <p key={file.path} className="truncate py-1 font-mono text-xs text-slate-300">{file.path}</p>
          ))}
        </div>
      )}
    </>
  );
}
