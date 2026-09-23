// app/static/js/dashboard.js
let incomeExpenseChart = null;

async function loadDashboardData() {
  try {
    const res = await fetch('/api/dashboard/summary');
    if (!res.ok) return;
    const json = await res.json();
    if (json.status !== 'success') return;

    const data = json.data;

    // 1. Update Core Balance & KPI DOM Elements
    const fmt = (n) => '₹' + (Number(n) || 0).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2});

    const balanceElem = document.getElementById('dash-total-balance');
    if (balanceElem) balanceElem.textContent = fmt(data.total_balance);

    const currBalElem = document.getElementById('dash-current-balance');
    if (currBalElem) currBalElem.textContent = fmt(data.current_balance);

    const savingsElem = document.getElementById('dash-total-savings');
    if (savingsElem) savingsElem.textContent = fmt(data.total_savings);

    const incomeElem = document.getElementById('dash-monthly-income');
    if (incomeElem) incomeElem.textContent = fmt(data.monthly_income);

    const spendingElem = document.getElementById('dash-monthly-spending');
    if (spendingElem) spendingElem.textContent = fmt(data.monthly_spending);

    const scoreElem = document.getElementById('dash-credit-score');
    if (scoreElem) scoreElem.textContent = data.credit_score || '770';

    // 2. Render / Update Chart.js (Line + Bar Hybrid Analytics)
    const ctx = document.getElementById('incomeExpenseChart');
    if (ctx && window.Chart && data.chart_data) {
      const labels = data.chart_data.labels || [];
      const incomeData = data.chart_data.income || [];
      const expenseData = data.chart_data.expenses || [];

      if (incomeExpenseChart) {
        incomeExpenseChart.data.labels = labels;
        incomeExpenseChart.data.datasets[0].data = incomeData;
        incomeExpenseChart.data.datasets[1].data = expenseData;
        incomeExpenseChart.update('active');
      } else {
        const gradientIncome = ctx.getContext('2d').createLinearGradient(0, 0, 0, 300);
        gradientIncome.addColorStop(0, 'rgba(16, 185, 129, 0.35)');
        gradientIncome.addColorStop(1, 'rgba(16, 185, 129, 0.0)');

        const gradientExpense = ctx.getContext('2d').createLinearGradient(0, 0, 0, 300);
        gradientExpense.addColorStop(0, 'rgba(239, 68, 68, 0.35)');
        gradientExpense.addColorStop(1, 'rgba(239, 68, 68, 0.0)');

        incomeExpenseChart = new Chart(ctx, {
          type: 'line',
          data: {
            labels: labels,
            datasets: [
              {
                label: 'Income / Inflow',
                data: incomeData,
                borderColor: '#10b981',
                backgroundColor: gradientIncome,
                borderWidth: 3,
                pointBackgroundColor: '#10b981',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
                fill: true,
                tension: 0.35
              },
              {
                label: 'Expenses / Outflow',
                data: expenseData,
                borderColor: '#f43f5e',
                backgroundColor: gradientExpense,
                borderWidth: 3,
                pointBackgroundColor: '#f43f5e',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
                fill: true,
                tension: 0.35
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
              mode: 'index',
              intersect: false
            },
            plugins: {
              legend: {
                position: 'top',
                labels: {
                  color: '#94a3b8',
                  font: { family: 'Inter', size: 12, weight: '600' },
                  usePointStyle: true,
                  boxWidth: 8
                }
              },
              tooltip: {
                backgroundColor: 'rgba(15, 23, 42, 0.95)',
                titleColor: '#f8fafc',
                bodyColor: '#cbd5e1',
                borderColor: 'rgba(255,255,255,0.15)',
                borderWidth: 1,
                padding: 12,
                boxPadding: 6,
                callbacks: {
                  label: function(context) {
                    let label = context.dataset.label || '';
                    if (label) label += ': ';
                    if (context.parsed.y !== null) {
                      label += '₹' + Number(context.parsed.y).toLocaleString('en-IN', {minimumFractionDigits: 2});
                    }
                    return label;
                  }
                }
              }
            },
            scales: {
              x: {
                grid: { color: 'rgba(255,255,255,0.04)', drawBorder: false },
                ticks: { color: '#94a3b8', font: { family: 'Inter', size: 11 } }
              },
              y: {
                grid: { color: 'rgba(255,255,255,0.06)', drawBorder: false },
                ticks: {
                  color: '#94a3b8',
                  font: { family: 'Inter', size: 11 },
                  callback: (val) => '₹' + Number(val).toLocaleString('en-IN')
                }
              }
            }
          }
        });
      }
    }

    // 3. Render Recent Transactions List
    const txContainer = document.getElementById('tx-list-container');
    if (txContainer && data.recent_transactions) {
      if (data.recent_transactions.length === 0) {
        txContainer.innerHTML = `
          <div class="p-8 text-center text-slate-400">
            <div class="text-3xl mb-2">💸</div>
            <p class="font-medium text-sm text-slate-300">No transactions recorded yet</p>
            <p class="text-xs text-slate-500 mt-1">Make a transfer or payment to see your live financial activity.</p>
          </div>
        `;
      } else {
        txContainer.innerHTML = data.recent_transactions.map(tx => {
          const isCredit = (tx.tx_type || '').toLowerCase() === 'credit';
          const iconBg = isCredit ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20';
          const symbol = isCredit ? '↓' : '↑';
          const sign = isCredit ? '+' : '-';
          const amtColor = isCredit ? 'text-emerald-400' : 'text-slate-100';

          return `
            <div class="flex items-center justify-between p-3.5 hover:bg-slate-800/40 rounded-2xl transition border border-transparent hover:border-slate-800/80 mb-2">
              <div class="flex items-center space-x-3.5">
                <div class="w-10 h-10 rounded-xl border flex items-center justify-center font-bold text-base ${iconBg}">
                  ${symbol}
                </div>
                <div>
                  <div class="font-semibold text-sm text-white flex items-center space-x-2">
                    <span>${tx.merchant}</span>
                    <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 font-mono">${tx.reference_no}</span>
                  </div>
                  <div class="text-xs text-slate-400 mt-0.5 flex items-center space-x-2">
                    <span>${tx.timestamp}</span>
                    <span>•</span>
                    <span class="capitalize px-1.5 py-0.2 bg-slate-900 rounded text-slate-400">${tx.category}</span>
                  </div>
                </div>
              </div>
              <div class="text-right">
                <div class="font-bold text-sm ${amtColor} font-mono">
                  ${sign}₹${Number(tx.amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}
                </div>
                ${tx.balance_after !== null && tx.balance_after !== undefined ? `<div class="text-[10px] text-slate-500 font-mono mt-0.5">Bal: ₹${Number(tx.balance_after).toLocaleString('en-IN', {minimumFractionDigits: 2})}</div>` : '<div class="text-[10px] text-emerald-400 mt-0.5">Completed</div>'}
              </div>
            </div>
          `;
        }).join('');
      }
    }

  } catch (err) {
    console.error("Dashboard fetch error:", err);
  }
}

// Quick Money Transfer handler directly from Dashboard
async function handleQuickTransfer(event) {
  event.preventDefault();
  const form = event.target;
  const btn = form.querySelector('button[type="submit"]');
  const recipient = document.getElementById('quick-recipient')?.value;
  const amount = document.getElementById('quick-amount')?.value;
  const remark = document.getElementById('quick-remark')?.value || 'Instant Dashboard Transfer';
  const statusMsg = document.getElementById('quick-transfer-status');

  if (!recipient || !amount) {
    if (statusMsg) {
      statusMsg.textContent = 'Please fill in recipient and amount.';
      statusMsg.className = 'text-xs text-rose-400 mt-2 block';
    }
    return;
  }

  try {
    if (btn) btn.disabled = true;
    if (statusMsg) {
      statusMsg.textContent = 'Processing transaction securely...';
      statusMsg.className = 'text-xs text-blue-400 mt-2 block';
    }

    const res = await fetch('/api/transactions/transfer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recipient, amount: parseFloat(amount), remark })
    });
    const json = await res.json();

    if (res.ok && json.status === 'success') {
      if (statusMsg) {
        statusMsg.textContent = `✓ ${json.message}`;
        statusMsg.className = 'text-xs text-emerald-400 mt-2 block font-medium';
      }
      form.reset();
      // Immediately refresh all dashboard numbers, chart, and transaction list
      await loadDashboardData();
    } else {
      if (statusMsg) {
        statusMsg.textContent = `✗ ${json.error || 'Transfer failed.'}`;
        statusMsg.className = 'text-xs text-rose-400 mt-2 block font-medium';
      }
    }
  } catch (e) {
    if (statusMsg) {
      statusMsg.textContent = 'Network error during transfer.';
      statusMsg.className = 'text-xs text-rose-400 mt-2 block';
    }
  } finally {
    if (btn) btn.disabled = false;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadDashboardData();
  // Poll every 6 seconds to capture transactions made via AI chat or other tabs
  setInterval(loadDashboardData, 6000);

  const quickForm = document.getElementById('quick-transfer-form');
  if (quickForm) {
    quickForm.addEventListener('submit', handleQuickTransfer);
  }
});