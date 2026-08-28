import { useState } from 'react'
import { approve, reject } from '../api'

export default function ApprovalQueue({ approval, onDecided }) {
  const [busy, setBusy] = useState(false)
  if (!approval) return null

  const act = async (fn) => {
    setBusy(true)
    try {
      await fn(approval.id, 'Demo Manager', '')
      onDecided()
    } finally {
      setBusy(false)
    }
  }

  const pending = approval.status === 'pending'

  return (
    <div className="panel approval-panel">
      <div className="comparison-title">
        <div>
          <span className="section-kicker">05 · CONTROL</span>
          <h2>Human approval gate</h2>
        </div>
        <span className={`status-pill ${approval.status}`}>{approval.status}</span>
      </div>

      {pending ? (
        <>
          <div className="approval-note">
            <span className="note-icon">●</span>
            <span>The workflow is paused here by design. No spend action can proceed until a human decision is recorded.</span>
          </div>
          <div className="approval-actions">
            <button className="btn" disabled={busy} onClick={() => act(approve)}>
              {busy ? 'Processing…' : 'Approve purchase'}
            </button>
            <button className="btn danger" disabled={busy} onClick={() => act(reject)}>
              Reject
            </button>
          </div>
        </>
      ) : (
        <div className="approval-note">
          <span className="note-icon">✓</span>
          <span>Decision recorded by <strong>{approval.approver}</strong> at {approval.decided_at ? new Date(approval.decided_at).toLocaleString() : '—'}.</span>
        </div>
      )}
    </div>
  )
}
