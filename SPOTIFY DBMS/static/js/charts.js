/**
 * Spotify Audio Features & Popularity Explorer - Chart.js Initializers
 * Renders glowing, interactive dark-mode visualizations with live filtering
 */

// Global Chart Defaults for Spotify Dark Theme
if (window.Chart) {
    Chart.defaults.color = '#a7a7a7';
    Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";
    Chart.defaults.font.size = 12;
    Chart.defaults.plugins.tooltip.backgroundColor = '#181d1a';
    Chart.defaults.plugins.tooltip.titleColor = '#ffffff';
    Chart.defaults.plugins.tooltip.bodyColor = '#1ed760';
    Chart.defaults.plugins.tooltip.borderColor = '#232a25';
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.boxPadding = 4;
}

let popularityLineChartInstance = null;
let audioFeatureDoughnutInstance = null;

function initDashboardCharts(data) {
    if (!data) return;

    // 1. Overview Popularity Line Chart
    const lineCanvas = document.getElementById("popularityChart");
    if (lineCanvas) {
        const ctx = lineCanvas.getContext("2d");
        
        // Create glowing Spotify green gradient
        const gradient = ctx.createLinearGradient(0, 0, 0, 320);
        gradient.addColorStop(0, "rgba(30, 215, 96, 0.45)");
        gradient.addColorStop(0.7, "rgba(30, 215, 96, 0.08)");
        gradient.addColorStop(1, "rgba(30, 215, 96, 0.0)");

        if (popularityLineChartInstance) {
            popularityLineChartInstance.destroy();
        }

        popularityLineChartInstance = new Chart(ctx, {
            type: "line",
            data: {
                labels: data.line_labels || [],
                datasets: [{
                    label: "Track Popularity Score",
                    data: data.line_values || [],
                    borderColor: "#1ed760",
                    borderWidth: 2.5,
                    backgroundColor: gradient,
                    fill: true,
                    tension: 0.38,
                    pointBackgroundColor: "#1ed760",
                    pointBorderColor: "#090c0a",
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: "#ffffff",
                    pointHoverBorderColor: "#1ed760"
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` Popularity: ${context.parsed.y} / 100`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: {
                            color: "#a7a7a7",
                            maxRotation: 40,
                            minRotation: 15
                        }
                    },
                    y: {
                        min: 50,
                        max: 100,
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: {
                            color: "#a7a7a7",
                            stepSize: 10
                        }
                    }
                }
            }
        });

        // Setup filter pills
        const filterContainer = document.getElementById("overviewFilterPills");
        if (filterContainer && data.filters) {
            const pills = filterContainer.querySelectorAll(".pill-btn");
            pills.forEach(pill => {
                pill.addEventListener("click", () => {
                    pills.forEach(p => p.classList.remove("active"));
                    pill.classList.add("active");
                    const filterKey = pill.getAttribute("data-filter");
                    const series = data.filters[filterKey];
                    if (series && popularityLineChartInstance) {
                        popularityLineChartInstance.data.labels = series.labels || [];
                        popularityLineChartInstance.data.datasets[0].data = series.values || [];
                        popularityLineChartInstance.update();
                        
                        const sub = document.getElementById("lineChartSubtitle");
                        if (sub && series.title) {
                            sub.textContent = series.title;
                        }
                    }
                });
            });
        }
    }

    // 2. Audio Features Doughnut Chart
    const doughnutCanvas = document.getElementById("featureChart");
    if (doughnutCanvas) {
        const ctxD = doughnutCanvas.getContext("2d");
        
        if (audioFeatureDoughnutInstance) {
            audioFeatureDoughnutInstance.destroy();
        }

        audioFeatureDoughnutInstance = new Chart(ctxD, {
            type: "doughnut",
            data: {
                labels: data.feature_labels || ["Danceability", "Energy", "Valence", "Acousticness"],
                datasets: [{
                    data: data.feature_values || [72, 68, 55, 18],
                    backgroundColor: [
                        "#1ed760", // Danceability
                        "#3d91f4", // Energy
                        "#f2994a", // Valence
                        "#9b51e0"  // Acousticness
                    ],
                    borderColor: "#121614",
                    borderWidth: 3,
                    hoverOffset: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "72%",
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` ${context.label}: ${context.parsed}%`;
                            }
                        }
                    }
                }
            }
        });
    }
}

// Initializer for SQL Analysis Dynamic Charts
function initAnalysisBarChart(labels, values, labelTitle) {
    const canvas = document.getElementById("analysisChart");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: labelTitle || "Score",
                data: values,
                backgroundColor: "rgba(30, 215, 96, 0.75)",
                borderColor: "#1ed760",
                borderWidth: 1.5,
                borderRadius: 6,
                hoverBackgroundColor: "#1ed760"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { color: "rgba(255, 255, 255, 0.05)" },
                    ticks: { color: "#a7a7a7" }
                },
                y: {
                    grid: { color: "rgba(255, 255, 255, 0.05)" },
                    ticks: { color: "#a7a7a7" }
                }
            }
        }
    });
}
