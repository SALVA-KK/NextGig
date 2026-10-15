import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';

export const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "AIzaSyAN9nl9RROfbf7zBNaTeGSNK31LxsGNflM",
  authDomain: "nextgig-d36a8.firebaseapp.com",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "nextgig-d36a8",
  storageBucket: "nextgig-d36a8.firebasestorage.app",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "852841732506",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || "1:852841732506:web:f6a6f8b9cae08ebe8d8223",
  vapidKey: import.meta.env.VITE_FIREBASE_VAPID_KEY || "",
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export default app;
