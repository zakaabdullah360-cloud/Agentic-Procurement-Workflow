import { useMemo, useState } from 'react'
import ChatInput from './components/ChatInput'
import WorkflowTrace from './components/WorkflowTrace'
import SupplierComparison from './components/SupplierComparison'
import POPreview from './components/POPreview'
import ApprovalQueue from './components/ApprovalQueue'
import { createWorkflow, getWorkflow } from './api'

const Icon = ({ name, size = 18 }) => {
  const paths = {
    spark: <><path d="m12 3-1.1 3.7a4.7 4.7 0 0 1-3.2 3.2L4 11l3.7 1.1a4.7 4.7 0 0 1 3.2 3.2L12 19l1.1-3.7a4.7 4.7 0 0 1 3.2-3.2L20 11l-3.7-1.1a4.7 4.7 0 0 1-3.2-3.2L12 3Z"/><path d="m19 3 .35 1.15c.16.53.58.95 1.11 1.11L21.6 5.6l-1.14.34c-.53.16-.95.58-1.11 1.11L19 8.2l-.35-1.15a1.63 1.63 0 0 0-1.11-1.11L16.4 5.6l1.14-.34c.53-.16.95-.58 1.11-1.11L19 3Z"/></>,
    activity: <><path d="M3 12h4l2-7 4 14 2-7h6"/><circle cx="9" cy="5" r="1"/><circle cx="15" cy="19" r="1"/></>,
    shield: <><path d="M12 3 20 6v5c0 5-3.4 8.3-8 10-4.6-1.7-8-5-8-10V6l8-3Z"/><path d="m8.5 12 2.2 2.2 4.8-5"/></>,
    users: <><path d="M16 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2"/><circle cx="9.5" cy="7" r="4"/><path d="M17 11a4 4 0 0 0 0-8"/><path d="M21 21v-2a4 4 0 0 0-3-3.87"/></>,
    file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M8 13h8M8 17h6"/></>,
    check: <path d="m5 12 4 4L19 6"/>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    arrow: <><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></>,
    menu: <><path d="M4 6h16M4 12h16M4 18h16"/></>,
    chevron: <path d="m6 9 6 6 6-6"/>,
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
}

export default function App() {
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const run = async (text) => {
    setLoading(true)
    setError(null)
    try {
      const result = await createWorkflow(text)
      setDetail(result)
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Something went wrong while running the workflow.')
    } finally {
      setLoading(false)
    }
  }

  const refresh = async () => {
    if (!detail) return
    const result = await getWorkflow(detail.workflow.id)
    setDetail(result)
  }

  const metrics = useMemo(() => {
    const quotes = detail?.quotes || []
    const best = quotes.find((q) => q.rank === 1)
    const within = quotes.filter((q) => q.within_budget).length
    return {
      suppliers: quotes.length,
      within,
      best,
      total: detail?.purchase_order?.total,
      currency: detail?.purchase_order?.currency || best?.supplier?.currency || 'PKR',
    }
  }, [detail])

  const status = detail?.workflow?.status
  const isComplete = ['approved', 'rejected', 'failed'].includes(status)

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Icon name="spark" size={20} /></div>
          <div>
            <strong>ProcureAI</strong>
            <span>Autonomous workflow</span>
          </div>
        </div>

        <div className="sidebar-label">WORKSPACE</div>
        <nav className="nav-list">
          <a className="nav-item active" href="#request"><span className="nav-icon"><Icon name="spark" /></span>New request</a>
          <a className="nav-item" href="#trace"><span className="nav-icon"><Icon name="activity" /></span>Execution trace</a>
          <a className="nav-item" href="#suppliers"><span className="nav-icon"><Icon name="users" /></span>Supplier analysis</a>
          <a className="nav-item" href="#approval"><span className="nav-icon"><Icon name="shield" /></span>Approval gate</a>
        </nav>

        <div className="sidebar-spacer" />

        <div className="security-card">
          <div className="security-icon"><Icon name="shield" size={16} /></div>
          <div>
            <strong>Human-in-the-loop</strong>
            <p>Spend stays blocked until approval.</p>
          </div>
        </div>

        <div className="sidebar-footer">
          <span className="online-dot" /> System ready
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="mobile-brand"><div className="brand-mark"><Icon name="spark" size={18} /></div><strong>ProcureAI</strong></div>
          <div className="breadcrumb">Workspace <span>/</span> Procurement agent</div>
          <div className="topbar-right">
            <span className="live-status"><i /> API connected</span>
            <span className="version">HackHorizon PS-2</span>
          </div>
        </header>

        <section className="hero" id="request">
          <div className="hero-copy">
            <div className="eyebrow"><span className="eyebrow-dot"><Icon name="spark" size={12} /></span> AI PROCUREMENT CONTROL CENTER</div>
            <h1>Turn business intent into<br /><em>controlled action.</em></h1>
            <p>Describe what you need in plain English. ProcureAI plans the workflow, compares suppliers, validates the result and prepares the purchase order — without bypassing human approval.</p>
          </div>
          <div className="hero-orbit" aria-hidden="true">
            <div className="orbit orbit-1"><span><Icon name="spark" size={16} /></span></div>
            <div className="orbit orbit-2"><span><Icon name="shield" size={14} /></span></div>
            <div className="orbit-core"><Icon name="activity" size={26} /></div>
          </div>
        </section>

        <section className="request-card">
          <div className="request-head">
            <div>
              <span className="section-kicker">01 · REQUEST</span>
              <h2>What would you like to procure?</h2>
            </div>
            <span className="secure-badge"><Icon name="shield" size={14} /> Controlled execution</span>
          </div>
          <ChatInput onSubmit={run} loading={loading} />
        </section>

        {error && (
          <div className="alert error-alert">
            <div className="alert-icon">!</div>
            <div><strong>Workflow could not be completed</strong><span>{error}</span></div>
          </div>
        )}

        {detail && (
          <>
            <section className="metric-grid">
              <div className="metric-card">
                <div className="metric-icon purple"><Icon name="activity" /></div>
                <div><span>Workflow status</span><strong className="metric-status">{status?.replace(/_/g, ' ')}</strong></div>
                <div className={`tiny-status ${status}`}><span /></div>
              </div>
              <div className="metric-card">
                <div className="metric-icon blue"><Icon name="users" /></div>
                <div><span>Suppliers compared</span><strong>{metrics.suppliers || '—'}</strong></div>
                <small>{metrics.within} within budget</small>
              </div>
              <div className="metric-card">
                <div className="metric-icon green"><Icon name="check" /></div>
                <div><span>Recommended supplier</span><strong>{metrics.best?.supplier?.name || 'Pending'}</strong></div>
                <small>{metrics.best?.score != null ? `Score ${metrics.best.score.toFixed(2)}` : 'Awaiting analysis'}</small>
              </div>
              <div className="metric-card">
                <div className="metric-icon amber"><Icon name="file" /></div>
                <div><span>Purchase order</span><strong>{metrics.total ? `${metrics.total.toLocaleString()} ${metrics.currency}` : 'Not created'}</strong></div>
                <small>{detail.purchase_order ? 'Validated draft' : 'Pending generation'}</small>
              </div>
            </section>

            {detail.extracted_params && (
              <details className="params-panel">
                <summary><span><span className="section-kicker">REQUEST DATA</span><strong>Extracted parameters</strong></span><Icon name="chevron" size={17} /></summary>
                <pre className="raw">{JSON.stringify(detail.extracted_params, null, 2)}</pre>
              </details>
            )}

            <div id="trace"><WorkflowTrace workflow={detail.workflow} steps={detail.steps} /></div>
            <div id="suppliers"><SupplierComparison quotes={detail.quotes} /></div>
            <POPreview po={detail.purchase_order} report={detail.final_report} />
            <div id="approval"><ApprovalQueue approval={detail.approval} onDecided={refresh} /></div>

            {detail.final_report && isComplete && (
              <details className="report-panel">
                <summary><span><span className="section-kicker">AUDIT OUTPUT</span><strong>Completion report</strong></span><Icon name="chevron" size={17} /></summary>
                <pre className="raw">{JSON.stringify(detail.final_report, null, 2)}</pre>
              </details>
            )}
          </>
        )}

        {!detail && !loading && (
          <section className="empty-state">
            <div className="empty-visual">
              <div className="empty-ring ring-a" />
              <div className="empty-ring ring-b" />
              <div className="empty-core"><Icon name="spark" size={24} /></div>
            </div>
            <span className="section-kicker">READY WHEN YOU ARE</span>
            <h2>One request. One controlled workflow.</h2>
            <p>Start with a sample above or describe your own procurement or vendor-renewal request.</p>
            <div className="flow-pills">
              <span>Parse intent</span><b>→</b><span>Plan</span><b>→</b><span>Compare</span><b>→</b><span>Validate</span><b>→</b><span>Approve</span>
            </div>
          </section>
        )}

        {loading && (
          <section className="loading-card">
            <div className="loader-orb"><span /><span /><span /></div>
            <div><strong>Agent is orchestrating your request</strong><p>Parsing intent · planning actions · checking suppliers · validating outputs</p></div>
          </section>
        )}

        <footer className="footer">
          <span>ProcureAI · Agentic Procurement Workflow</span>
          <span><Icon name="shield" size={13} /> Human approval required before spend</span>
        </footer>
      </main>
    </div>
  )
}
