const label = (value = '') => value.replace(/_/g, ' ')

export default function WorkflowTrace({ workflow, steps = [] }) {
  if (!workflow) return null
  return (
    <div className="panel workflow-panel">
      <div className="comparison-title">
        <div>
          <span className="section-kicker">02 · ORCHESTRATION</span>
          <h2>Execution trace</h2>
        </div>
        <span className={`status-pill ${workflow.status}`}>{label(workflow.status)}</span>
      </div>

      {workflow.failure_reason && (
        <div className="failure-box">{workflow.failure_reason}</div>
      )}

      {steps.map((s, i) => (
        <div className={`step-row ${s.status === 'done' || s.status === 'success' ? 'is-done' : ''}`} key={s.id}>
          <div className="step-index">{String(i + 1).padStart(2, '0')}</div>
          <div className="step-name">{label(s.step_name)}</div>
          <span className={`status-pill ${s.status}`}>{label(s.status)}</span>
        </div>
      ))}
    </div>
  )
}
