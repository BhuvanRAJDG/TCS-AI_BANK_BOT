// app/static/js/dashboard.js
document.addEventListener('DOMContentLoaded', async () => {
  try {
    const res = await fetch('/api/dashboard/summary');
    if (!res.ok) return;
    const json = await res.json();
    if (json.status !== 'success') return;

    const data = json.data;

    // Update DOM elements if present
    const balanceElem = document.getElementById('dash-total-balance');
    if (balanceElem) balanceElem.textContent = '₹' + data.total_balance.toLocaleString('en-IN', {minimumFractionDigits: 2});

    const currBalElem = document.getElementById('dash-current-balance');
    if (currBalElem) currBalElem.textContent = '₹' + data.current_balance.toLocaleString('en-IN', {minimumFractionDigits: 2});

    const savingsElem = document.getElementById('dash-total-savings');
    if (savingsElem) savingsElem.textContent = '₹' + data.total_savings.toLocaleString('en-IN', {minimumFractionDigits: 2});

    const spendingElem = document.getElementById('dash-monthly-spending');
    if (spendingElem) spendingElem.textContent = '₹' + data.monthly_spending.toLocaleString('en-IN', {minimumFractionDigits: 2});

    const scoreElem = document.getElementById('dash-credit-score');
    if (scoreElem) scoreElem.textContent = data.credit_score;

    // Render Chart.js if canvas exists
    const ctx = document.getElementById('incomeExpenseChart');
    if (ctx && window.Chart && data.chart_data) {
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: data.chart_data.labels,
          datasets: [
            {
              label: 'Income',
              data: data.chart_data.income,
              borderColor: '#10b981',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              fill: true,
              tension: 0.4
            },
            {
              label: 'Expenses',
              data: data.chart_data.expenses,
              borderColor: '#ef4444',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              fill: true,
              tension: 0.4
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { labels: { color: '#94a3b8' } }
          },
          scales: {
            x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } }
          }
        }
      });
    }
  } catch (err) {
    console.error("Dashboard JS error:", err);
  }
});
