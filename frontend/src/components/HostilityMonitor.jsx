import { useState, useEffect } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from 'recharts'
import { getHostilityScores, getApiErrorMessage } from '../utils/api'

const COUNTRY_PAIRS = [
  { a: 'IND', b: 'RUS', color: '#ef4444' },
  { a: 'IND', b: 'CHN', color: '#f97316' },
  { a: 'IND', b: 'USA', color: '#3b82f6' },
  { a: 'IND', b: 'GBR', color: '#8b5cf6' },
]

export default function HostilityMonitor({ liveMessages }) {
  const [scores, setScores] = useState([])
  const [error, setError] = useState('')
  const latestMessage = liveMessages?.[0]

  useEffect(() => {
    if (latestMessage && latestMessage.type !== 'hostility_update') return

    getHostilityScores(null, 200).then(r => {
      // Group by time for chart
      const grouped = {}
      r.data.forEach(s => {
        const t = s.time.substring(0, 16) // minute precision
        if (!grouped[t]) grouped[t] = { time: t }
        grouped[t][`${s.country_a}-${s.country_b}`] = s.score
      })
      setScores(Object.values(grouped).sort((a, b) => a.time.localeCompare(b.time)).slice(-50))
      setError('')
    }).catch(requestError => setError(getApiErrorMessage(requestError)))
  }, [latestMessage])

  return (
    <div style={{ padding: '16px 0' }}>
      <h3 style={{ color: '#e2e8f0', marginBottom: 16, fontSize: 14, fontWeight: 600 }}>
        India Hostility Monitor — Live
      </h3>

      {error && <div style={{ color: '#fca5a5', fontSize: 13 }}>API unavailable: {error}</div>}

      {scores.length === 0 ? (
        <div style={{ color: '#94a3b8', fontSize: 13, padding: '20px 0' }}>
          No hostility data yet — run the sentiment engine to populate scores.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={scores}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="time"
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              tickFormatter={v => v.substring(11)}
            />
            <YAxis domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: '1px solid #334155', color: '#e2e8f0' }}
            />
            <Legend />
            <ReferenceLine y={65} stroke="#ef4444" strokeDasharray="4 4" label={{ value: 'Alert', fill: '#ef4444', fontSize: 11 }} />
            {COUNTRY_PAIRS.map(({ a, b, color }) => (
              <Line
                key={`${a}-${b}`}
                type="monotone"
                dataKey={`${a}-${b}`}
                stroke={color}
                dot={false}
                strokeWidth={2}
                name={`IND↔${b}`}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}

      {/* Latest scores table */}
      <div style={{ marginTop: 16 }}>
        <div style={{ color: '#94a3b8', fontSize: 12, marginBottom: 8 }}>Latest Scores</div>
        {scores.slice(-1).map((row, i) => (
          <div key={i} style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {COUNTRY_PAIRS.map(({ a, b }) => {
              const score = row[`${a}-${b}`]
              if (score == null) return null
              return (
                <div key={`${a}-${b}`} style={{
                  background: '#1e293b', borderRadius: 6,
                  padding: '6px 12px', fontSize: 12
                }}>
                  <span style={{ color: '#94a3b8' }}>IND↔{b} </span>
                  <span style={{
                    color: score > 65 ? '#ef4444' : score > 45 ? '#f97316' : '#22c55e',
                    fontWeight: 600
                  }}>{score}</span>
                </div>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}
