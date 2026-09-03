const RECAPTCHA_SITE_KEY = "6LcBi4wtAAAAABRj00TpA7AXsd0-9z8WJ52y5uOV";

/**
 * Safely obtains a Google reCAPTCHA v3 response token for a given action.
 * If the reCAPTCHA script is still initializing when called, polls/waits up to maxWaitMs
 * dynamically checking both the hook instance and window.grecaptcha.
 *
 * @param {Function|undefined} executeRecaptcha - Function from useGoogleReCaptcha hook
 * @param {string} action - Action name ('login', 'register', 'forgot_password')
 * @param {number} maxWaitMs - Maximum milliseconds to wait for script readiness (default 5000ms)
 * @returns {Promise<string|null>} Resolved reCAPTCHA token or null if unavailable/timed out
 */
export const getReCaptchaToken = async (executeRecaptcha, action = 'submit', maxWaitMs = 5000) => {
  const startTime = Date.now();
  let attempt = 0;

  while (Date.now() - startTime < maxWaitMs) {
    attempt++;

    // 1. Try passed-in executeRecaptcha function if defined
    if (typeof executeRecaptcha === 'function') {
      try {
        console.log(`[reCAPTCHA] Poll attempt ${attempt}: calling executeRecaptcha('${action}')...`);
        const token = await executeRecaptcha(action);
        if (token && typeof token === 'string' && token.trim().length > 0) {
          console.log(`[reCAPTCHA] Poll attempt ${attempt}: Success via executeRecaptcha!`);
          return token.trim();
        }
      } catch (err) {
        console.warn(`[reCAPTCHA] Poll attempt ${attempt}: executeRecaptcha failed:`, err);
      }
    }

    // 2. Fallback to global window.grecaptcha directly if script loaded after hook mount
    if (window.grecaptcha && typeof window.grecaptcha.execute === 'function') {
      try {
        console.log(`[reCAPTCHA] Poll attempt ${attempt}: calling window.grecaptcha.execute('${action}')...`);
        const token = await window.grecaptcha.execute(RECAPTCHA_SITE_KEY, { action });
        if (token && typeof token === 'string' && token.trim().length > 0) {
          console.log(`[reCAPTCHA] Poll attempt ${attempt}: Success via window.grecaptcha!`);
          return token.trim();
        }
      } catch (err) {
        console.warn(`[reCAPTCHA] Poll attempt ${attempt}: window.grecaptcha.execute failed:`, err);
      }
    }

    console.log(`[reCAPTCHA] Poll attempt ${attempt}: Not ready yet (executeRecaptcha is ${typeof executeRecaptcha}, window.grecaptcha is ${typeof window.grecaptcha}). Waiting 200ms...`);
    await new Promise((resolve) => setTimeout(resolve, 200));
  }

  console.error(`[reCAPTCHA] Timed out after ${maxWaitMs}ms without obtaining token.`);
  return null;
};
