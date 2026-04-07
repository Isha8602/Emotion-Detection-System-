document.addEventListener('DOMContentLoaded', () => {
    loadHistoricalCalls();
    loadEmotionDistribution();
    loadUsers();

    document.getElementById('searchInput').addEventListener('input', filterHistoricalCalls);
});

// ==================== Historical Calls ====================
let allHistoricalCalls = [];

function loadHistoricalCalls() {
    fetch('/api/reports')
        .then(res => res.json())
        .then(data => {
            allHistoricalCalls = data;
            renderHistoricalCalls(data);
        })
        .catch(err => console.error('Error loading historical calls:', err));
}

function renderHistoricalCalls(calls) {
    const tbody = document.querySelector('#historyTable tbody');
    tbody.innerHTML = '';
    calls.forEach(call => {
        const row = tbody.insertRow();
        row.insertCell(0).textContent = formatDate(call.start_time);
        row.insertCell(1).textContent = call.agent_name;
        row.insertCell(2).textContent = call.customer_name;
        row.insertCell(3).innerHTML = `<span class="emotion-badge ${call.overall_sentiment}">${call.overall_sentiment}</span>`;
        row.insertCell(4).textContent = formatDuration(call.duration);
        const detailsBtn = document.createElement('button');
        detailsBtn.textContent = 'View';
        detailsBtn.onclick = () => viewDetails(call);
        row.insertCell(5).appendChild(detailsBtn);
    });
}

function filterHistoricalCalls() {
    const term = document.getElementById('searchInput').value.toLowerCase();
    const filtered = allHistoricalCalls.filter(call =>
        call.agent_name.toLowerCase().includes(term) ||
        call.customer_name.toLowerCase().includes(term) ||
        formatDate(call.start_time).toLowerCase().includes(term) ||
        call.overall_sentiment.toLowerCase().includes(term)
    );
    renderHistoricalCalls(filtered);
}

function viewDetails(call) {
    alert(`Call ID: ${call.id}\nCustomer: ${call.customer_name}\nAgent: ${call.agent_name}\nEmotion: ${call.overall_sentiment}\nEmotion Peaks: ${call.emotion_peaks}\nEvents: ${call.emotion_events}`);
}

// ==================== Emotion Distribution Charts ====================
let pieChart = null;
let donutChart = null;

function loadEmotionDistribution() {
    fetch('/api/emotion_distribution')
        .then(res => res.json())
        .then(distribution => {
            const labels = Object.keys(distribution);
            const data = Object.values(distribution);
            const backgroundColor = [
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF', '#7C4DFF'
            ];

            // Pie chart
            const pieCtx = document.getElementById('emotionPieChart').getContext('2d');
            if (pieChart) pieChart.destroy();
            pieChart = new Chart(pieCtx, {
                type: 'pie',
                data: { labels, datasets: [{ data, backgroundColor }] },
                options: { responsive: true, maintainAspectRatio: true }
            });

            // Donut chart (same as pie but with cutout)
            const donutCtx = document.getElementById('emotionDonutChart').getContext('2d');
            if (donutChart) donutChart.destroy();
            donutChart = new Chart(donutCtx, {
                type: 'doughnut',
                data: { labels, datasets: [{ data, backgroundColor }] },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    cutout: '50%'   // creates the donut hole
                }
            });
        })
        .catch(err => console.error('Error loading emotion distribution:', err));
}

// ==================== Registered Users ====================
function loadUsers() {
    fetch('/api/users')
        .then(res => res.json())
        .then(users => {
            const tbody = document.querySelector('#usersTable tbody');
            tbody.innerHTML = '';
            users.forEach(user => {
                const row = tbody.insertRow();
                row.insertCell(0).textContent = user.name || '—';
                row.insertCell(1).textContent = user.email;
                row.insertCell(2).textContent = user.role;
                row.insertCell(3).textContent = formatDate(user.created_at);
            });
        })
        .catch(err => console.error('Error loading users:', err));
}

// ==================== Export Functions ====================
window.exportCSV = function() {
    let csvContent = "Date,Agent,Customer,Emotion,Duration\n";
    allHistoricalCalls.forEach(call => {
        csvContent += `${formatDate(call.start_time)},${call.agent_name},${call.customer_name},${call.overall_sentiment},${formatDuration(call.duration)}\n`;
    });
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'historical_calls.csv';
    link.click();
    URL.revokeObjectURL(link.href);
};

window.exportPDF = function() {
    window.print();
};

// ========== Helpers ==========
function formatDuration(seconds) {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatDate(isoString) {
    if (!isoString) return '—';
    const date = new Date(isoString);
    return date.toLocaleString();
}