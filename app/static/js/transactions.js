// app/static/js/transactions.js
document.addEventListener('DOMContentLoaded', async () => {
  const container = document.getElementById('tx-list-container');
  if (!container) return;

  try {
    const res = await fetch('/api/transactions');
    if (!res.ok) return;
    const json = await res.json();
    if (json.status !== 'success') return;

    const items = json.data.items || [];
    if (items.length === 0) {
      container.innerHTML = '<p class="text-slate-400 py-4">No transactions found.</p>';
      return;
    }

    container.innerHTML = items.map(tx => `
      <div class="flex items-center justify-between p-4 glass-card mb-2 hover:bg-slate-800/50 transition cursor-pointer" onclick="window.location.href='/transactions/${tx.id}'">
        <div class="flex items-center space-x-3">
          <div class="w-10 h-10 rounded-full flex items-center justify-center ${tx.tx_type === 'credit' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}">
            ${tx.tx_type === 'credit' ? '↓' : '↑'}
          </div>
          <div>
            <div class="font-semibold text-slate-100">${tx.merchant}</div>
            <div class="text-xs text-slate-400">${tx.timestamp} • <span class="capitalize">${tx.category}</span></div>
          </div>
        </div>
        <div class="text-right">
          <div class="font-bold ${tx.tx_type === 'credit' ? 'text-emerald-400' : 'text-slate-200'}">
            ${tx.tx_type === 'credit' ? '+' : '-'}₹${tx.amount.toLocaleString('en-IN', {minimumFractionDigits: 2})}
          </div>
          <div class="text-xs text-slate-500 capitalize">${tx.status}</div>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error("Transactions fetch error:", err);
  }
});
