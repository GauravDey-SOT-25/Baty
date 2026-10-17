const imageInput = document.getElementById('ocr-image');
const extractButton = document.getElementById('extract-image-text');
const ocrStatus = document.getElementById('ocr-status');
const ocrOutput = document.getElementById('ocr-output');
const useOcrButton = document.getElementById('use-ocr-text');
let extractedText = '';

extractButton.addEventListener('click', async () => {
  const image = imageInput.files?.[0];
  extractedText = '';
  useOcrButton.disabled = true;
  ocrOutput.textContent = 'Extracted text will appear here.';
  if (!image) {
    ocrStatus.textContent = 'Choose an image first.';
    return;
  }
  if (image.size < 1 || image.size > 4 * 1024 * 1024) {
    ocrStatus.textContent = 'Choose a non-empty image smaller than 4 MiB.';
    return;
  }
  ocrStatus.textContent = 'Extracting locally with Apple Vision…';
  try {
    const dataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error('Could not read the selected image.'));
      reader.onload = () => resolve(reader.result);
      reader.readAsDataURL(image);
    });
    const encoded = String(dataUrl).split(',', 2)[1];
    const response = await fetch('/api/ocr', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_base64: encoded }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'OCR failed.');
    extractedText = result.text || '';
    ocrOutput.textContent = extractedText || 'No readable text was found in this image.';
    ocrStatus.textContent = extractedText ? 'Text extracted locally. Review it before use.' : 'No text recognized.';
    useOcrButton.disabled = !extractedText;
  } catch (error) {
    ocrStatus.textContent = error?.message || 'Local OCR is unavailable.';
  }
});

useOcrButton.addEventListener('click', () => {
  if (!extractedText) return;
  const question = document.getElementById('question');
  const addition = `\n\n[Text extracted locally from an image; verify accuracy]\n${extractedText}`;
  if (question.value.length + addition.length > 8000) {
    ocrStatus.textContent = 'The extracted text is too long to add; shorten the question or extracted text.';
    return;
  }
  question.value = `${question.value.trim()}${addition}`.trim();
  ocrStatus.textContent = 'Added to the question. Review it before sending.';
  question.focus();
});
