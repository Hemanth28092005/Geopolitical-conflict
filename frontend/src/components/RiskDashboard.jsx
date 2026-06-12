import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { getForecastResults, getApiErrorMessage } from '../utils/api'

export default function RiskDashboard() {
  const [forecasts, setForecasts] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    getForecastResults('xgboost_route_risk').then(r => {
      const sorted = [...r.data]
        .sort((a, b) => b.forecast_value - a.forecast_value)
        .slice(0, 15)
      setForecasts(sorted)
      setError('')
    }).catch(requestError => setError(getApiErrorMessage(requestError)))
  }, [])

  const getRiskColor = (val) => {
    if (val > 0.6) return '#ef4444'
    if (val > 0.3) return '#f97316'
    return '#22c55e'
  }

  return (
    <div style={{ padding: '16px 0' }}>
      <h3 style={{ color: '#e2e8f0', marginBottom: 16, fontSize: 14, fontWeight: 600 }}>
        Route Risk Dashboard — XGBoost P(closure)
      </h3>

      {error && <div style={{ color: '#fca5a5', fontSize: 13 }}>API unavailable: {error}</div>}

      <ResponsiveContainer width="100%" height={320}>
        <BarChart
          data={forecasts}
          layout="vertical"
          margin={{ left: 80, right: 20 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            type="number"
            domain={[0, 1]}
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            tickFormatter={v => `${(v * 100).toFixed(0)}%`}
          />
          <YAxis
            type="category"
            dataKey="route"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            width={80}
          />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', color: '#e2e8f0' }}
            formatter={(v) => [`${(v * 100).toFixed(1)}%`, 'P(closure)']}
          />
          <Bar dataKey="forecast_value" radius={[0, 4, 4, 0]}>
            {forecasts.map((entry, i) => (
              <Cell key={i} fill={getRiskColor(entry.forecast_value)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
