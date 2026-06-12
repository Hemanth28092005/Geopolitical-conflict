import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000,
})

export const getCountries       = () => api.get('/countries')
export const getTradeRoutes     = (country) => api.get('/trade-routes', { params: { country } })
export const getHostilityScores = (country, limit) => api.get('/hostility-scores', { params: { country, limit } })
export const getLatestHostility = () => api.get('/hostility-scores/latest')
export const getForecastResults = (model) => api.get('/forecast-results', { params: { model } })
export const getSimulations     = () => api.get('/simulations')
export const runSimulation      = (payload) => api.post('/simulate', payload)

export function getApiErrorMessage(error) {
  const message = error.response?.data?.detail
    || error.response?.data?.error
    || error.message
    || 'Unable to reach the API'

  return typeof message === 'string' ? message : JSON.stringify(message)
}
