import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './lexai.css'
import App from './LexAI'

const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error('Failed to find root element')
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
