import http.server
import socketserver
import threading
import sys
import os
import time
import subprocess
from pathlib import Path
from config import logger

PORT = 8089

# Beautiful HTML that acts as Melbet SPA (Login, OTP, Dashboard, Deposits, Withdrawals, Bets)
MOCK_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Melbet India - Mock Betting Platform</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #1a1e24;
            color: #f5f6fa;
            margin: 0;
            padding: 0;
        }
        header {
            background-color: #2c3e50;
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 3px solid #f1c40f;
        }
        .logo {
            font-size: 24px;
            font-weight: bold;
            color: #f1c40f;
        }
        .header-right {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .btn {
            background-color: #f1c40f;
            color: #2c3e50;
            border: none;
            padding: 8px 16px;
            font-weight: bold;
            cursor: pointer;
            border-radius: 4px;
        }
        .btn:hover {
            background-color: #f39c12;
        }
        .user-profile-menu {
            background-color: #34495e;
            padding: 8px 15px;
            border-radius: 4px;
            cursor: pointer;
            border: 1px solid #f1c40f;
        }
        .container {
            max-width: 1200px;
            margin: 30px auto;
            padding: 20px;
            background-color: #2d3436;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        }
        .hidden {
            display: none !important;
        }
        /* Modal styling */
        .modal {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background-color: #2c3e50;
            padding: 30px;
            border-radius: 8px;
            border: 2px solid #f1c40f;
            z-index: 1000;
            width: 350px;
        }
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.7);
            z-index: 999;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-size: 14px;
        }
        .form-group input {
            width: 100%;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid #7f8c8d;
            background-color: #1a1e24;
            color: white;
            box-sizing: border-box;
        }
        /* Dashboard Styling */
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid #7f8c8d;
            padding-bottom: 10px;
        }
        .tab-btn {
            background: none;
            border: none;
            color: #b2bec3;
            font-size: 16px;
            padding: 10px 20px;
            cursor: pointer;
            font-weight: bold;
        }
        .tab-btn.active {
            color: #f1c40f;
            border-bottom: 3px solid #f1c40f;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th, td {
            padding: 12px;
            text-align: center;
            border-bottom: 1px solid #4a5568;
        }
        th {
            background-color: #1a1e24;
            color: #f1c40f;
        }
        .status-success { color: #2ecc71; font-weight: bold; }
        .status-failed { color: #e74c3c; font-weight: bold; }
        .status-pending { color: #f1c40f; font-weight: bold; }
        
        .profile-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }
        .profile-card {
            background-color: #1a1e24;
            padding: 20px;
            border-radius: 6px;
            border-left: 5px solid #f1c40f;
        }
    </style>
</head>
<body>

    <header>
        <div class="logo">MELBET IND</div>
        <div class="header-right">
            <button class="btn login-btn" id="loginBtn" onclick="openModal()">Log In</button>
            <div class="user-profile-menu hidden" id="profileMenu">
                <span class="user-name" data-testid="user-name">Expert286</span> 
                (<span class="wallet-balance" data-testid="balance">15,432.50 ₹</span>)
            </div>
        </div>
    </header>

    <div class="container" id="mainContainer">
        <!-- Welcoming / Landing View -->
        <div id="welcomeView">
            <h2>Welcome to Melbet India</h2>
            <p>Please log in to view your profile, transactions, and betting analytics.</p>
        </div>

        <!-- Dashboard View (Shown after login) -->
        <div id="dashboardView" class="hidden">
            <div class="profile-grid">
                <div class="profile-card">
                    <h3>Account Profile</h3>
                    <p><strong>User ID:</strong> <span class="user-id" data-testid="user-id">ID: 4829103</span></p>
                    <p><strong>Username:</strong> <span class="user-name">Expert286</span></p>
                    <p><strong>Account Status:</strong> <span class="account-status" data-testid="status">Verified</span></p>
                </div>
                <div class="profile-card">
                    <h3>Wallet Balance</h3>
                    <p><strong>Balance:</strong> <span class="wallet-balance">15,432.50 ₹</span></p>
                    <p><strong>Currency:</strong> <span class="wallet-currency" data-testid="currency">INR</span></p>
                </div>
            </div>

            <div class="tabs">
                <button class="tab-btn active" onclick="switchTab('profile')">Profile Overview</button>
                <button class="tab-btn deposit-history-tab" onclick="switchTab('deposits')">Deposit History</button>
                <button class="tab-btn withdrawal-history-tab" onclick="switchTab('withdrawals')">Withdrawal History</button>
                <button class="tab-btn bet-history-tab" onclick="switchTab('bets')">Bet History</button>
            </div>

            <!-- Tab Contents -->
            <div id="tab-profile" class="tab-content">
                <h4>Welcome back, Expert286! Use the tabs above to explore your transaction histories and betting slips.</h4>
            </div>

            <div id="tab-deposits" class="tab-content hidden">
                <h3>Deposit History</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Ref Number</th>
                            <th>Amount</th>
                            <th>Date & Time</th>
                            <th>Method</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr class="transaction-row">
                            <td class="ref-id">DEP902847</td>
                            <td class="amount">10,000.00 ₹</td>
                            <td class="date">2026-06-20 14:32:00</td>
                            <td class="method">UPI / NetBanking</td>
                            <td class="status status-success">Success</td>
                        </tr>
                        <tr class="transaction-row">
                            <td class="ref-id">DEP827394</td>
                            <td class="amount">5,000.00 ₹</td>
                            <td class="date">2026-06-18 10:15:00</td>
                            <td class="method">PhonePe</td>
                            <td class="status status-success">Success</td>
                        </tr>
                        <tr class="transaction-row">
                            <td class="ref-id">DEP738492</td>
                            <td class="amount">2,000.00 ₹</td>
                            <td class="date">2026-06-15 18:45:00</td>
                            <td class="method">UPI</td>
                            <td class="status status-failed">Failed</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div id="tab-withdrawals" class="tab-content hidden">
                <h3>Withdrawal History</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Ref Number</th>
                            <th>Amount</th>
                            <th>Date & Time</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr class="transaction-row">
                            <td class="ref-id">WTH482910</td>
                            <td class="amount">3,000.00 ₹</td>
                            <td class="date">2026-06-22 09:30:00</td>
                            <td class="status status-success">Success</td>
                        </tr>
                        <tr class="transaction-row">
                            <td class="ref-id">WTH392817</td>
                            <td class="amount">5,000.00 ₹</td>
                            <td class="date">2026-06-21 11:00:00</td>
                            <td class="status status-pending">Pending</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div id="tab-bets" class="tab-content hidden">
                <h3>Bet History</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Bet ID</th>
                            <th>Event Name</th>
                            <th>Stake</th>
                            <th>Odds</th>
                            <th>Status</th>
                            <th>Profit/Loss</th>
                            <th>Settlement Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr class="bet-row">
                            <td class="bet-id">BET772093</td>
                            <td class="event-name">India vs Australia T20</td>
                            <td class="stake-amount">1,000.00 ₹</td>
                            <td class="odds-value">1.85</td>
                            <td class="bet-status status-success">Win</td>
                            <td class="pnl-amount">850.00 ₹</td>
                            <td class="settlement-time">2026-06-23 15:45:00</td>
                        </tr>
                        <tr class="bet-row">
                            <td class="bet-id">BET771822</td>
                            <td class="event-name">Mumbai Indians vs RCB IPL</td>
                            <td class="stake-amount">2,000.00 ₹</td>
                            <td class="odds-value">2.10</td>
                            <td class="bet-status status-failed">Loss</td>
                            <td class="pnl-amount">-2,000.00 ₹</td>
                            <td class="settlement-time">2026-06-22 22:30:00</td>
                        </tr>
                        <tr class="bet-row">
                            <td class="bet-id">BET770932</td>
                            <td class="event-name">Chelsea vs Arsenal EPL</td>
                            <td class="stake-amount">500.00 ₹</td>
                            <td class="odds-value">3.20</td>
                            <td class="bet-status status-success">Win</td>
                            <td class="pnl-amount">1,100.00 ₹</td>
                            <td class="settlement-time">2026-06-21 21:00:00</td>
                        </tr>
                    </tbody>
                </table>
            </div>

        </div>
    </div>

    <!-- Login Modal overlay -->
    <div class="modal-overlay hidden" id="modalOverlay"></div>
    
    <!-- Credentials Modal -->
    <div class="modal hidden" id="loginModal">
        <h3 style="margin-top:0; color:#f1c40f;">Account Log In</h3>
        <div id="credSection">
            <div class="form-group">
                <label>Email / Username</label>
                <input type="email" id="emailInput" placeholder="Expert286@gmail.com" name="email">
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" id="passwordInput" placeholder="••••••••" name="password">
            </div>
            <button class="btn" style="width:100%; margin-top:10px;" onclick="submitCreds()">Next</button>
        </div>
        
        <!-- OTP section inside modal -->
        <div id="otpSection" class="hidden">
            <p>A verification code has been sent to your email.</p>
            <div class="form-group">
                <label>Enter 6-Digit OTP</label>
                <input type="text" id="otpInput" placeholder="123456" name="otp">
            </div>
            <button class="btn otp-submit-btn" style="width:100%; margin-top:10px;" onclick="submitOtp()">Submit Code</button>
        </div>
        
        <p id="errorMsg" style="color:#e74c3c; font-size:13px; text-align:center; margin-top:15px;" class="hidden"></p>
    </div>

    <script>
        // Check session cookie/storage state simulation
        if (localStorage.getItem("isLoggedIn") === "true") {
            showDashboard();
        }

        function openModal() {
            document.getElementById("modalOverlay").classList.remove("hidden");
            document.getElementById("loginModal").classList.remove("hidden");
            document.getElementById("credSection").classList.remove("hidden");
            document.getElementById("otpSection").classList.add("hidden");
            document.getElementById("errorMsg").classList.add("hidden");
        }

        function closeModal() {
            document.getElementById("modalOverlay").classList.add("hidden");
            document.getElementById("loginModal").classList.add("hidden");
        }

        function submitCreds() {
            const email = document.getElementById("emailInput").value.trim();
            const pass = document.getElementById("passwordInput").value.trim();
            const error = document.getElementById("errorMsg");

            // Check hardcoded credentials matching user input
            if (email === "Expert286@gmail.com" && pass === "Dhfm@1234") {
                error.classList.add("hidden");
                document.getElementById("credSection").classList.add("hidden");
                document.getElementById("otpSection").classList.remove("hidden");
            } else {
                error.innerText = "Invalid credentials. Please check username and password.";
                error.classList.remove("hidden");
            }
        }

        function submitOtp() {
            const otp = document.getElementById("otpInput").value.trim();
            const error = document.getElementById("errorMsg");

            if (otp.length >= 4) {
                // Successful verification
                localStorage.setItem("isLoggedIn", "true");
                closeModal();
                showDashboard();
            } else {
                error.innerText = "Invalid OTP code. Try again.";
                error.classList.remove("hidden");
            }
        }

        function showDashboard() {
            document.getElementById("loginBtn").classList.add("hidden");
            document.getElementById("profileMenu").classList.remove("hidden");
            document.getElementById("welcomeView").classList.add("hidden");
            document.getElementById("dashboardView").classList.remove("hidden");
        }

        function switchTab(tabId) {
            // Hide all tab contents
            const contents = document.querySelectorAll(".tab-content");
            contents.forEach(c => c.classList.add("hidden"));
            
            // Remove active from all tab buttons
            const buttons = document.querySelectorAll(".tab-btn");
            buttons.forEach(b => b.classList.remove("active"));
            
            // Show selected tab content
            document.getElementById("tab-" + tabId).classList.remove("hidden");
            
            // Highlight button
            event.currentTarget.classList.add("active");
        }
    </script>
</body>
</html>
"""

class MockHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # We serve the same SPA for all frontend routing paths
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(MOCK_HTML.encode('utf-8'))

def start_server():
    """Runs the HTTP server synchronously."""
    handler = MockHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        logger.info(f"Mock HTTP server starting on port {PORT}...")
        httpd.serve_forever()

def start_mock_server() -> tuple[subprocess.Popen, str]:
    """Starts the mock server in a separate background python process."""
    # Launch this file as a subprocess to keep the main async script non-blocking
    process = subprocess.Popen(
        [sys.executable, __file__],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    # Allow server a brief moment to boot up
    time.sleep(1.5)
    return process, f"http://localhost:{PORT}/en"

if __name__ == "__main__":
    start_server()
