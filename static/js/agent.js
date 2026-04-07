// static/js/agent.js

let isMuted = false;
let isOnHold = false;
let callActive = false;
let callTimerInterval;
let callSeconds = 0;
let timelineData = [];
let emotionEvents = [];    // this stores the emotion data
let customerName = "";
let gaugeChart, timelineChart;

const callSetupDiv = document.getElementById('callSetup');
const liveCallPanel = document.getElementById('liveCallPanel');
const afterCallSummary = document.getElementById('afterCallSummary');
const startCallBtn = document.getElementById('startCallBtn');
const generateReportBtn = document.getElementById('generateReportBtn');

document.addEventListener('DOMContentLoaded', () => {
    initGauge();
    initTimeline();
    setupCallControls();
    startCallBtn.addEventListener('click', startCall);
    generateReportBtn.addEventListener('click', generateReport);
    if (typeof socket !== 'undefined') {
        socket.on('emotion_update', (data) => {
            if (callActive) updateEmotion(data.emotion, data.probabilities);
        });
    }
});

function initGauge() {
    const ctx = document.getElementById('gaugeChart').getContext('2d');
    gaugeChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: emotionLabels.slice(0,5),
            datasets: [{
                data: new Array(5).fill(0),
                backgroundColor: ['#ff6384', '#36a2eb', '#ffce56', '#cc65cf', '#aaa']
            }]
        },
        options: { cutout: '70%', plugins: { tooltip: { enabled: false }, legend: { display: false } } }
    });
}

function updateGauge(probabilities) {
    gaugeChart.data.datasets[0].data = probabilities.slice(0,5);
    gaugeChart.update();
}

function initTimeline() {
    const ctx = document.getElementById('timelineChart').getContext('2d');
    timelineChart = new Chart(ctx, {
        type: 'line',
        data: { labels: [], datasets: [{
            label: 'Emotion Index',
            data: [],
            borderColor: '#36a2eb',
            tension: 0.3,
            fill: false
        }] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: { y: { beginAtZero: true, max: 7, title: { display: true, text: 'Emotion (0-7)' } } }
        }
    });
}

function updateTimeline(emotionIndex) {
    timelineData.push(emotionIndex);
    if (timelineData.length > 30) timelineData.shift();
    timelineChart.data.datasets[0].data = timelineData;
    timelineChart.update();
}

function startCall() {
    const customerInput = document.getElementById('customerName');
    if (!customerInput.value.trim()) {
        alert('Please enter a customer name or call ID');
        return;
    }
    customerName = customerInput.value.trim();
    document.getElementById('customerDisplay').innerText = `Customer: ${customerName}`;

    callActive = true;
    callSeconds = 0;
    timelineData = [];
    emotionEvents = [];      // reset emotion events
    console.log("Call started. emotionEvents cleared.");

    updateTimerDisplay();
    clearInterval(callTimerInterval);
    callTimerInterval = setInterval(() => {
        if (callActive) {
            callSeconds++;
            updateTimerDisplay();
        }
    }, 1000);

    callSetupDiv.style.display = 'none';
    liveCallPanel.style.display = 'block';
    afterCallSummary.style.display = 'none';

    document.getElementById('muteBtn').disabled = false;
    document.getElementById('holdBtn').disabled = false;
    document.getElementById('endBtn').disabled = false;

    document.getElementById('currentEmotion').innerText = 'Neutral';
    document.getElementById('currentEmotion').className = 'emotion-badge neutral';

    if (window.emulationInterval) clearInterval(window.emulationInterval);
    window.emulationInterval = setInterval(() => {
        if (callActive) simulateEmotionUpdate();
    }, 5000);
}

function updateEmotion(emotion, probabilities) {
    if (!callActive) return;
    const emotionIndex = emotionLabels.indexOf(emotion);
    if (emotionIndex === -1) return;

    const event = {
        timestamp: callSeconds,
        emotion: emotion,
        emotionIndex: emotionIndex,
        probabilities: probabilities || null
    };
    emotionEvents.push(event);
    console.log("Emotion captured:", event);

    document.getElementById('currentEmotion').innerText = emotion;
    document.getElementById('currentEmotion').className = `emotion-badge ${emotion}`;
    if (probabilities) updateGauge(probabilities);
    updateTimeline(emotionIndex);
    updateSuggestion(emotion);
    updateSelfFeedback(emotionIndex);
}

function updateSuggestion(emotion) {
    const suggestions = {
        angry: "Remain calm and empathize. Use a soothing tone.",
        happy: "Acknowledge their positive mood. Keep the conversation light.",
        sad: "Show compassion. Offer support and understanding.",
        fearful: "Reassure the customer. Explain clearly and calmly.",
        surprised: "Address their surprise promptly. Provide clear information.",
        neutral: "Maintain a friendly tone. Ask if they need any help.",
        calm: "Great! Keep up the good work.",
        disgust: "Stay professional. Try to understand their concern."
    };
    document.getElementById('suggestion').innerText = suggestions[emotion] || "Listen carefully and respond appropriately.";
}

function updateSelfFeedback(emotionIndex) {
    const feedbacks = ["You sound rushed.", "Your tone is calm.", "You seem stressed."];
    const idx = Math.floor(Math.random() * feedbacks.length);
    document.getElementById('selfTone').innerText = feedbacks[idx];
}

function simulateEmotionUpdate() {
    const randomIdx = Math.floor(Math.random() * emotionLabels.length);
    const emotion = emotionLabels[randomIdx];
    const probs = new Array(emotionLabels.length).fill(0.05);
    probs[randomIdx] = 0.6;
    updateEmotion(emotion, probs);
}

function updateTimerDisplay() {
    const mins = Math.floor(callSeconds / 60);
    const secs = callSeconds % 60;
    document.getElementById('callDuration').innerText = `${mins.toString().padStart(2,'0')}:${secs.toString().padStart(2,'0')}`;
}

function setupCallControls() {
    const muteBtn = document.getElementById('muteBtn');
    const holdBtn = document.getElementById('holdBtn');
    const endBtn = document.getElementById('endBtn');

    muteBtn.addEventListener('click', toggleMute);
    holdBtn.addEventListener('click', toggleHold);
    endBtn.addEventListener('click', endCall);
}

function toggleMute() {
    if (!callActive) return;
    isMuted = !isMuted;
    const muteBtn = document.getElementById('muteBtn');
    muteBtn.textContent = isMuted ? 'Unmute' : 'Mute';
    muteBtn.style.backgroundColor = isMuted ? '#e67e22' : '#f1c40f';
    if (typeof socket !== 'undefined') {
        socket.emit('call_control', { action: 'mute', state: isMuted, callId: customerName || 'unknown' });
    }
    showNotification(isMuted ? 'Microphone muted' : 'Microphone unmuted');
}

function toggleHold() {
    if (!callActive) return;
    isOnHold = !isOnHold;
    const holdBtn = document.getElementById('holdBtn');
    holdBtn.textContent = isOnHold ? 'Resume' : 'Hold';
    holdBtn.style.backgroundColor = isOnHold ? '#27ae60' : '#95a5a6';
    if (typeof socket !== 'undefined') {
        socket.emit('call_control', { action: 'hold', state: isOnHold, callId: customerName || 'unknown' });
    }
    showNotification(isOnHold ? 'Call on hold' : 'Call resumed');
}

function endCall() {
    if (!callActive) return;
    callActive = false;
    clearInterval(callTimerInterval);
    if (window.emulationInterval) clearInterval(window.emulationInterval);

    document.getElementById('muteBtn').disabled = true;
    document.getElementById('holdBtn').disabled = true;
    document.getElementById('endBtn').disabled = true;

    liveCallPanel.style.display = 'none';
    afterCallSummary.style.display = 'block';
    document.getElementById('summaryCustomerName').innerText = customerName;
    document.getElementById('summaryDuration').innerText = formatDuration(callSeconds);

    // Calculate overall sentiment from emotionEvents
    if (emotionEvents.length > 0) {
        const avgIdx = emotionEvents.reduce((sum, e) => sum + e.emotionIndex, 0) / emotionEvents.length;
        const avgEmotion = emotionLabels[Math.round(avgIdx)];
        document.getElementById('overallSentiment').innerText = avgEmotion;
    } else {
        document.getElementById('overallSentiment').innerText = 'Neutral';
    }

    const freq = {};
    emotionEvents.forEach(e => freq[e.emotion] = (freq[e.emotion] || 0) + 1);
    let peakEmotion = 'None', maxCount = 0;
    for (let [em, count] of Object.entries(freq)) {
        if (count > maxCount) {
            maxCount = count;
            peakEmotion = em;
        }
    }
    document.getElementById('emotionPeaks').innerText = peakEmotion + ` (${maxCount} times)`;

    if (typeof socket !== 'undefined') {
        socket.emit('call_control', { action: 'end', callId: customerName || 'unknown' });
    }
    showNotification('Call ended. You can generate the report now.');
    console.log("Call ended. emotionEvents count:", emotionEvents.length);
}

function formatDuration(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2,'0')}:${secs.toString().padStart(2,'0')}`;
}

function generateReport() {
    if (!customerName) {
        showNotification('No call data to report.');
        return;
    }
    console.log("Generating report with emotionEvents:", emotionEvents);
    const report = {
        customer: customerName,
        duration: callSeconds,
        overallSentiment: document.getElementById('overallSentiment').innerText,
        emotionPeaks: document.getElementById('emotionPeaks').innerText,
        emotionEvents: emotionEvents   // this is the key
    };
    fetch('/api/save_report', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(report)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            showNotification('Report saved. Redirecting to Analytics...');
            setTimeout(() => {
                window.location.href = '/analytics';
            }, 1500);
        } else {
            showNotification('Error saving report.');
        }
    })
    .catch(err => {
        console.error('Fetch error:', err);
        showNotification('Error saving report.');
    });
}

function showNotification(message) {
    const panel = document.getElementById('notificationPanel');
    panel.textContent = message;
    panel.style.display = 'block';
    setTimeout(() => { panel.style.display = 'none'; }, 3000);
}