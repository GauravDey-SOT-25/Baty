const MODAL_ASSISTANT_URL = 'https://gauravdey2020--cyber-qwen-modal-preview-inference-api.us-east.modal.run/api/assistant';
const MAX_QUESTION_BYTES = 16_000;
const MAX_FIREBASE_TOKEN_CHARS = 8_192;
const UPSTREAM_TIMEOUT_MS = 275_000;

export const config = {
  api: {bodyParser: {sizeLimit: '20kb'}},
};

const ERROR_MESSAGES = Object.freeze({
  401: 'Firebase sign-in is invalid or expired. Sign in again.',
  403: 'This account is not authorized for hosted inference.',
  422: 'The hosted model rejected the question format.',
  429: 'The hosted model rate limit was reached. Wait a minute and retry.',
  503: 'The Modal model is temporarily unavailable.',
});

export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store, max-age=0');
  res.setHeader('X-Content-Type-Options', 'nosniff');

  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({error: 'Only POST is supported.'});
  }

  if (!String(req.headers['content-type'] || '').toLowerCase().startsWith('application/json')) {
    return res.status(415).json({error: 'Send a JSON request.'});
  }

  const authorization = req.headers.authorization;
  if (typeof authorization !== 'string' || !authorization.startsWith('Bearer ')) {
    return res.status(401).json({error: 'Sign in with Google to use the hosted model.'});
  }
  const idToken = authorization.slice(7).trim();
  if (!idToken || idToken.length > MAX_FIREBASE_TOKEN_CHARS) {
    return res.status(401).json({error: 'Firebase sign-in token is missing or invalid.'});
  }

  const question = req.body && typeof req.body.question === 'string' ? req.body.question.trim() : '';
  if (!question || question.length > 8_000 || Buffer.byteLength(question, 'utf8') > MAX_QUESTION_BYTES) {
    return res.status(422).json({error: 'Enter a question within the 8,000 character limit.'});
  }

  const modalKey = process.env.MODAL_PROXY_KEY?.trim();
  const modalSecret = process.env.MODAL_PROXY_SECRET?.trim();
  if (!modalKey || !modalSecret) {
    return res.status(503).json({error: 'Hosted inference is not configured. Set its Modal credentials in Vercel.'});
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);
  try {
    const upstream = await fetch(MODAL_ASSISTANT_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${idToken}`,
        'Modal-Key': modalKey,
        'Modal-Secret': modalSecret,
      },
      body: JSON.stringify({question}),
      cache: 'no-store',
      signal: controller.signal,
    });

    if (!upstream.ok) {
      const status = ERROR_MESSAGES[upstream.status] ? upstream.status : 502;
      return res.status(status).json({error: ERROR_MESSAGES[upstream.status] || 'The hosted inference request failed.'});
    }

    const result = await upstream.json();
    if (!result || typeof result.answer !== 'string' || result.answer.length > 30_000) {
      return res.status(502).json({error: 'The hosted model returned an invalid response.'});
    }

    const limitations = Array.isArray(result.limitations)
      ? result.limitations.filter((item) => typeof item === 'string').slice(0, 8).map((item) => item.slice(0, 300))
      : [];
    if (!limitations.some((item) => /unverified|may be wrong/i.test(item))) {
      limitations.push('Generated content is unverified and may be wrong.');
    }
    return res.status(200).json({
      answer: result.answer,
      answer_basis: typeof result.answer_basis === 'string' ? result.answer_basis : 'general_model_knowledge_unverified',
      ...(typeof result.model === 'string' ? {model: result.model} : {}),
      limitations,
    });
  } catch (error) {
    const timedOut = error?.name === 'AbortError';
    return res.status(timedOut ? 504 : 502).json({
      error: timedOut ? 'The hosted model took too long. Please retry.' : 'Could not reach the Modal inference service.',
    });
  } finally {
    clearTimeout(timeout);
  }
}
