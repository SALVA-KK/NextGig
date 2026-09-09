import React from 'react';

/**
 * Reusable PaginationControl component for NextGig lists
 *
 * Props:
 * - currentPage: number (1-based index)
 * - totalItems: number (total count of records across all pages)
 * - pageSize: number (items per page, default 20)
 * - onPageChange: (newPage: number) => void
 */
export default function PaginationControl({
  currentPage = 1,
  totalItems = 0,
  pageSize = 20,
  onPageChange
}) {
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));

  // If there's only 1 page or no items, don't show pagination controls unless totalItems > pageSize
  if (totalItems <= pageSize) {
    return null;
  }

  const startItem = (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalItems);

  const handlePrev = () => {
    if (currentPage > 1 && onPageChange) {
      onPageChange(currentPage - 1);
    }
  };

  const handleNext = () => {
    if (currentPage < totalPages && onPageChange) {
      onPageChange(currentPage + 1);
    }
  };

  return (
    <div
      className="pagination-container"
      style={{
        display: 'flex',
        alignItems: 'center',
        justify: 'space-between',
        flexWrap: 'wrap',
        gap: '16px',
        padding: '16px 20px',
        marginTop: '20px',
        borderRadius: '12px',
        backgroundColor: 'var(--bg-surface, #ffffff)',
        border: '1px solid var(--border-color, #e5e7eb)',
      }}
    >
      <div style={{ fontSize: '14px', color: 'var(--text-muted, #6b7280)' }}>
        Showing <strong>{startItem}</strong> - <strong>{endItem}</strong> of <strong>{totalItems}</strong> results
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button
          onClick={handlePrev}
          disabled={currentPage <= 1}
          className="btn-secondary-link"
          style={{
            padding: '6px 14px',
            fontSize: '13px',
            fontWeight: '600',
            borderRadius: '6px',
            border: '1px solid var(--border-color, #e5e7eb)',
            cursor: currentPage <= 1 ? 'not-allowed' : 'pointer',
            opacity: currentPage <= 1 ? 0.5 : 1,
            backgroundColor: 'transparent',
            color: 'var(--text-main, #111827)',
          }}
        >
          &larr; Previous
        </button>

        <span
          style={{
            fontSize: '13px',
            fontWeight: '600',
            color: 'var(--text-main, #111827)',
            padding: '0 8px',
          }}
        >
          Page {currentPage} of {totalPages}
        </span>

        <button
          onClick={handleNext}
          disabled={currentPage >= totalPages}
          className="btn-secondary-link"
          style={{
            padding: '6px 14px',
            fontSize: '13px',
            fontWeight: '600',
            borderRadius: '6px',
            border: '1px solid var(--border-color, #e5e7eb)',
            cursor: currentPage >= totalPages ? 'not-allowed' : 'pointer',
            opacity: currentPage >= totalPages ? 0.5 : 1,
            backgroundColor: 'transparent',
            color: 'var(--text-main, #111827)',
          }}
        >
          Next &rarr;
        </button>
      </div>
    </div>
  );
}
