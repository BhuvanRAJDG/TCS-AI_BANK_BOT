// app/static/js/chat.js
document.addEventListener('DOMContentLoaded', () => {
  const chatForm = document.getElementById('chat-form');
  const chatInput = document.getElementById('chat-input');
  const messagesContainer = document.getElementById('chat-messages');
  const typingIndicator = document.getElementById('typing-indicator');
  const latencyBadge = document.getElementById('latency-badge');

  if (!chatForm || !messagesContainer) return;

  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = chatInput.value.trim();
    if (!query) return;

    // Append user message
    appendMessage('user', query);
    chatInput.value = '';

    // Show typing indicator
    if (typingIndicator) typingIndicator.classList.remove('hidden');
    const startTime = Date.now();

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: query })
      });

      const latency = Date.now() - startTime;
      if (latencyBadge) latencyBadge.textContent = `${latency} ms`;

      if (typingIndicator) typingIndicator.classList.add('hidden');

      if (!res.ok) {
        appendMessage('assistant', 'Sorry, I encountered an error processing your query. Please try again.');
        return;
      }

      const data = await res.json();
      const answer = data.response || data.message || "I've processed your request.";
      const citations = data.citations || [];
      
      appendMessage('assistant', answer, citations, data.intent);
    } catch (err) {
      if (typingIndicator) typingIndicator.classList.add('hidden');
      appendMessage('assistant', 'Network error. Please check your connection.');
    }
  });

  window.sendSuggestedPrompt = (promptText) => {
    if (chatInput) {
      chatInput.value = promptText;
      chatForm.dispatchEvent(new Event('submit'));
    }
  };

  function appendMessage(sender, text, citations = [], intent = null) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `flex ${sender === 'user' ? 'justify-end' : 'justify-start'} mb-4`;
    
    let citationHtml = '';
    if (citations && citations.length > 0) {
      citationHtml = `<div class="mt-2 pt-2 border-t border-slate-700 text-xs text-slate-400">
        <strong>Sources:</strong> ${citations.map(c => `<span class="bg-slate-700 px-1.5 py-0.5 rounded text-blue-300 ml-1">${c}</span>`).join('')}
      </div>`;
    }

    let intentBadge = '';
    if (intent && sender === 'assistant') {
      intentBadge = `<span class="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-blue-900/60 text-blue-300 mb-1 inline-block">Intent: ${intent}</span><br/>`;
    }

    msgDiv.innerHTML = `
      <div class="max-w-[80%] rounded-2xl px-4 py-3 ${sender === 'user' ? 'bg-blue-600 text-white rounded-br-none' : 'glass-card text-slate-100 rounded-bl-none'}">
        ${intentBadge}
        <div>${escapeHtml(text)}</div>
        ${citationHtml}
      </div>
    `;
    messagesContainer.appendChild(msgDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
});
