import { useState } from 'react'
import { runSimulation, getSimulations, getApiErrorMessage } from '../utils/api'
import { useEffect } from 'react'

const COUNTRIES  = ['IND','USA','CHN','RUS','DEU','SAU','JPN','GBR','FRA','BRA','IRQ','ARE','KOR','BGD','AUS']
const COMMODITIES = ['CRUDE_OIL','NATURAL_GAS','SEMICONDUCTORS','STEEL','WHEAT','RARE_EARTH','CORN','LITHIUM']

export default function SimulationView() {
  const [form,       setForm]       = useState({ from: 'RUS', to: 'IND', commodity: 'CRUDE_OIL', closure: 50 })
  const [result,     setResult]     = useState(null)
  const [history,    setHistory]    = useState([])
  const [loading,    setLoading]    = useState(false)
  const [error,      setError]      = useState('')

  useEffect(() => {
    getSimulations()
      .then(r => {
        setHistory(r.data)
        setError('')
      })
      .catch(requestError => setError(getApiErrorMessage(requestError)))
  }, [])

  const handleRun = async () => {
    setLoading(true)
    try {
      const res = await runSimulation({
        name:   `${form.from}→${form.to} ${form.commodity} ${form.closure}%`,
        shocks: [{ from_country: form.from, to_country: form.to, commodity: form.commodity, closure_pct: form.closure }]
      })
      setResult(res.data)
      setError('')
      const historyResponse = await getSimulations()
      setHistory(historyResponse.data)
    } catch (e) {
      setError(getApiErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  const inp = {
    background: '#1e293b', border: '1px solid #334155',
    borderRadius: 6, color: '#e2e8f0', padding: '6px 10px', fontSize: 13
  }

  return (
    <div style={{ padding: '16px 0' }}>
      <h3 style={{ color: '#e2e8f0', marginBottom: 16, fontSize: 14, fontWeight: 600 }}>
        What-if Simulation Engine
      </h3>

      {error && <div style={{ color: '#fca5a5', fontSize: 13, marginBottom: 12 }}>API unavailable: {error}</div>}

      {/* Form */}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
        <select style={inp} value={form.from} onChange={e => setForm({...form, from: e.target.value})}>
          {COUNTRIES.map(c => <option key={c}>{c}</option>)}
        </select>
        <span style={{ color: '#94a3b8', alignSelf: 'center' }}>→</span>
        <select style={inp} value={form.to} onChange={e => setForm({...form, to: e.target.value})}>
          {COUNTRIES.map(c => <option key={c}>{c}</option>)}
        </select>
        <select style={inp} value={form.commodity} onChange={e => setForm({...form, commodity: e.target.value})}>
          {COMMODITIES.map(c => <option key={c}>{c}</option>)}
        </select>
        <input
          type="range" min={0} max={100} value={form.closure}
          onChange={e => setForm({...form, closure: Number(e.target.value)})}
          style={{ width: 100 }}
        />
        <span style={{ color: '#e2e8f0', fontSize: 13, alignSelf: 'center' }}>{form.closure}%</span>
        <button
          onClick={handleRun}
          disabled={loading}
          style={{
            background: loading ? '#334155' : '#3b82f6',
            border: 'none', borderRadius: 6,
            color: '#fff', padding: '6px 18px',
            cursor: loading ? 'not-allowed' : 'pointer', fontSize: 13
          }}
        >
          {loading ? 'Running...' : 'Run Simulation'}
        </button>
      </div>

      {/* Result */}
      {result && (
        <div style={{
          background: '#1e293b', borderRadius: 8,
          padding: 16, marginBottom: 16,
          border: '1px solid #334155'
        }}>
          <div style={{ color: '#e2e8f0', fontWeight: 600, marginBottom: 12 }}>
            {result.scenario}
          </div>
          <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', marginBottom: 12 }}>
            {[
              { label: 'Direct Impact',  value: `$${(result.impact?.direct_impact_usd/1e9).toFixed(1)}B` },
              { label: 'Cascade Impact', value: `$${(result.impact?.cascade_impact_usd/1e9).toFixed(1)}B` },
              { label: 'Total Impact',   value: `$${(result.impact?.total_impact_usd/1e9).toFixed(1)}B` },
              { label: 'Nodes Affected', value: result.cascade?.affected_count },
            ].map(({ label, value }) => (
              <div key={label} style={{ textAlign: 'center' }}>
                <div style={{ color: '#94a3b8', fontSize: 11 }}>{label}</div>
                <div style={{ color: '#f97316', fontSize: 20, fontWeight: 700 }}>{value}</div>
              </div>
            ))}
          </div>

          {/* Node impact bars */}
          <div style={{ fontSize: 12 }}>
            <div style={{ color: '#94a3b8', marginBottom: 8 }}>Node Impact Scores</div>
            {Object.entries(result.cascade?.node_impacts || {})
              .sort((a, b) => b[1] - a[1])
              .map(([node, score]) => (
                <div key={node} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <span style={{ color: '#94a3b8', width: 35 }}>{node}</span>
                  <div style={{ flex: 1, background: '#0f172a', borderRadius: 4, height: 16 }}>
                    <div style={{
                      width: `${score}%`, height: '100%',
                      background: score > 65 ? '#ef4444' : score > 35 ? '#f97316' : '#22c55e',
                      borderRadius: 4, transition: 'width 0.5s'
                    }}/>
                  </div>
                  <span style={{ color: '#e2e8f0', width: 35 }}>{score}</span>
                </div>
              ))
            }
          </div>
        </div>
      )}

      {/* History */}
      <div>
        <div style={{ color: '#94a3b8', fontSize: 12, marginBottom: 8 }}>Simulation History</div>
        {history.slice(0, 5).map(h => (
          <div key={h.id} style={{
            background: '#1e293b', borderRadius: 6,
            padding: '8px 12px', marginBottom: 6,
            border: '1px solid #1e293b',
            display: 'flex', justifyContent: 'space-between',
            fontSize: 12
          }}>
            <span style={{ color: '#e2e8f0' }}>{h.name}</span>
            <span style={{ color: '#f97316' }}>${(h.total_impact_usd/1e9).toFixed(1)}B</span>
          </div>
        ))}
      </div>
    </div>
  )
}
