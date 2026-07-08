import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

// Legacy theme, loaded globally in the same order as base.html:
// 1. erpnext-style.css (custom theme), 2. FontAwesome icons.
// Bootstrap 5 is added as an npm dependency in the layout phase.
import './assets/css/erpnext-style.css'
import './assets/fontawesome-free/css/all.min.css'

import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
