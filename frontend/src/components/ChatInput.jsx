import { useState } from 'react'

const EXAMPLES = [
  'Create a purchase request for 50 laptops under PKR 10 million, compare three suppliers, identify the best option, prepare the purchase order, and send it for approval.',
  'Our software vendor contract is expiring. Compare 3 renewal/alternative options and recommend one within a $20,000 budget.',
  'Buy some laptops please',
]

export default function ChatInput({ onSubmit, loading }) {
  const [text, setText] = useState('')

  const submit = () => {
    if (!text.trim() || loading) return
    onSubmit(text.trim())
  }

  const onKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') submit()
  }

  return (
    <div>
      <div className="examples">
        <span className="examples-label">Try a sample:</span>
        {EXAMPLES.map((ex, i) => (
          <button key={i} onClick={() => setText(ex)}>
            {i === 0 ? 'Laptop procurement' : i === 1 ? 'Vendor renewal' : 'Missing-info demo'}
          </button>
        ))}
      </div>
      <div className="chat-box">
        <textarea
          aria-label="Business request"
          placeholder="Describe a business request in plain English…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <button onClick={submit} disabled={loading || !text.trim()}>
          {loading ? 'Running…' : 'Run agent'}
        </button>
      </div>
      <div style={{ marginTop: 7, color: '#9aa2b1', fontSize: 8 }}>
        Press Ctrl + Enter to run · The agent will stop at the human approval gate.
      </div>
    </div>
  )
}
