"""
Test Dashboard - Real-time Test Results with Charts/Graphs
Generates HTML dashboard for visualizing test results
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class TestDashboard:
    def __init__(self, output_dir: str = "test_dashboard"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.static_dir = self.output_dir / "static"
        self.static_dir.mkdir(exist_ok=True)
        self.templates_dir = self.output_dir / "templates"
        self.templates_dir.mkdir(exist_ok=True)

    def generate_chart_js(self) -> str:
        """Generate Chart.js based dashboard HTML"""
        return (
            """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wicked Zerg Test Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; color: #fff; }
        .header { background: linear-gradient(90deg, #0f3460, #e94560); padding: 20px; text-align: center; }
        .header h1 { font-size: 2.5em; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
        .stat-card { background: rgba(255,255,255,0.1); border-radius: 15px; padding: 20px; text-align: center; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2); }
        .stat-card h3 { font-size: 0.9em; opacity: 0.8; }
        .stat-card .value { font-size: 2.5em; font-weight: bold; margin: 10px 0; }
        .stat-card.pass .value { color: #4ade80; }
        .stat-card.fail .value { color: #f87171; }
        .charts-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; margin: 20px 0; }
        .chart-container { background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; border: 1px solid rgba(255,255,255,0.1); }
        .chart-container h2 { margin-bottom: 15px; color: #e94560; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }
        th { background: rgba(233,69,96,0.3); color: #fff; }
        tr:hover { background: rgba(255,255,255,0.05); }
        .badge { padding: 4px 12px; border-radius: 20px; font-size: 0.8em; }
        .badge.pass { background: #4ade80; color: #000; }
        .badge.fail { background: #f87171; color: #000; }
        .scenario-selector { background: rgba(255,255,255,0.1); padding: 20px; border-radius: 15px; margin: 20px 0; }
        select, button { padding: 10px 20px; border-radius: 8px; border: none; margin: 5px; cursor: pointer; }
        select { background: #1a1a2e; color: #fff; min-width: 200px; }
        button { background: #e94560; color: #fff; font-weight: bold; }
        button:hover { background: #ff6b6b; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🪰 Wicked Zerg Test Dashboard</h1>
        <p>Unit Combination Analysis & Performance Metrics</p>
    </div>
    <div class="container">
        <div class="scenario-selector">
            <h2>Test Scenario Selection</h2>
            <select id="scenarioSelect">
                <option value="">Select Scenario...</option>
                <option value="rush_defense">Rush Defense</option>
                <option value="macro_battle">Macro Battle</option>
                <option value="harassment">Harassment</option>
                <option value="economy_tech">Economy Tech Build</option>
                <option value="all">All Scenarios</option>
            </select>
            <button onclick="runSelectedTest()">Run Test</button>
            <button onclick="exportResults()">Export Results</button>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card pass">
                <h3>Total Tests</h3>
                <div class="value" id="totalTests">0</div>
            </div>
            <div class="stat-card pass">
                <h3>Passed</h3>
                <div class="value" id="passedTests">0</div>
            </div>
            <div class="stat-card fail">
                <h3>Failed</h3>
                <div class="value" id="failedTests">0</div>
            </div>
            <div class="stat-card">
                <h3>Win Rate</h3>
                <div class="value" id="winRate">0%</div>
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-container">
                <h2>Unit Combination Win Rates</h2>
                <canvas id="unitComboChart"></canvas>
            </div>
            <div class="chart-container">
                <h2>Scenario Performance</h2>
                <canvas id="scenarioChart"></canvas>
            </div>
            <div class="chart-container">
                <h2>Test History Timeline</h2>
                <canvas id="timelineChart"></canvas>
            </div>
            <div class="chart-container">
                <h2>Unit Synergy Heatmap</h2>
                <canvas id="heatmapChart"></canvas>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>Detailed Test Results</h2>
            <table id="resultsTable">
                <thead>
                    <tr>
                        <th>Scenario</th>
                        <th>Unit Combo</th>
                        <th>Result</th>
                        <th>Win Rate</th>
                        <th>Avg Duration</th>
                        <th>Last Run</th>
                    </tr>
                </thead>
                <tbody id="resultsBody"></tbody>
            </table>
        </div>
    </div>
    
    <script>
        const testData = """
            + json.dumps(self._get_sample_data())
            + """;
        
        function initCharts() {
            new Chart(document.getElementById('unitComboChart'), {
                type: 'bar',
                data: {
                    labels: Object.keys(testData.unitCombos),
                    datasets: [{
                        label: 'Win Rate %',
                        data: Object.values(testData.unitCombos).map(v => v.winRate),
                        backgroundColor: 'rgba(233,69,96,0.7)',
                        borderColor: '#e94560',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { labels: { color: '#fff' } } },
                    scales: { y: { beginAtZero: true, max: 100, ticks: { color: '#fff' } }, x: { ticks: { color: '#fff' } } }
                }
            });
            
            new Chart(document.getElementById('scenarioChart'), {
                type: 'doughnut',
                data: {
                    labels: Object.keys(testData.scenarios),
                    datasets: [{
                        data: Object.values(testData.scenarios).map(s => s.tests),
                        backgroundColor: ['#e94560', '#4ade80', '#60a5fa', '#fbbf24', '#a78bfa']
                    }]
                },
                options: { responsive: true, plugins: { legend: { labels: { color: '#fff' } } } }
            });
            
            new Chart(document.getElementById('timelineChart'), {
                type: 'line',
                data: {
                    labels: testData.history.map(h => h.date),
                    datasets: [{
                        label: 'Win Rate %',
                        data: testData.history.map(h => h.winRate),
                        borderColor: '#4ade80',
                        tension: 0.4,
                        fill: true,
                        backgroundColor: 'rgba(74,222,128,0.2)'
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { labels: { color: '#fff' } } },
                    scales: { y: { beginAtZero: true, max: 100, ticks: { color: '#fff' } }, x: { ticks: { color: '#fff' } } }
                }
            });
            
            const units = ['Zergling', 'Baneling', 'Roach', 'Hydralisk', 'Mutalisk', 'Ultralisk'];
            const synergyData = units.map((_, i) => units.map((_, j) => Math.random() * 100));
            new Chart(document.getElementById('heatmapChart'), {
                type: 'bar',
                data: {
                    labels: units,
                    datasets: units.map((u, i) => ({
                        label: u,
                        data: synergyData[i],
                        backgroundColor: `rgba(${100 + i*30}, ${150 - i*20}, ${200 - i*10}, 0.7)`
                    }))
                },
                options: {
                    responsive: true,
                    plugins: { legend: { labels: { color: '#fff' } } },
                    scales: { y: { beginAtZero: true, max: 100, ticks: { color: '#fff' } }, x: { ticks: { color: '#fff' } } }
                }
            });
        }
        
        function updateStats() {
            document.getElementById('totalTests').textContent = testData.totalTests;
            document.getElementById('passedTests').textContent = testData.passed;
            document.getElementById('failedTests').textContent = testData.failed;
            document.getElementById('winRate').textContent = testData.winRate + '%';
            
            const tbody = document.getElementById('resultsBody');
            tbody.innerHTML = testData.details.map(d => `
                <tr>
                    <td>${d.scenario}</td>
                    <td>${d.combo}</td>
                    <td><span class="badge ${d.passed ? 'pass' : 'fail'}">${d.passed ? 'PASS' : 'FAIL'}</span></td>
                    <td>${d.winRate}%</td>
                    <td>${d.avgDuration}ms</td>
                    <td>${d.lastRun}</td>
                </tr>
            `).join('');
        }
        
        function runSelectedTest() {
            alert('Running test simulation...');
        }
        
        function exportResults() {
            alert('Exporting results to JSON...');
        }
        
        initCharts();
        updateStats();
    </script>
</body>
</html>"""
        )

    def _get_sample_data(self) -> Dict[str, Any]:
        return {
            "totalTests": 156,
            "passed": 128,
            "failed": 28,
            "winRate": 82,
            "unitCombos": {
                "Zergling+Baneling": {"winRate": 89, "tests": 24},
                "Roach+Hydralisk": {"winRate": 78, "tests": 20},
                "Mutalisk+Corruptor": {"winRate": 85, "tests": 18},
                "Ultralisk+BroodLord": {"winRate": 92, "tests": 12},
                "Queen+Drone": {"winRate": 75, "tests": 16},
                "Zergling+Roach": {"winRate": 81, "tests": 22},
            },
            "scenarios": {
                "rush_defense": {"tests": 42, "winRate": 88},
                "macro_battle": {"tests": 38, "winRate": 79},
                "harassment": {"tests": 35, "winRate": 85},
                "economy_tech": {"tests": 41, "winRate": 76},
            },
            "history": [
                {"date": "2026-04-01", "winRate": 72},
                {"date": "2026-04-02", "winRate": 75},
                {"date": "2026-04-03", "winRate": 78},
                {"date": "2026-04-04", "winRate": 80},
                {"date": "2026-04-05", "winRate": 82},
            ],
            "details": [
                {
                    "scenario": "rush_defense",
                    "combo": "Zergling+Baneling",
                    "passed": True,
                    "winRate": 92,
                    "avgDuration": 1250,
                    "lastRun": "2026-04-05 14:30",
                },
                {
                    "scenario": "macro_battle",
                    "combo": "Roach+Hydralisk",
                    "passed": True,
                    "winRate": 78,
                    "avgDuration": 3420,
                    "lastRun": "2026-04-05 14:25",
                },
                {
                    "scenario": "harassment",
                    "combo": "Mutalisk",
                    "passed": True,
                    "winRate": 85,
                    "avgDuration": 2100,
                    "lastRun": "2026-04-05 14:20",
                },
                {
                    "scenario": "economy_tech",
                    "combo": "Queen+Drone",
                    "passed": False,
                    "winRate": 65,
                    "avgDuration": 4500,
                    "lastRun": "2026-04-05 14:15",
                },
            ],
        }

    def generate(self) -> Path:
        html_path = self.output_dir / "dashboard.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(self.generate_chart_js())
        print(f"[TestDashboard] Generated: {html_path}")
        return html_path


if __name__ == "__main__":
    dashboard = TestDashboard()
    dashboard.generate()
