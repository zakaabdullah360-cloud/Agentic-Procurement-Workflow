export default function SupplierComparison({ quotes }) {
  if (!quotes || quotes.length === 0) return null

  const sorted = [...quotes].sort((a, b) => {
    if (a.rank == null) return 1
    if (b.rank == null) return -1
    return a.rank - b.rank
  })
  const best = sorted.find((q) => q.rank === 1)

  return (
    <div className="panel supplier-panel">
      <div className="comparison-title">
        <div>
          <span className="section-kicker">03 · SOURCING</span>
          <h2>Supplier comparison & scoring</h2>
        </div>
        <div className="weight-chips">
          <span className="weight-chip"><b>50%</b> Price</span>
          <span className="weight-chip"><b>30%</b> Delivery</span>
          <span className="weight-chip"><b>20%</b> Warranty</span>
        </div>
      </div>

      {best && (
        <div className="best-banner">
          <span className="score-badge">#1</span>
          <span><strong>{best.supplier.name}</strong> is the recommended option based on the transparent weighted score.</span>
        </div>
      )}

      <div style={{ overflowX: 'auto' }}>
        <table>
          <thead>
            <tr>
              <th>Supplier</th><th>Unit price</th><th>Total</th><th>Lead time</th>
              <th>Warranty</th><th>Budget</th><th>Score</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((q) => (
              <tr key={q.id} className={q.rank === 1 ? 'best-row' : ''}>
                <td>
                  <strong>{q.supplier.name}</strong>
                  {q.rank === 1 && <span className="selected-label">Recommended</span>}
                </td>
                <td>{q.unit_price.toLocaleString()} {q.supplier.currency}</td>
                <td>{q.total_price.toLocaleString()} {q.supplier.currency}</td>
                <td>{q.lead_time_days}d</td>
                <td>{q.warranty_years}y</td>
                <td>
                  <span className={`status-pill ${q.within_budget ? 'budget-ok' : 'budget-bad'}`}>
                    {q.within_budget ? 'Within' : 'Exceeds'}
                  </span>
                </td>
                <td>{q.score != null ? <span className="score-badge">{q.score.toFixed(2)}</span> : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
