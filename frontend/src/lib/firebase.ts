import { initializeApp, type FirebaseApp } from 'firebase/app';
import { getAuth, type Auth } from 'firebase/auth';
import { getStorage, type FirebaseStorage } from 'firebase/storage';
import { getFirestore, type Firestore } from 'firebase/firestore';

const config = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

if (!config.apiKey || !config.projectId) {
  throw new Error(
    'Firebase web SDK config is missing. The deploy workflow fetches this via ' +
      '`firebase apps:sdkconfig WEB`; if it failed silently the project has zero or ' +
      'multiple Web apps. Set the FIREBASE_WEB_APP_ID GitHub Variable to disambiguate.',
  );
}

export const app: FirebaseApp = initializeApp(config);
export const auth: Auth = getAuth(app);
export const db: Firestore = getFirestore(app);
export const storage: FirebaseStorage = getStorage(app);
