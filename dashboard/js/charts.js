/**
 * Real-Time Chart Rendering Engine (Chart.js)
 * 
 * Manages 3 interactive streaming and historical time-series charts:
 *   1. Thermal Dynamics: Temperature (°C) & Humidity (%) with threshold markers.
 *   2. Kinematic Vibration: Dynamic Vibration Magnitude & Total Vector Accel (m/s²).
 *   3. Machine Condition & Anomaly Timeline: Historical status stepping (0=Normal, 1=Warning, 2=Critical).
 */

const MAX_HISTORY_POINTS = 40;

let thermalChartInstance = null;
let vibrationChartInstance = null;
let conditionChartInstance = null;

// Dark theme defaults for Chart.js
const CHART_GRID_COLOR = 'rgba(75, 85, 99, 0.2)';
const CHART_TEXT_COLOR = '#9ca3af';

/**
 * Initializes all 3 Chart.js instances with dark-mode styling and empty buffers.
 */
function initCharts() {
    // 1. Thermal Dynamics Chart (DHT22)
    const ctxThermal = document.getElementById('thermalChart');
    if (ctxThermal) {
        thermalChartInstance = new Chart(ctxThermal, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Temperature (°C)',
                        data: [],
                        borderColor: '#f59e0b',
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        borderWidth: 2,
                        tension: 0.3,
                        pointRadius: 2,
                        fill: true,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Humidity (%)',
                        data: [],
                        borderColor: '#06b6d4',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        borderDash: [4, 4],
                        tension: 0.3,
                        pointRadius: 2,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { labels: { color: CHART_TEXT_COLOR, font: { size: 11, weight: 'bold' } } },
                    tooltip: { backgroundColor: '#1f2937', titleColor: '#f9fafb', bodyColor: '#d1d5db' }
                },
                scales: {
                    x: {
                        grid: { color: CHART_GRID_COLOR },
                        ticks: { color: CHART_TEXT_COLOR, maxTicksLimit: 8, font: { size: 10 } }
                    },
                    y: {
                        position: 'left',
                        title: { display: true, text: 'Temperature (°C)', color: '#f59e0b', font: { size: 11 } },
                        grid: { color: CHART_GRID_COLOR },
                        ticks: { color: CHART_TEXT_COLOR },
                        suggestedMin: 20,
                        suggestedMax: 80
                    },
                    y1: {
                        position: 'right',
                        title: { display: true, text: 'Humidity (%)', color: '#06b6d4', font: { size: 11 } },
                        grid: { drawOnChartArea: false },
                        ticks: { color: CHART_TEXT_COLOR },
                        suggestedMin: 20,
                        suggestedMax: 80
                    }
                }
            }
        });
    }

    // 2. Vibration Dynamics Chart (MPU6050)
    const ctxVib = document.getElementById('vibrationChart');
    if (ctxVib) {
        vibrationChartInstance = new Chart(ctxVib, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Dynamic Vibration (m/s²)',
                        data: [],
                        borderColor: '#8b5cf6',
                        backgroundColor: 'rgba(139, 92, 246, 0.15)',
                        borderWidth: 2.5,
                        tension: 0.3,
                        pointRadius: 2,
                        fill: true
                    },
                    {
                        label: 'Total Accel (m/s²)',
                        data: [],
                        borderColor: '#38bdf8',
                        backgroundColor: 'transparent',
                        borderWidth: 1.5,
                        borderDash: [3, 3],
                        tension: 0.3,
                        pointRadius: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { labels: { color: CHART_TEXT_COLOR, font: { size: 11, weight: 'bold' } } },
                    tooltip: { backgroundColor: '#1f2937', titleColor: '#f9fafb', bodyColor: '#d1d5db' }
                },
                scales: {
                    x: {
                        grid: { color: CHART_GRID_COLOR },
                        ticks: { color: CHART_TEXT_COLOR, maxTicksLimit: 8, font: { size: 10 } }
                    },
                    y: {
                        title: { display: true, text: 'Acceleration (m/s²)', color: CHART_TEXT_COLOR, font: { size: 11 } },
                        grid: { color: CHART_GRID_COLOR },
                        ticks: { color: CHART_TEXT_COLOR },
                        suggestedMin: 0,
                        suggestedMax: 12
                    }
                }
            }
        });
    }

    // 3. Condition & Anomaly Timeline Chart
    const ctxCond = document.getElementById('conditionChart');
    if (ctxCond) {
        conditionChartInstance = new Chart(ctxCond, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Machine Health State (0=Normal, 1=Warning, 2=Critical)',
                        data: [],
                        stepped: true,
                        borderColor: '#10b981',
                        borderWidth: 2.5,
                        pointRadius: 4,
                        pointBackgroundColor: [],
                        segment: {
                            borderColor: (ctx) => {
                                const val = ctx.p1.parsed.y;
                                if (val >= 2) return '#ef4444';
                                if (val >= 1) return '#f59e0b';
                                return '#10b981';
                            }
                        }
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                plugins: {
                    legend: { labels: { color: CHART_TEXT_COLOR, font: { size: 11, weight: 'bold' } } },
                    tooltip: {
                        backgroundColor: '#1f2937',
                        callbacks: {
                            label: (context) => {
                                const val = context.parsed.y;
                                const state = val >= 2 ? 'CRITICAL' : (val >= 1 ? 'WARNING' : 'NORMAL');
                                return `Condition: ${state}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: CHART_GRID_COLOR },
                        ticks: { color: CHART_TEXT_COLOR, maxTicksLimit: 12, font: { size: 10 } }
                    },
                    y: {
                        grid: { color: CHART_GRID_COLOR },
                        ticks: {
                            color: CHART_TEXT_COLOR,
                            stepSize: 1,
                            callback: (v) => {
                                if (v === 0) return 'NORMAL';
                                if (v === 1) return 'WARNING';
                                if (v === 2) return 'CRITICAL';
                                return '';
                            }
                        },
                        min: 0,
                        max: 2.2
                    }
                }
            }
        });
    }

    console.log('[CHARTS] All 3 Chart.js visualizers initialized successfully.');
}

/**
 * Updates all charts using an array of historical records from Firebase.
 * @param {Array<Object>} historyItems Array of items with sensor_values, timestamp_ms, etc.
 */
function updateChartsFromHistory(historyItems) {
    if (!historyItems || historyItems.length === 0) {
        return;
    }

    const labels = [];
    const temps = [];
    const hums = [];
    const dynVibs = [];
    const totAccels = [];
    const conditions = [];
    const pointColors = [];

    // Slice up to the last MAX_HISTORY_POINTS
    const recent = historyItems.slice(-MAX_HISTORY_POINTS);

    recent.forEach(item => {
        const timeStr = item.timestamp_ms
            ? new Date(item.timestamp_ms > 1e11 ? item.timestamp_ms : item.recorded_at || Date.now()).toLocaleTimeString()
            : '--:--:--';

        labels.push(timeStr);

        const s = item.sensor_values || {};
        temps.push(s.temperature !== undefined ? s.temperature : null);
        hums.push(s.humidity !== undefined ? s.humidity : null);
        dynVibs.push(s.vibration_mag !== undefined ? s.vibration_mag : null);
        totAccels.push(s.total_accel !== undefined ? s.total_accel : null);

        const condStr = (item.predicted_condition || 'NORMAL').toUpperCase();
        let numVal = 0;
        let color = '#10b981';

        if (condStr === 'CRITICAL') {
            numVal = 2;
            color = '#ef4444';
        } else if (condStr === 'WARNING') {
            numVal = 1;
            color = '#f59e0b';
        }

        conditions.push(numVal);
        pointColors.push(color);
    });

    // 1. Update Thermal Chart
    if (thermalChartInstance) {
        thermalChartInstance.data.labels = labels;
        thermalChartInstance.data.datasets[0].data = temps;
        thermalChartInstance.data.datasets[1].data = hums;
        thermalChartInstance.update();
    }

    // 2. Update Vibration Chart
    if (vibrationChartInstance) {
        vibrationChartInstance.data.labels = labels;
        vibrationChartInstance.data.datasets[0].data = dynVibs;
        vibrationChartInstance.data.datasets[1].data = totAccels;
        vibrationChartInstance.update();
    }

    // 3. Update Condition Timeline Chart
    if (conditionChartInstance) {
        conditionChartInstance.data.labels = labels;
        conditionChartInstance.data.datasets[0].data = conditions;
        conditionChartInstance.data.datasets[0].pointBackgroundColor = pointColors;
        conditionChartInstance.update();
    }
}
