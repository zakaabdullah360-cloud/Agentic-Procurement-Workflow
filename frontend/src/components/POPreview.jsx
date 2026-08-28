import { poDownloadUrl } from '../api'

export default function POPreview({ po, report }) {
  if (!po) return null
  return (
    <div className="panel po-panel">
      <div className="comparison-title">
        <div>
          <span className="section-kicker">04 · DOCUMENT</span>
          <h2>Purchase order</h2>
        </div>
        <span className={`status-pill ${po.validated ? 'done' : 'failed'}`}>
          {po.validated ? 'Validated' : 'Validation failed'}
        </span>
      </div>

      <table>
        <tbody>
          <tr><th>Item</th><td>{po.item}</td></tr>
          <tr><th>Quantity</th><td>{po.quantity.toLocaleString()}</td></tr>
          <tr><th>Unit price</th><td>{po.unit_price.toLocaleString()} {po.currency}</td></tr>
          <tr><th>Terms</th><td>{po.terms || 'Standard procurement terms'}</td></tr>
        </tbody>
      </table>

      <div className="po-total">
        <span>Validated order total</span>
        <strong>{po.total.toLocaleString()} {po.currency}</strong>
      </div>

      {po.validation_notes && <div className="explanation-box">{po.validation_notes}</div>}
      {report?.summary && <div className="explanation-box">{report.summary}</div>}

      <a className="btn po-download" href={poDownloadUrl(po.id)} target="_blank" rel="noreferrer">
        Download PO · .docx
      </a>
    </div>
  )
}
