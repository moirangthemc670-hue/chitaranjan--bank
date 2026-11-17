from flask import Flask, request, redirect, url_for, render_template_string, jsonify
import qrcode
import io
import base64
import uuid
import time

app = Flask(__name__)

# ============================================================
# BANK CLASSES
# ============================================================

class Customer:
    def __init__(self, name):
        self.name = name


class Account:
    def __init__(self, customer, account_no, initial_balance):
        self.customer = customer
        self.account_no = account_no
        self.balance = initial_balance
        self.transactions = []

        self.transactions.append({
            "type": "Initial Deposit",
            "amount": initial_balance,
            "time": time.strftime("%d-%m-%Y %I:%M:%S %p")
        })

    def deposit(self, amount, transaction_type="Deposit"):
        if amount <= 0:
            return False

        self.balance += amount

        self.transactions.insert(0, {
            "type": transaction_type,
            "amount": amount,
            "time": time.strftime("%d-%m-%Y %I:%M:%S %p")
        })

        return True

    def withdraw(self, amount):
        if amount <= 0:
            return False

        if amount > self.balance:
            return False

        self.balance -= amount

        self.transactions.insert(0, {
            "type": "Withdrawal",
            "amount": amount,
            "time": time.strftime("%d-%m-%Y %I:%M:%S %p")
        })

        return True


# ============================================================
# GLOBAL VARIABLES
# ============================================================

account = None

message = ""
message_type = ""

# Temporary QR deposit tokens
pending_deposits = {}


# ============================================================
# COMMON HTML
# ============================================================

BASE_STYLE = """
<style>
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    font-family: Arial, Helvetica, sans-serif;
}

body {
    min-height: 100vh;
    background:
        radial-gradient(circle at 10% 20%, rgba(37, 99, 235, 0.20), transparent 30%),
        radial-gradient(circle at 90% 80%, rgba(14, 165, 233, 0.18), transparent 30%),
        linear-gradient(135deg, #020617, #0f172a, #172554);
    color: white;
}

.container {
    width: 94%;
    max-width: 1250px;
    margin: auto;
}

button {
    border: none;
    cursor: pointer;
}

.header {
    padding: 20px 0;
    border-bottom: 1px solid rgba(255,255,255,0.10);
}

.header-inner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
}

.bank-logo {
    display: flex;
    align-items: center;
    gap: 14px;
}

.logo {
    width: 52px;
    height: 52px;
    border-radius: 15px;
    background: linear-gradient(135deg, #2563eb, #06b6d4);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 25px;
    font-weight: bold;
    box-shadow: 0 10px 30px rgba(37,99,235,0.35);
}

.bank-name {
    font-size: 21px;
    font-weight: bold;
}

.bank-subtitle {
    color: #94a3b8;
    font-size: 12px;
    margin-top: 4px;
}

.status {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #86efac;
    font-size: 13px;
}

.status-dot {
    width: 9px;
    height: 9px;
    background: #22c55e;
    border-radius: 50%;
    box-shadow: 0 0 12px #22c55e;
}

.logout {
    background: rgba(239,68,68,0.12);
    color: #fca5a5;
    padding: 10px 18px;
    border-radius: 10px;
    border: 1px solid rgba(239,68,68,0.25);
    font-weight: bold;
}

.logout:hover {
    background: rgba(239,68,68,0.22);
}

.dashboard {
    padding: 35px 0 60px;
}

.welcome {
    margin-bottom: 25px;
}

.welcome h1 {
    font-size: 30px;
    margin-bottom: 7px;
}

.welcome p {
    color: #94a3b8;
}

.grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
}

.card {
    background: rgba(15,23,42,0.75);
    border: 1px solid rgba(148,163,184,0.13);
    border-radius: 20px;
    padding: 25px;
    backdrop-filter: blur(15px);
    box-shadow: 0 20px 50px rgba(0,0,0,0.20);
    animation: fadeIn 0.5s ease;
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(12px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.account-card {
    grid-column: span 2;
}

.balance-card {
    background: linear-gradient(135deg, rgba(37,99,235,0.35), rgba(14,165,233,0.18));
}

.card-title {
    color: #94a3b8;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 15px;
}

.account-number {
    font-size: 24px;
    font-weight: bold;
    letter-spacing: 2px;
}

.account-holder {
    color: #cbd5e1;
    margin-top: 8px;
}

.balance {
    font-size: 38px;
    font-weight: bold;
    margin-top: 8px;
}

.currency {
    color: #93c5fd;
    font-size: 14px;
}

.action-card {
    grid-column: span 1;
}

.action-title {
    font-size: 20px;
    font-weight: bold;
    margin-bottom: 8px;
}

.action-description {
    color: #94a3b8;
    font-size: 13px;
    margin-bottom: 18px;
}

input {
    width: 100%;
    padding: 14px;
    border-radius: 11px;
    border: 1px solid rgba(148,163,184,0.18);
    background: rgba(2,6,23,0.65);
    color: white;
    outline: none;
    font-size: 15px;
    margin-bottom: 12px;
}

input:focus {
    border-color: #3b82f6;
}

.btn {
    width: 100%;
    padding: 14px;
    border-radius: 11px;
    color: white;
    font-size: 15px;
    font-weight: bold;
    background: linear-gradient(135deg, #2563eb, #0891b2);
    transition: 0.2s;
}

.btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 25px rgba(37,99,235,0.25);
}

.withdraw-btn {
    background: linear-gradient(135deg, #dc2626, #ea580c);
}

.qr-btn {
    background: linear-gradient(135deg, #7c3aed, #2563eb);
}

.security {
    margin-top: 20px;
    padding: 17px;
    border-radius: 14px;
    background: rgba(34,197,94,0.08);
    border: 1px solid rgba(34,197,94,0.15);
    color: #bbf7d0;
    font-size: 13px;
}

.history {
    margin-top: 20px;
}

.transaction {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 15px 0;
    border-bottom: 1px solid rgba(148,163,184,0.10);
}

.transaction:last-child {
    border-bottom: none;
}

.transaction-type {
    font-weight: bold;
}

.transaction-time {
    color: #64748b;
    font-size: 12px;
    margin-top: 4px;
}

.deposit {
    color: #4ade80;
}

.withdrawal {
    color: #f87171;
}

.qr-section {
    margin-top: 20px;
    text-align: center;
}

.qr-box {
    display: inline-block;
    background: white;
    padding: 14px;
    border-radius: 15px;
    margin: 15px 0;
}

.qr-box img {
    width: 230px;
    height: 230px;
    display: block;
}

.qr-info {
    color: #94a3b8;
    font-size: 13px;
    line-height: 1.6;
}

.network-warning {
    margin-top: 15px;
    background: rgba(245,158,11,0.10);
    border: 1px solid rgba(245,158,11,0.20);
    color: #fde68a;
    padding: 12px;
    border-radius: 10px;
    font-size: 12px;
}

.modal {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.75);
    display: none;
    justify-content: center;
    align-items: center;
    padding: 20px;
    z-index: 1000;
}

.modal-box {
    width: 100%;
    max-width: 440px;
    background: #0f172a;
    border: 1px solid rgba(148,163,184,0.18);
    border-radius: 22px;
    padding: 25px;
    text-align: center;
    position: relative;
}

.close {
    position: absolute;
    right: 18px;
    top: 15px;
    font-size: 25px;
    color: #94a3b8;
    background: none;
}

.close:hover {
    color: white;
}

.modal-title {
    font-size: 23px;
    font-weight: bold;
    margin-bottom: 7px;
}

.modal-subtitle {
    color: #94a3b8;
    font-size: 13px;
    line-height: 1.5;
}

.loading {
    display: none;
    color: #60a5fa;
    margin-top: 10px;
    font-size: 13px;
}

@media(max-width: 850px) {
    .grid {
        grid-template-columns: 1fr;
    }

    .account-card {
        grid-column: span 1;
    }

    .header-inner {
        flex-wrap: wrap;
    }

    .balance {
        font-size: 32px;
    }
}
</style>
"""


# ============================================================
# DASHBOARD HTML
# ============================================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Chitaranjan Bank of Manipur</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    {{ style|safe }}
</head>

<body>

<header class="header">
    <div class="container header-inner">

        <div class="bank-logo">
            <div class="logo">CB</div>

            <div>
                <div class="bank-name">
                    Chitaranjan Bank of Manipur
                </div>

                <div class="bank-subtitle">
                    Digital Banking System
                </div>
            </div>
        </div>

        <div class="status">
            <div class="status-dot"></div>
            SYSTEM ONLINE
        </div>

        <form action="/logout" method="POST">
            <button class="logout">Logout</button>
        </form>

    </div>
</header>


<main class="dashboard">

<div class="container">

    <div class="welcome">
        <h1>Welcome, {{ account.customer.name }}</h1>
        <p>Manage your account securely from your banking dashboard.</p>
    </div>


    {% if message %}
    <div class="security"
         style="
         margin-bottom:20px;
         {% if message_type == 'error' %}
         background:rgba(239,68,68,0.10);
         border-color:rgba(239,68,68,0.20);
         color:#fecaca;
         {% endif %}
         ">
        {{ message }}
    </div>
    {% endif %}


    <div class="grid">

        <!-- ACCOUNT INFORMATION -->

        <div class="card account-card">

            <div class="card-title">
                Account Information
            </div>

            <div class="account-number">
                {{ account.account_no }}
            </div>

            <div class="account-holder">
                {{ account.customer.name }}
            </div>

        </div>


        <!-- BALANCE -->

        <div class="card balance-card">

            <div class="card-title">
                Available Balance
            </div>

            <div class="balance">
                ₹<span id="balance">{{ "%.2f"|format(account.balance) }}</span>
            </div>

            <div class="currency">
                Indian Rupees
            </div>

        </div>


        <!-- DEPOSIT -->

        <div class="card action-card">

            <div class="action-title">
                Deposit Money
            </div>

            <div class="action-description">
                Add money directly to your account.
            </div>

            <form action="/deposit" method="POST">

                <input
                    type="number"
                    name="amount"
                    step="0.01"
                    min="0.01"
                    placeholder="Enter amount"
                    required
                >

                <button class="btn">
                    Deposit Money
                </button>

            </form>

        </div>


        <!-- WITHDRAW -->

        <div class="card action-card">

            <div class="action-title">
                Withdraw Money
            </div>

            <div class="action-description">
                Withdraw money from your available balance.
            </div>

            <form action="/withdraw" method="POST">

                <input
                    type="number"
                    name="amount"
                    step="0.01"
                    min="0.01"
                    placeholder="Enter amount"
                    required
                >

                <button class="btn withdraw-btn">
                    Withdraw Money
                </button>

            </form>

        </div>


        <!-- QR PHONE DEPOSIT -->

        <div class="card action-card">

            <div class="action-title">
                📱 Scan to Deposit
            </div>

            <div class="action-description">
                Generate a QR code and scan it using your phone.
                Enter the deposit amount directly on your phone.
            </div>

            <button
                class="btn qr-btn"
                onclick="generateQR()">
                Generate Deposit QR
            </button>

            <div id="qrLoading" class="loading">
                Generating secure QR...
            </div>

        </div>


    </div>


    <!-- SECURITY -->

    <div class="security">

        🔒 <strong>Secure Banking</strong><br>

        Your transactions are processed securely by
        Chitaranjan Bank of Manipur.

    </div>


    <!-- TRANSACTION HISTORY -->

    <div class="card history">

        <div class="card-title">
            Transaction History
        </div>

        <div id="transactions">

            {% for transaction in account.transactions %}

            <div class="transaction">

                <div>
                    <div class="transaction-type
                        {% if transaction.type == 'Withdrawal' %}
                        withdrawal
                        {% else %}
                        deposit
                        {% endif %}">
                        {{ transaction.type }}
                    </div>

                    <div class="transaction-time">
                        {{ transaction.time }}
                    </div>
                </div>

                <div class="
                    {% if transaction.type == 'Withdrawal' %}
                    withdrawal
                    {% else %}
                    deposit
                    {% endif %}
                    ">

                    {% if transaction.type == 'Withdrawal' %}
                    -
                    {% else %}
                    +
                    {% endif %}

                    ₹{{ "%.2f"|format(transaction.amount) }}

                </div>

            </div>

            {% endfor %}

        </div>

    </div>

</div>

</main>


<!-- QR MODAL -->

<div class="modal" id="qrModal">

    <div class="modal-box">

        <button class="close"
                onclick="closeQR()">
            ×
        </button>

        <div class="modal-title">
            📱 Scan to Deposit
        </div>

        <div class="modal-subtitle">
            Open your phone camera and scan this QR code.
            The phone will open a secure deposit page.
        </div>

        <div class="qr-section">

            <div class="qr-box">
                <img id="qrImage" src="">
            </div>

            <div class="qr-info">
                1. Scan the QR using your phone<br>
                2. Enter the deposit amount on your phone<br>
                3. Confirm the deposit<br>
                4. Your laptop balance updates automatically
            </div>

            <div class="network-warning">
                ⚠ Both laptop and phone must be connected
                to the same Wi-Fi network.
            </div>

        </div>

    </div>

</div>


<script>

async function generateQR() {

    document.getElementById("qrLoading").style.display = "block";

    try {

        const response = await fetch("/generate-deposit-qr");

        const data = await response.json();

        if (data.success) {

            document.getElementById("qrImage").src =
                "data:image/png;base64," + data.qr;

            document.getElementById("qrModal").style.display =
                "flex";

        } else {

            alert(data.message);

        }

    } catch (error) {

        alert("Unable to generate QR code.");

    }

    document.getElementById("qrLoading").style.display = "none";
}


function closeQR() {

    document.getElementById("qrModal").style.display =
        "none";

}


/* ---------------------------------------------------------
   AUTOMATIC BALANCE UPDATE
--------------------------------------------------------- */

async function updateAccount() {

    try {

        const response =
            await fetch("/api/account");

        const data =
            await response.json();

        if (!data.logged_in) {
            return;
        }

        document.getElementById("balance").innerText =
            Number(data.balance).toFixed(2);


        let transactionHTML = "";

        data.transactions.forEach(function(transaction) {

            const isWithdrawal =
                transaction.type === "Withdrawal";

            transactionHTML += `
                <div class="transaction">

                    <div>

                        <div class="transaction-type
                            ${isWithdrawal ? "withdrawal" : "deposit"}">

                            ${transaction.type}

                        </div>

                        <div class="transaction-time">

                            ${transaction.time}

                        </div>

                    </div>

                    <div class="
                        ${isWithdrawal ? "withdrawal" : "deposit"}
                    ">

                        ${isWithdrawal ? "-" : "+"}
                        ₹${Number(transaction.amount).toFixed(2)}

                    </div>

                </div>
            `;

        });

        document.getElementById("transactions").innerHTML =
            transactionHTML;

    } catch (error) {

        console.log("Account update error:", error);

    }

}


/*
   Check the account every 2 seconds.
   When the phone deposits money, the laptop
   automatically receives the new balance.
*/

setInterval(updateAccount, 2000);


</script>

</body>
</html>
"""


# ============================================================
# PHONE DEPOSIT PAGE
# ============================================================

PHONE_DEPOSIT_HTML = """
<!DOCTYPE html>
<html>

<head>

<title>Mobile Deposit - Chitaranjan Bank</title>

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

{{ style|safe }}

<style>

.mobile-container {
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 20px;
}

.mobile-card {
    width: 100%;
    max-width: 420px;
    background: rgba(15,23,42,0.92);
    border: 1px solid rgba(148,163,184,0.15);
    border-radius: 25px;
    padding: 30px;
    box-shadow: 0 25px 70px rgba(0,0,0,0.4);
}

.mobile-logo {
    width: 65px;
    height: 65px;
    margin: auto;
    border-radius: 18px;
    background: linear-gradient(135deg,#2563eb,#06b6d4);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 27px;
    font-weight: bold;
    margin-bottom: 20px;
}

.mobile-title {
    text-align: center;
    font-size: 24px;
    font-weight: bold;
}

.mobile-subtitle {
    text-align: center;
    color: #94a3b8;
    font-size: 13px;
    margin-top: 8px;
    line-height: 1.5;
}

.mobile-account {
    margin-top: 25px;
    padding: 15px;
    border-radius: 13px;
    background: rgba(37,99,235,0.10);
    border: 1px solid rgba(37,99,235,0.20);
}

.mobile-account-label {
    color: #94a3b8;
    font-size: 12px;
}

.mobile-account-name {
    font-weight: bold;
    margin-top: 5px;
}

.mobile-form {
    margin-top: 25px;
}

.mobile-form label {
    display: block;
    color: #cbd5e1;
    margin-bottom: 8px;
    font-size: 14px;
}

.amount-input {
    font-size: 22px;
    text-align: center;
    padding: 18px;
}

.mobile-btn {
    margin-top: 5px;
    padding: 17px;
    font-size: 16px;
}

.secure-text {
    text-align: center;
    margin-top: 18px;
    color: #86efac;
    font-size: 12px;
}

.error-box {
    background: rgba(239,68,68,0.10);
    border: 1px solid rgba(239,68,68,0.20);
    color: #fecaca;
    padding: 13px;
    border-radius: 10px;
    margin-top: 15px;
    font-size: 13px;
}

.success-icon {
    font-size: 65px;
    text-align: center;
    margin-bottom: 15px;
}

.success-title {
    text-align: center;
    font-size: 25px;
    font-weight: bold;
    color: #86efac;
}

.success-amount {
    text-align: center;
    font-size: 38px;
    font-weight: bold;
    margin: 20px 0;
}

.success-message {
    text-align: center;
    color: #94a3b8;
    line-height: 1.6;
    font-size: 14px;
}

</style>

</head>


<body>

<div class="mobile-container">

<div class="mobile-card">

    <div class="mobile-logo">
        CB
    </div>

    <div class="mobile-title">
        Chitaranjan Bank
    </div>

    <div class="mobile-subtitle">
        Secure Mobile Deposit
    </div>


    {% if error %}

    <div class="error-box">
        {{ error }}
    </div>

    {% endif %}


    <div class="mobile-account">

        <div class="mobile-account-label">
            DEPOSIT ACCOUNT
        </div>

        <div class="mobile-account-name">
            {{ customer_name }}
        </div>

    </div>


    <form
        class="mobile-form"
        method="POST"
    >

        <label>
            Enter Deposit Amount
        </label>

        <input
            class="amount-input"
            type="number"
            name="amount"
            step="0.01"
            min="0.01"
            placeholder="₹ 0.00"
            required
            autofocus
        >

        <button
            class="btn mobile-btn"
            type="submit"
        >
            Confirm Deposit
        </button>

    </form>


    <div class="secure-text">
        🔒 Secure connection • Chitaranjan Bank of Manipur
    </div>

</div>

</div>

</body>

</html>
"""


# ============================================================
# SUCCESS PAGE
# ============================================================

SUCCESS_HTML = """
<!DOCTYPE html>
<html>

<head>

<title>Deposit Successful</title>

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

{{ style|safe }}

</head>


<body>

<div class="mobile-container">

<div class="mobile-card">

    <div class="success-icon">
        ✅
    </div>

    <div class="success-title">
        Deposit Successful
    </div>

    <div class="success-amount">
        ₹{{ "%.2f"|format(amount) }}
    </div>

    <div class="success-message">

        Your deposit has been successfully added
        to the account.

        <br><br>

        The balance on the bank dashboard
        will update automatically.

    </div>

    <div class="mobile-account">

        <div class="mobile-account-label">
            ACCOUNT HOLDER
        </div>

        <div class="mobile-account-name">
            {{ customer_name }}
        </div>

    </div>

</div>

</div>

</body>

</html>
"""


# ============================================================
# LOGIN / CREATE ACCOUNT PAGE
# ============================================================

LOGIN_HTML = """
<!DOCTYPE html>
<html>

<head>

<title>Chitaranjan Bank of Manipur</title>

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

{{ style|safe }}

<style>

.login-container {
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 20px;
}

.login-card {
    width: 100%;
    max-width: 480px;
    background: rgba(15,23,42,0.85);
    border: 1px solid rgba(148,163,184,0.15);
    border-radius: 25px;
    padding: 35px;
    box-shadow: 0 30px 80px rgba(0,0,0,0.35);
}

.login-logo {
    width: 75px;
    height: 75px;
    margin: auto;
    border-radius: 20px;
    background: linear-gradient(135deg,#2563eb,#06b6d4);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 30px;
    font-weight: bold;
    box-shadow: 0 15px 35px rgba(37,99,235,0.30);
}

.login-title {
    text-align: center;
    font-size: 25px;
    font-weight: bold;
    margin-top: 20px;
}

.login-subtitle {
    text-align: center;
    color: #94a3b8;
    font-size: 13px;
    margin-top: 8px;
    margin-bottom: 30px;
}

.form-group {
    margin-bottom: 15px;
}

.form-label {
    display: block;
    color: #cbd5e1;
    font-size: 13px;
    margin-bottom: 7px;
}

.error-message {
    background: rgba(239,68,68,0.10);
    border: 1px solid rgba(239,68,68,0.20);
    color: #fecaca;
    padding: 13px;
    border-radius: 10px;
    margin-bottom: 18px;
    font-size: 13px;
}

.rules {
    margin-top: 18px;
    color: #64748b;
    font-size: 12px;
    line-height: 1.7;
}

</style>

</head>


<body>

<div class="login-container">

<div class="login-card">

    <div class="login-logo">
        CB
    </div>

    <div class="login-title">
        Chitaranjan Bank of Manipur
    </div>

    <div class="login-subtitle">
        Create Your Digital Bank Account
    </div>


    {% if message %}

    <div class="error-message">
        {{ message }}
    </div>

    {% endif %}


    <form action="/create-account" method="POST">

        <div class="form-group">

            <label class="form-label">
                Customer Name
            </label>

            <input
                type="text"
                name="name"
                placeholder="Enter your full name"
                required
            >

        </div>


        <div class="form-group">

            <label class="form-label">
                10-Digit Account Number
            </label>

            <input
                type="text"
                name="account_no"
                placeholder="Enter exactly 10 digits"
                maxlength="10"
                pattern="[0-9]{10}"
                required
            >

        </div>


        <div class="form-group">

            <label class="form-label">
                Initial Balance
            </label>

            <input
                type="number"
                name="initial_balance"
                step="0.01"
                min="500"
                placeholder="Minimum ₹500"
                required
            >

        </div>


        <button class="btn" type="submit">
            Create Bank Account
        </button>

    </form>


    <div class="rules">

        ✓ Account number must contain exactly 10 digits<br>
        ✓ Minimum initial balance is ₹500<br>
        ✓ Deposit amount must be greater than ₹0<br>
        ✓ Withdrawal cannot exceed available balance

    </div>

</div>

</div>

</body>

</html>
"""


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    global account

    if account is None:

        return render_template_string(
            LOGIN_HTML,
            style=BASE_STYLE,
            message=""
        )

    return render_template_string(
        DASHBOARD_HTML,
        style=BASE_STYLE,
        account=account,
        message=message,
        message_type=message_type
    )


# ============================================================
# CREATE ACCOUNT
# ============================================================

@app.route("/create-account", methods=["POST"])
def create_account():

    global account
    global message
    global message_type

    name = request.form.get("name", "").strip()
    account_no = request.form.get("account_no", "").strip()

    try:
        initial_balance = float(
            request.form.get("initial_balance", "0")
        )
    except ValueError:
        initial_balance = 0

    # Name validation

    if not name:

        return render_template_string(
            LOGIN_HTML,
            style=BASE_STYLE,
            message="Please enter your name."
        )


    # Account number validation

    if not account_no.isdigit() or len(account_no) != 10:

        return render_template_string(
            LOGIN_HTML,
            style=BASE_STYLE,
            message="Account number must be exactly 10 digits."
        )


    # Initial balance validation

    if initial_balance < 500:

        return render_template_string(
            LOGIN_HTML,
            style=BASE_STYLE,
            message="Initial balance must be at least ₹500."
        )


    customer = Customer(name)

    account = Account(
        customer,
        account_no,
        initial_balance
    )

    message = "Account created successfully."
    message_type = "success"

    return redirect(url_for("home"))


# ============================================================
# DEPOSIT FROM LAPTOP
# ============================================================

@app.route("/deposit", methods=["POST"])
def deposit():

    global message
    global message_type

    if account is None:
        return redirect(url_for("home"))

    try:

        amount = float(
            request.form.get("amount", "0")
        )

    except ValueError:

        amount = 0


    if amount <= 0:

        message = "Deposit amount must be greater than ₹0."
        message_type = "error"

        return redirect(url_for("home"))


    account.deposit(
        amount,
        "Cash / Online Deposit"
    )

    message = (
        f"₹{amount:.2f} deposited successfully."
    )

    message_type = "success"

    return redirect(url_for("home"))


# ============================================================
# WITHDRAW
# ============================================================

@app.route("/withdraw", methods=["POST"])
def withdraw():

    global message
    global message_type

    if account is None:
        return redirect(url_for("home"))

    try:

        amount = float(
            request.form.get("amount", "0")
        )

    except ValueError:

        amount = 0


    if amount <= 0:

        message = "Withdrawal amount must be greater than ₹0."
        message_type = "error"

        return redirect(url_for("home"))


    if amount > account.balance:

        message = (
            f"Insufficient balance. "
            f"Available balance is ₹{account.balance:.2f}."
        )

        message_type = "error"

        return redirect(url_for("home"))


    account.withdraw(amount)

    message = (
        f"₹{amount:.2f} withdrawn successfully."
    )

    message_type = "success"

    return redirect(url_for("home"))


# ============================================================
# GENERATE QR CODE FOR PHONE DEPOSIT
# ============================================================

@app.route("/generate-deposit-qr")
def generate_deposit_qr():

    if account is None:

        return jsonify({
            "success": False,
            "message": "No active account."
        })


    # Create a unique temporary token

    token = uuid.uuid4().hex


    # Token valid for 10 minutes

    pending_deposits[token] = {
        "account_no": account.account_no,
        "created": time.time(),
        "used": False
    }


    # IMPORTANT:
    #
    # The laptop should be opened using its LAN IP.
    #
    # Example:
    #
    # http://192.168.1.10:5000
    #
    # Then request.host_url will become:
    #
    # http://192.168.1.10:5000/
    #
    # which the phone can access.

    deposit_url = (
        request.host_url.rstrip("/")
        + url_for(
            "phone_deposit",
            token=token
        )
    )


    # Create QR

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )

    qr.add_data(deposit_url)
    qr.make(fit=True)

    img = qr.make_image(
        fill_color="black",
        back_color="white"
    )


    # Convert QR image to Base64

    buffer = io.BytesIO()

    img.save(
        buffer,
        format="PNG"
    )

    qr_base64 = base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")


    return jsonify({
        "success": True,
        "qr": qr_base64
    })


# ============================================================
# PHONE DEPOSIT PAGE
# ============================================================

@app.route(
    "/phone-deposit/<token>",
    methods=["GET", "POST"]
)
def phone_deposit(token):

    # Check account

    if account is None:

        return """
        <h2>Bank session expired.</h2>
        <p>Please generate a new QR code from the bank website.</p>
        """


    # Check token

    deposit_data = pending_deposits.get(token)

    if deposit_data is None:

        return """
        <h2>Invalid QR Code</h2>
        <p>Please generate a new QR code from the bank website.</p>
        """


    # Check token expiration

    if time.time() - deposit_data["created"] > 600:

        del pending_deposits[token]

        return """
        <h2>QR Code Expired</h2>
        <p>Please generate a new QR code from the bank website.</p>
        """


    # Check if already used

    if deposit_data["used"]:

        return """
        <h2>QR Code Already Used</h2>
        <p>Please generate a new QR code from the bank website.</p>
        """


    # POST = phone submitted amount

    if request.method == "POST":

        try:

            amount = float(
                request.form.get(
                    "amount",
                    "0"
                )
            )

        except ValueError:

            amount = 0


        # Deposit amount validation

        if amount <= 0:

            return render_template_string(
                PHONE_DEPOSIT_HTML,
                style=BASE_STYLE,
                customer_name=account.customer.name,
                error="Deposit amount must be greater than ₹0."
            )


        # Deposit money

        account.deposit(
            amount,
            "QR Mobile Deposit"
        )


        # Mark QR as used

        pending_deposits[token]["used"] = True


        # Show success page

        return render_template_string(
            SUCCESS_HTML,
            style=BASE_STYLE,
            amount=amount,
            customer_name=account.customer.name
        )


    # GET = show phone deposit page

    return render_template_string(
        PHONE_DEPOSIT_HTML,
        style=BASE_STYLE,
        customer_name=account.customer.name,
        error=""
    )


# ============================================================
# ACCOUNT API
# Used by laptop to automatically update balance
# ============================================================

@app.route("/api/account")
def account_api():

    if account is None:

        return jsonify({
            "logged_in": False
        })


    return jsonify({
        "logged_in": True,
        "balance": account.balance,
        "transactions": account.transactions
    })


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout", methods=["POST"])
def logout():

    global account
    global pending_deposits
    global message
    global message_type

    account = None

    pending_deposits = {}

    message = ""
    message_type = ""

    return redirect(url_for("home"))


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("   CHITARANJAN BANK OF MANIPUR")
    print("=" * 60)
    print()
    print("Bank website is starting...")
    print()
    print("On this laptop:")
    print("http://127.0.0.1:5000")
    print()
    print("For PHONE QR DEPOSIT:")
    print("Open the website using the laptop's Wi-Fi IP address.")
    print("Example:")
    print("http://192.168.1.10:5000")
    print()
    print("Both laptop and phone must be on the same Wi-Fi.")
    print()
    print("=" * 60)
    print()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )