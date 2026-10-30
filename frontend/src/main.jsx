import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './lexai.css'
import App from './LexAI.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
