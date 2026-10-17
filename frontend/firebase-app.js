import { initializeApp } from 'https://www.gstatic.com/firebasejs/12.19.0/firebase-app.js';
import {
  GoogleAuthProvider,
  getAuth,
  onAuthStateChanged,
  signInWithPopup,
  signOut,
} from 'https://www.gstatic.com/firebasejs/12.19.0/firebase-auth.js';
import {
  get,
  getDatabase,
  limitToLast,
  orderByChild,
  push,
  query,
  ref,
  remove,
  serverTimestamp,
  set,
} from 'https://www.gstatic.com/firebasejs/12.19.0/firebase-database.js';

// Firebase web configuration is public client metadata, not an Admin credential.
// Database access must remain protected by database.rules.json.
const firebaseConfig = Object.freeze({
  apiKey: 'AIzaSyBVfRb76Vb69VxtPqBiuefsi8z8U7jmnV4',
  authDomain: 'baty-ac397.firebaseapp.com',
  databaseURL: 'https://baty-ac397-default-rtdb.firebaseio.com',
  projectId: 'baty-ac397',
  storageBucket: 'baty-ac397.firebasestorage.app',
  messagingSenderId: '1064675162396',
  appId: '1:1064675162396:web:51363ca8da32ee11bf22d9',
});

const accountStatus = document.getElementById('account-status');
const syncStatus = document.getElementById('cloud-sync-status');
const signInButton = document.getElementById('google-sign-in');
const signOutButton = document.getElementById('google-sign-out');
const syncToggle = document.getElementById('cloud-sync');
const deleteButton = document.getElementById('delete-cloud-history');
const historyList = document.getElementById('cloud-history');

let currentUser = null;
let cloudSyncEnabled = false;
let database = null;

function firebaseErrorCode(error) {
  return typeof error?.code === 'string' ? error.code : 'unknown error';
}

function showHistory(entries) {
  historyList.replaceChildren();
  for (const entry of entries) {
    const row = document.createElement('li');
    const question = document.createElement('p');
    const answer = document.createElement('p');
    const metadata = document.createElement('small');
    question.textContent = `You: ${entry.question}`;
    answer.textContent = `Assistant: ${entry.answer}`;
    const basis = typeof entry.answerBasis === 'string' ? entry.answerBasis : 'unverified';
    const when = Number.isFinite(Number(entry.createdAt))
      ? new Date(Number(entry.createdAt)).toLocaleString()
      : 'time unavailable';
    metadata.textContent = `${basis} · ${when}`;
    row.append(question, answer, metadata);
    historyList.append(row);
  }
}

function userHistoryRef() {
  return ref(database, `users/${currentUser.uid}/assistantHistory`);
}

async function refreshHistory() {
  if (!currentUser || !cloudSyncEnabled) return;
  syncStatus.textContent = 'Loading your saved assistant history from Firebase…';
  try {
    const result = await get(query(userHistoryRef(), orderByChild('createdAt'), limitToLast(25)));
    const values = result.val() || {};
    const entries = Object.values(values).sort((left, right) => (left.createdAt || 0) - (right.createdAt || 0));
    showHistory(entries);
    syncStatus.textContent = `Cloud sync is on. Showing up to ${entries.length} recent saved assistant exchanges.`;
  } catch (error) {
    syncStatus.textContent = `Could not read Firebase history (${firebaseErrorCode(error)}). Check database rules and your connection.`;
  }
}

function configureFirebase() {
  try {
    const app = initializeApp(firebaseConfig);
    const auth = getAuth(app);
    database = getDatabase(app);
    const provider = new GoogleAuthProvider();

    signInButton.disabled = false;
    accountStatus.textContent = 'Not signed in. Local analysis remains available.';

    signInButton.addEventListener('click', async () => {
      signInButton.disabled = true;
      try {
        await signInWithPopup(auth, provider);
      } catch (error) {
        accountStatus.textContent = error?.code === 'auth/unauthorized-domain'
          ? 'This app address is not authorized in Firebase Authentication yet.'
          : `Google sign-in failed (${firebaseErrorCode(error)}). Check that Google is enabled in Firebase Authentication.`;
      } finally {
        signInButton.disabled = false;
      }
    });

    signOutButton.addEventListener('click', async () => {
      try {
        await signOut(auth);
      } catch (error) {
        accountStatus.textContent = `Sign-out failed (${firebaseErrorCode(error)}). Please retry.`;
      }
    });

    syncToggle.addEventListener('change', async () => {
      if (!currentUser) {
        syncToggle.checked = false;
        syncStatus.textContent = 'Sign in before enabling cloud sync.';
        return;
      }
      cloudSyncEnabled = syncToggle.checked;
      if (cloudSyncEnabled) {
        await refreshHistory();
      } else {
        syncStatus.textContent = 'Cloud sync is off. New assistant exchanges stay on this computer.';
      }
    });

    deleteButton.addEventListener('click', async () => {
      if (!currentUser || !window.confirm('Permanently delete all assistant history saved in your Firebase account?')) return;
      deleteButton.disabled = true;
      try {
        await remove(userHistoryRef());
        showHistory([]);
        syncStatus.textContent = 'Your saved cloud assistant history was deleted.';
      } catch (error) {
        syncStatus.textContent = `Could not delete Firebase history (${firebaseErrorCode(error)}). Check database rules and retry.`;
      } finally {
        deleteButton.disabled = !currentUser;
      }
    });

    onAuthStateChanged(auth, (user) => {
      currentUser = user;
      cloudSyncEnabled = false;
      syncToggle.checked = false;
      syncToggle.disabled = !user;
      deleteButton.disabled = !user;
      signInButton.classList.toggle('hidden', Boolean(user));
      signOutButton.classList.toggle('hidden', !user);
      if (user) {
        accountStatus.textContent = `Signed in as ${user.displayName || user.email || 'Google user'}.`;
        syncStatus.textContent = 'Cloud sync is off. Enable it above to load and save Learning assistant history.';
      } else {
        accountStatus.textContent = 'Not signed in. Local analysis remains available.';
        syncStatus.textContent = 'Cloud sync is off.';
        showHistory([]);
      }
      window.dispatchEvent(new CustomEvent('firebase-auth-state', {
        detail: user ? { uid: user.uid, displayName: user.displayName || '', email: user.email || '' } : null,
      }));
    }, (error) => {
      accountStatus.textContent = `Firebase Authentication is unavailable (${firebaseErrorCode(error)}). Local analysis remains available.`;
      signInButton.disabled = true;
    });

    window.firebaseCloud = Object.freeze({
      async getIdToken() {
        if (!currentUser) throw new Error('Google sign-in is required.');
        return currentUser.getIdToken();
      },
      async saveAssistantExchange({ question, answer, answerBasis }) {
        if (!currentUser || !cloudSyncEnabled) return false;
        if (typeof question !== 'string' || typeof answer !== 'string') return false;
        const entry = push(userHistoryRef());
        await set(entry, {
          question: question.slice(0, 8000),
          answer: answer.slice(0, 12000),
          answerBasis: typeof answerBasis === 'string' ? answerBasis.slice(0, 80) : 'unverified',
          createdAt: serverTimestamp(),
        });
        await refreshHistory();
        return true;
      },
    });
  } catch (error) {
    accountStatus.textContent = `Firebase could not initialize (${firebaseErrorCode(error)}). Local analysis remains available.`;
    signInButton.disabled = true;
    syncToggle.disabled = true;
  }
}

configureFirebase();
