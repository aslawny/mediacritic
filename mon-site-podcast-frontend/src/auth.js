import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: "AIzaSyAtzGIL3IJS6HhoE_yB6T3EHE9iVyj1wt0",
  authDomain: "MediaCritic.firebaseapp.com",
  projectId: "MediaCritic",
  storageBucket: "MediaCritic.firebasestorage.app",
  messagingSenderId: "519991200690",
  appId: "1:519991200690:web:8a0e778afe19f16ec9b2ab"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

export { app, auth, db };

