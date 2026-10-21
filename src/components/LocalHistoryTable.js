import { EmptyState } from "@/components/ui";

export default function LocalHistoryTable({ title, items, columns, onClear, emptyTitle, emptyMessage }) {
  return (
    <div className="mt-8 rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-xl font-bold text-white">{title}</h3>
          <p className="text-sm text-slate-400">
            Browser history for quick review. Open the Dashboard for your saved backend records.
          </p>
        </div>
        <button
          onClick={onClear}
          disabled={items.length === 0}
          className="rounded-xl bg-red-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-600 disabled:opacity-50"
        >
          Clear Local History
        </button>
      </div>

      {items.length > 0 ? (
        <div className="max-h-72 overflow-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead className="text-slate-400">
              <tr className="border-b border-slate-700">
                {columns.map((column) => (
                  <th key={column.label} className="py-3 pr-3">{column.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-slate-800">
                  {columns.map((column) => (
                    <td key={column.label} className={`py-3 pr-3 ${column.className || "text-slate-300"}`}>
                      {column.render ? column.render(item) : item[column.key]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState title={emptyTitle} message={emptyMessage} />
      )}
    </div>
  );
}
