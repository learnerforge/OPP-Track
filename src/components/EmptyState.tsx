interface EmptyStateProps {
  onAdd: () => void;
}

export function EmptyState({ onAdd }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 animate-fade-in">
      <div className="text-5xl mb-4">🎯</div>
      <h3 className="text-xl font-semibold text-gray-800 mb-2">
        No opportunities yet
      </h3>
      <p className="text-gray-500 text-center max-w-md mb-6">
        Start tracking hackathons, internships, and certifications. Add your
        first opportunity to see it here.
      </p>
      <button
        onClick={onAdd}
        className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-6 py-3 rounded-lg transition-colors"
      >
        + Add First Opportunity
      </button>
    </div>
  );
}
