import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { GoogleOAuthProvider } from '@react-oauth/google'
import { GoogleReCaptchaProvider } from 'react-google-recaptcha-v3'
import './index.css'
import App from './App.jsx'

const GOOGLE_CLIENT_ID = "852841732506-f1bvs03hg92g9gl1k0f29nd9gjamoljk.apps.googleusercontent.com";
const RECAPTCHA_SITE_KEY = "6LcBi4wtAAAAABRj00TpA7AXsd0-9z8WJ52y5uOV";

createRoot(document.getElementById('root')).render(
  <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
    <StrictMode>
      <GoogleReCaptchaProvider reCaptchaKey={RECAPTCHA_SITE_KEY}>
        <App />
      </GoogleReCaptchaProvider>
    </StrictMode>
  </GoogleOAuthProvider>,
)
