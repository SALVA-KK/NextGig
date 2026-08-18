import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';

const firebaseConfig = {
  apiKey: "AIzaSyAN9nl9RROfbf7zBNaTeGSNK31LxsGNflM",
  authDomain: "nextgig-d36a8.firebaseapp.com",
  projectId: "nextgig-d36a8",
  storageBucket: "nextgig-d36a8.firebasestorage.app",
  messagingSenderId: "852841732506",
  appId: "1:852841732506:web:f6a6f8b9cae08ebe8d8223",
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export default app;
