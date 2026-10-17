import { initializeApp } from 'https://www.gstatic.com/firebasejs/12.19.0/firebase-app.js';
import {
  GoogleAuthProvider,
  getAuth,
  onAuthStateChanged,
  signInWithPopup,
  signOut,
} from 'https://www.gstatic.com/firebasejs/12.19.0/firebase-auth.js';

const firebaseConfig = Object.freeze({
  apiKey: 'AIzaSyBVfRb76Vb69VxtPqBiuefsi8z8U7jmnV4',
  authDomain: 'baty-ac397.firebaseapp.com',
  projectId: 'baty-ac397',
  appId: '1:1064675162396:web:51363ca8da32ee11bf22d9',
});

const accountStatus = document.getElementById('account-status');
const signInButton = document.getElementById('google-sign-in');
const signOutButton = document.getElementById('google-sign-out');
const form = document.getElementById('hosted-ask-form');
const questionInput = document.getElementById('hosted-question');
const submitButton = document.getElementById('hosted-submit');
const answerOutput = document.getElementById('hosted-answer');

let currentUser = null;

function authFailure(error) {
  if (error?.code === 'auth/unauthorized-domain') {
    return 'This Vercel hostname is not yet allowed in Firebase Authentication. Add it to Firebase Authorized domains, then retry.';
  }
  if (error?.code === 'auth/popup-blocked') return 'The sign-in popup was blocked. Allow popups for this site and retry.';
  return `Google sign-in failed (${typeof error?.code === 'string' ? error.code : 'unknown error'}).`;
}

try {
  const auth = getAuth(initializeApp(firebaseConfig));
  const provider = new GoogleAuthProvider();
  signInButton.disabled = false;
  accountStatus.textContent = 'Not signed in. Sign-in is required before sending a question to Modal.';

  signInButton.addEventListener('click', async () => {
    signInButton.disabled = true;
    try {
      await signInWithPopup(auth, provider);
    } catch (error) {
      accountStatus.textContent = authFailure(error);
      signInButton.disabled = false;
    }
  });

  signOutButton.addEventListener('click', async () => {
    signOutButton.disabled = true;
    try {
      await signOut(auth);
    } catch (error) {
      accountStatus.textContent = authFailure(error);
      signOutButton.disabled = false;
    }
  });

  onAuthStateChanged(auth, (user) => {
    currentUser = user;
    signInButton.hidden = Boolean(user);
    signInButton.disabled = Boolean(user);
    signOutButton.hidden = !user;
    signOutButton.disabled = !user;
    submitButton.disabled = !user;
    accountStatus.textContent = user
      ? 'Signed in with Google. Your question is sent to Modal only when you submit it.'
      : 'Not signed in. Sign-in is required before sending a question to Modal.';
    if (!user) answerOutput.textContent = 'Sign in with Google to enable a question.';
  }, (error) => {
    accountStatus.textContent = `Firebase Authentication is unavailable (${typeof error?.code === 'string' ? error.code : 'unknown error'}).`;
    signInButton.disabled = true;
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const question = questionInput.value.trim();
    if (!currentUser || !question) {
      answerOutput.textContent = 'Sign in and enter a question first.';
      return;
    }
    if (new TextEncoder().encode(question).length > 16_000) {
      answerOutput.textContent = 'Keep the question below 16 KiB of UTF-8 text.';
      return;
    }

    submitButton.disabled = true;
    signOutButton.disabled = true;
    answerOutput.textContent = 'Sending your question to Modal for cloud inference…';
    try {
      const idToken = await currentUser.getIdToken();
      const response = await fetch('/api/modal/assistant', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${idToken}`},
        cache: 'no-store',
        body: JSON.stringify({question}),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.error || `The hosted assistant could not answer (${response.status}).`);
      const limitations = Array.isArray(result.limitations) ? result.limitations.filter((item) => typeof item === 'string') : [];
      answerOutput.textContent = [
        typeof result.answer === 'string' ? result.answer : 'No answer was returned.',
        `Answer basis: ${typeof result.answer_basis === 'string' ? result.answer_basis : 'general_model_knowledge_unverified'}`,
        ...limitations,
      ].join('\n\n');
    } catch (error) {
      answerOutput.textContent = error?.message || 'The hosted assistant request failed. Please retry.';
    } finally {
      submitButton.disabled = !currentUser;
      signOutButton.disabled = !currentUser;
    }
  });
} catch (error) {
  accountStatus.textContent = `Firebase could not initialize (${typeof error?.code === 'string' ? error.code : 'unknown error'}).`;
  signInButton.disabled = true;
}
