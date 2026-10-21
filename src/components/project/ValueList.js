// Renders a string, a list of strings, or a list of objects returned by the AI.
export default function ValueList({ value }) {
  if (!value || (Array.isArray(value) && value.length === 0)) return null;

  if (Array.isArray(value)) {
    return (
      <ul className="mt-2 list-disc space-y-2 pl-5 text-sm leading-7 text-slate-200">
        {value.map((item, index) => (
          <li key={index} className="break-words">
            {typeof item === "object" && item !== null
              ? Object.entries(item)
                  .map(([key, val]) => `${key}: ${typeof val === "object" ? JSON.stringify(val) : val}`)
                  .join(" | ")
              : item}
          </li>
        ))}
      </ul>
    );
  }

  return <p className="mt-2 whitespace-pre-line break-words text-sm leading-7 text-slate-200">{value}</p>;
}
