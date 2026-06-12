import { useState } from 'react'
import TradeMap        from './components/TradeMap'
import HostilityMonitor from './components/HostilityMonitor'
import RiskDashboard   from './components/RiskDashboard'
import SimulationView  from './components/SimulationView'
import { useWebSocket } from './hooks/useWebSocket'

const TABS = ['Trade Map', 'Hostility Monitor', 'Risk Dashboard', 'Simulation']
const COMMODITIES = ['All','CRUDE_OIL','NATURAL_GAS','SEMICONDUCTORS','STEEL','WHEAT','RARE_EARTH','CORN','LITHIUM']

export default function App() {
  const [activeTab,          setActiveTab]          = useState('Trade Map')
  const [selectedCommodity,  setSelectedCommodity]  = useState(null)
  const [selectedRoute,      setSelectedRoute]      = useState(null)
  const { messages, connected } = useWebSocket()

  const style = {
    app: {
      background: '#0f172a', minHeight: '100vh',
      color: '#e2e8f0', fontFamily: "'Inter', sans-serif"
    },
    header: {
      background: '#1e293b',
      borderBottom: '1px solid #334155',
      padding: '0 24px',
      display: 'flex', alignItems: 'center',
      justifyContent: 'space-between', height: 56
    },
    title: { fontSize: 16, fontWeight: 700, color: '#f8fafc', letterSpacing: '-0.3px' },
    subtitle: { fontSize: 12, color: '#64748b', marginTop: 2 },
    tabs: { display: 'flex', gap: 4, padding: '0 24px', borderBottom: '1px solid #1e293b' },
    tab: (active) => ({
      padding: '10px 16px', fontSize: 13, cursor: 'pointer',
      borderBottom: active ? '2px solid #3b82f6' : '2px solid transparent',
      color: active ? '#e2e8f0' : '#64748b',
      background: 'none', border: 'none',
      borderBottomWidth: 2,
      borderBottomStyle: 'solid',
      borderBottomColor: active ? '#3b82f6' : 'transparent',
    }),
    content: { padding: 24 },
    badge: (connected) => ({
      fontSize: 11, padding: '2px 8px', borderRadius: 99,
      background: connected ? '#14532d' : '#450a0a',
      color: connected ? '#4ade80' : '#f87171'
    })
  }

  return (
    <div style={style.app}>
      {/* Header */}
      <div style={style.header}>
        <div>
          <div style={style.title}>🌐 WarImpactForecast</div>
          <div style={style.subtitle}>India Geopolitical Trade Intelligence</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {activeTab === 'Trade Map' && (
            <select
              style={{
                background: '#0f172a', border: '1px solid #334155',
                color: '#e2e8f0', borderRadius: 6,
                padding: '4px 8px', fontSize: 12
              }}
              onChange={e => setSelectedCommodity(e.target.value === 'All' ? null : e.target.value)}
            >
              {COMMODITIES.map(c => <option key={c}>{c}</option>)}
            </select>
          )}
          <span style={style.badge(connected)}>
            {connected ? '● Live' : '○ Offline'}
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div style={style.tabs}>
        {TABS.map(tab => (
          <button key={tab} style={style.tab(activeTab === tab)} onClick={() => setActiveTab(tab)}>
            {tab}
          </button>
        ))}
      </div>

      {/* Selected route info */}
      {selectedRoute && activeTab === 'Trade Map' && (
        <div style={{
          background: '#1e293b', padding: '10px 24px',
          borderBottom: '1px solid #334155',
          display: 'flex', gap: 20, fontSize: 13
        }}>
          <span style={{ color: '#94a3b8' }}>Selected Route:</span>
          <span style={{ color: '#e2e8f0', fontWeight: 600 }}>
            {selectedRoute.from_country} → {selectedRoute.to_country}
          </span>
          <span style={{ color: '#f97316' }}>{selectedRoute.commodity}</span>
          <span style={{ color: '#94a3b8' }}>
            ${(selectedRoute.annual_value_usd / 1e9).toFixed(1)}B/yr
          </span>
          <button
            onClick={() => setSelectedRoute(null)}
            style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer' }}
          >✕</button>
        </div>
      )}

      {/* Content */}
      <div style={style.content}>
        {activeTab === 'Trade Map' && (
          <div style={{ height: 'calc(100vh - 160px)', borderRadius: 12, overflow: 'hidden' }}>
            <TradeMap
              selectedCommodity={selectedCommodity}
              onRouteClick={setSelectedRoute}
            />
          </div>
        )}
        {activeTab === 'Hostility Monitor' && (
          <HostilityMonitor liveMessages={messages} />
        )}
        {activeTab === 'Risk Dashboard' && <RiskDashboard />}
        {activeTab === 'Simulation'     && <SimulationView />}
      </div>
    </div>
  )
}