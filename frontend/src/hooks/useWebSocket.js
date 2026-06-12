import { useEffect, useRef, useState } from 'react'

function getDefaultWebSocketUrl() {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws/live-feed`
}

export function useWebSocket(url = getDefaultWebSocketUrl()) {
  const [messages, setMessages] = useState([])
  const [connected, setConnected] = useState(false)
  const ws = useRef(null)

  useEffect(() => {
    let reconnectTimer
    let pingTimer
    let disposed = false

    const connect = () => {
      const socket = new WebSocket(url)
      ws.current = socket

      socket.onopen = () => {
        setConnected(true)
        pingTimer = window.setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) socket.send('ping')
        }, 20000)
      }

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          setMessages(previous => [data, ...previous].slice(0, 50))
        } catch (error) {
          console.error('Invalid WebSocket message', error)
        }
      }

      socket.onclose = () => {
        setConnected(false)
        window.clearInterval(pingTimer)
        if (!disposed) reconnectTimer = window.setTimeout(connect, 3000)
      }

      socket.onerror = () => socket.close()
    }

    connect()

    return () => {
      disposed = true
      window.clearInterval(pingTimer)
      window.clearTimeout(reconnectTimer)
      ws.current?.close()
    }
  }, [url])

  return { messages, connected }
}
