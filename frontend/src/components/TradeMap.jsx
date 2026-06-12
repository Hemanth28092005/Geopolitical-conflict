import { useState, useEffect } from 'react'
import DeckGL from '@deck.gl/react'
import { ArcLayer, ScatterplotLayer } from '@deck.gl/layers'
import { Map } from 'react-map-gl/maplibre'
import { getTradeRoutes, getCountries, getApiErrorMessage } from '../utils/api'

// Country ISO → approximate coordinates
const COUNTRY_COORDS = {
  IND: [78.9629,  20.5937], USA: [-95.7129, 37.0902],
  CHN: [104.1954, 35.8617], RUS: [105.3188, 61.5240],
  DEU: [10.4515,  51.1657], SAU: [45.0792,  23.8859],
  JPN: [138.2529, 36.2048], GBR: [-3.4360,  55.3781],
  FRA: [2.2137,   46.2276], BRA: [-51.9253, -14.2350],
  IRQ: [43.6793,  33.2232], ARE: [53.8478,  23.4241],
  KOR: [127.7669, 35.9078], BGD: [90.3563,  23.6850],
  IDN: [113.9213, -0.7893], EGY: [30.8025,  26.8206],
  AUS: [133.7751, -25.2744],CHL: [-71.5430, -35.6751],
  VNM: [108.2772, 14.0583],
}

const COMMODITY_COLORS = {
  CRUDE_OIL:      [255, 100, 0],
  NATURAL_GAS:    [255, 200, 0],
  SEMICONDUCTORS: [0, 150, 255],
  STEEL:          [150, 150, 150],
  WHEAT:          [200, 180, 0],
  RARE_EARTH:     [150, 0, 255],
  LITHIUM:        [0, 255, 200],
  CORN:           [180, 220, 0],
}

const INITIAL_VIEW = {
  longitude: 78.96,
  latitude:  20.59,
  zoom:      2,
  pitch:     30,
  bearing:   0
}

export default function TradeMap({ selectedCommodity, onRouteClick }) {
  const [routes,    setRoutes]    = useState([])
  const [countries, setCountries] = useState([])
  const [viewState, setViewState] = useState(INITIAL_VIEW)
  const [error,     setError]     = useState('')

  useEffect(() => {
    Promise.all([getTradeRoutes(), getCountries()])
      .then(([routesResponse, countriesResponse]) => {
        setRoutes(routesResponse.data)
        setCountries(countriesResponse.data)
        setError('')
      })
      .catch(requestError => setError(getApiErrorMessage(requestError)))
  }, [])

  const filteredRoutes = selectedCommodity
    ? routes.filter(r => r.commodity === selectedCommodity)
    : routes

  // Arc layer — trade routes
  const arcLayer = new ArcLayer({
    id:            'trade-arcs',
    data:          filteredRoutes,
    getSourcePosition: d => COUNTRY_COORDS[d.from_country] || [0, 0],
    getTargetPosition: d => COUNTRY_COORDS[d.to_country]   || [0, 0],
    getSourceColor: d => [...(COMMODITY_COLORS[d.commodity] || [200,200,200]), 180],
    getTargetColor: d => [...(COMMODITY_COLORS[d.commodity] || [200,200,200]), 80],
    getWidth:       d => Math.max(1, Math.log10((d.annual_value_usd || 1e9) / 1e9) * 2),
    pickable:       true,
    onClick:        ({ object }) => onRouteClick && onRouteClick(object),
  })

  // Scatter layer — country nodes
  const scatterLayer = new ScatterplotLayer({
    id:              'countries',
    data:            countries,
    getPosition:     d => COUNTRY_COORDS[d.iso_code] || [0, 0],
    getRadius:       d => d.iso_code === 'IND' ? 150000 : 80000,
    getFillColor:    d => d.iso_code === 'IND' ? [255, 140, 0, 220] : [100, 180, 255, 180],
    pickable:        true,
  })

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <DeckGL
        viewState={viewState}
        onViewStateChange={({ viewState }) => setViewState(viewState)}
        controller={true}
        layers={[arcLayer, scatterLayer]}
      >
        <Map
          mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
        />
      </DeckGL>

      {error && (
        <div style={{
          position: 'absolute', top: 20, left: 20, right: 20,
          background: '#450a0a', color: '#fca5a5',
          padding: '10px 12px', borderRadius: 6, fontSize: 12
        }}>
          API unavailable: {error}
        </div>
      )}

      {/* Legend */}
      <div style={{
        position: 'absolute', bottom: 20, left: 20,
        background: 'rgba(0,0,0,0.75)', color: '#fff',
        padding: '12px 16px', borderRadius: 8, fontSize: 12
      }}>
        <div style={{ fontWeight: 600, marginBottom: 8 }}>Commodities</div>
        {Object.entries(COMMODITY_COLORS).map(([name, color]) => (
          <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <div style={{
              width: 12, height: 12, borderRadius: '50%',
              background: `rgb(${color.join(',')})`
            }}/>
            <span>{name.replace('_', ' ')}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
