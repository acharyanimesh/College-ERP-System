import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

// Same load order as base.html: erpnext-style.css, FontAwesome, Bootstrap 5.
import './assets/css/erpnext-style.css'
import './assets/fontawesome-free/css/all.min.css'
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap/dist/js/bootstrap.bundle.min.js'

import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
