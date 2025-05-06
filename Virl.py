import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import time
from streamlit_option_menu import option_menu
import plotly.express as px
import joblib
import numpy as np

# Page configuration
st.set_page_config(
    page_title="MFI Credit Risk Assessment",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
/* Main app styling */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background: linear-gradient(135deg, #1a2a6c 0%, #2a5298 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.1) !important;
}

/* Metric cards */
.metric-card {
    background: white;
    border-radius: 10px;
    padding: 15px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    text-align: center;
    margin-bottom: 20px;
}

.metric-card h3 {
    color: #4b6cb7;
    font-size: 1rem;
    margin-bottom: 5px;
}

.metric-card h1 {
    color: #2a5298;
    font-size: 2rem;
    margin-top: 0;
}

/* Custom cards */
.custom-card {
    background: white;
    border-radius: 10px;
    padding: 20px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    margin-bottom: 20px;
}

.custom-card h2 {
    color: #4b6cb7;
    margin-top: 0;
}

/* Buttons */
.stButton>button {
    border: none;
    background: linear-gradient(135deg, #4e54c8 0%, #8f94fb 100%);
    color: white;
    font-weight: bold;
    border-radius: 8px;
}

.stButton>button:hover {
    background: linear-gradient(135deg, #3a3f9e 0%, #6a6fc9 100%);
}

/* Input fields */
.stTextInput>div>div>input, .stTextInput>div>div>input:focus {
    color: #333333;
    background-color: rgba(255,255,255,0.9);
    border-radius: 8px;
}

/* Tabs */
.stTabs [data-baseweb="tab"] {
    padding: 12px 20px;
    background-color: rgba(255,255,255,0.1);
    color: white !important;
    border-radius: 8px 8px 0 0;
}

.stTabs [aria-selected="true"] {
    background-color: rgba(255,255,255,0.3) !important;
    font-weight: bold;
}

/* Animations */
@keyframes pulse {
    0% { transform: scale(1); opacity: 0.8; }
    50% { transform: scale(1.05); opacity: 1; }
    100% { transform: scale(1); opacity: 0.8; }
}

/* Login page specific */
.login-container {
    background: rgba(255, 255, 255, 0.15);
    backdrop-filter: blur(10px);
    border-radius: 15px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    padding: 30px;
    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15);
}

.login-header {
    text-align: center;
    margin-bottom: 20px;
}

.login-header h2 {
    color: white;
    font-weight: bold;
    animation: pulse 2s infinite;
}

.login-header p {
    color: rgba(255,255,255,0.8);
    margin-top: 5px;
}
</style>
""", unsafe_allow_html=True)

# Database functions
def init_db():
    conn = sqlite3.connect('mfi_credit_risk.db')
    c = conn.cursor()
    
    # Create users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            email TEXT,
            full_name TEXT,
            role TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create applications table
    c.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            applicant_name TEXT,
            age INTEGER,
            gender TEXT,
            marital_status TEXT,
            employment_type TEXT,
            monthly_income REAL,
            loan_amount REAL,
            loan_type TEXT,
            purpose TEXT,
            risk_score REAL,
            risk_category TEXT,
            decision TEXT,
            officer_username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (officer_username) REFERENCES users(username)
        )
    ''')
    
    # Create borrowers table
    c.execute('''
        CREATE TABLE IF NOT EXISTS borrowers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            borrower_id TEXT,
            name TEXT,
            current_risk_level TEXT,
            last_updated TIMESTAMP,
            officer_username TEXT,
            FOREIGN KEY (officer_username) REFERENCES users(username))
    ''')
    
    conn.commit()
    conn.close()

def add_user(username, password, email, full_name, role="credit_officer"):
    conn = sqlite3.connect('mfi_credit_risk.db')
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (username, hashlib.sha256(password.encode()).hexdigest(), email, full_name, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username, password):
    conn = sqlite3.connect('mfi_credit_risk.db')
    c = conn.cursor()
    c.execute(
        "SELECT 1 FROM users WHERE username = ? AND password = ?",
        (username, hashlib.sha256(password.encode()).hexdigest()))
    result = c.fetchone() is not None
    conn.close()
    return result

def user_exists(username):
    conn = sqlite3.connect('mfi_credit_risk.db')
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE username = ?", (username,))
    result = c.fetchone() is not None
    conn.close()
    return result

# Login Page
def login_page():
    st.markdown("""
    <div style="display: flex; justify-content: center; padding-top: 40px;">
        <div style="width: 100%; max-width: 900px;">
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%;">
            <div style="width: 150px; height: 150px; background: linear-gradient(135deg, #4e54c8 0%, #8f94fb 100%); 
                        border-radius: 50%; display: flex; align-items: center; justify-content: center; 
                        margin-bottom: 20px;">
                <span style="font-size: 3rem; color: white;">💰</span>
            </div>
            <div style="text-align: center;">
                <h1 style="color: #2a5298; margin-bottom: 5px;">MFI Credit Risk</h1>
                <p style="color: #4b6cb7; font-size: 1.1rem;">Smart credit assessment for microfinance</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="login-container">
            <div class="login-header">
                <h2>🔒 Access Portal</h2>
                <p>Login or register to continue</p>
            </div>
        """, unsafe_allow_html=True)

        login_tab, signup_tab = st.tabs(["**🔐 LOGIN**", "**🆕 SIGN UP**"])

        with login_tab:
            with st.form("Login Form"):
                st.markdown("<h3 style='color: white; text-align: center; margin-bottom: 30px;'>Welcome Back!</h3>", unsafe_allow_html=True)
                username = st.text_input("**Username**", key="login_username")
                password = st.text_input("**Password**", type="password", key="login_password")

                col_a, col_b = st.columns([1, 2])
                with col_a:
                    remember = st.checkbox("Remember me", value=True)
                with col_b:
                    st.markdown("""
                        <div style="text-align: right; margin-top: 10px;">
                            <a href='#' style='color: rgba(255,255,255,0.8); text-decoration: none; font-size: 0.9rem;'>Forgot password?</a>
                        </div>
                    """, unsafe_allow_html=True)

                if st.form_submit_button("LOGIN", type="primary", use_container_width=True):
                    if verify_user(username, password):
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = username
                        st.success("Login successful!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Invalid credentials")

        with signup_tab:
            with st.form("Signup Form"):
                st.markdown("<h3 style='color: white; text-align: center; margin-bottom: 30px;'>Create Account</h3>", unsafe_allow_html=True)

                col1, col2 = st.columns(2)
                with col1:
                    full_name = st.text_input("**Full Name**", key="signup_name")
                with col2:
                    email = st.text_input("**Email**", key="signup_email")

                username = st.text_input("**Username**", key="signup_username")
                password = st.text_input("**Password**", type="password", key="signup_password")
                terms = st.checkbox("**I agree to the Terms & Conditions**", key="terms_checkbox")

                if st.form_submit_button("CREATE ACCOUNT", type="primary", use_container_width=True):
                    if not terms:
                        st.warning("Please accept the Terms & Conditions")
                    elif user_exists(username):
                        st.error("Username already exists")
                    elif add_user(username, password, email, full_name):
                        st.success("Account created successfully! Please login.")
                    else:
                        st.error("Error creating account")

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("""
        </div>
    </div>
    """, unsafe_allow_html=True)

# Sidebar
def sidebar():
    with st.sidebar:
        # Header Section
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem; padding-top: 1rem;">
            <h2 style="color: white; margin-bottom: 0;">MFI Credit Risk</h2>
            <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem; font-size: 0.9rem;">
                Microfinance Credit Assessment System
            </p>
        </div>
        """, unsafe_allow_html=True)

        # User Profile Card
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.15);
                    backdrop-filter: blur(5px);
                    border-radius: 10px;
                    padding: 1rem;
                    margin-bottom: 1.5rem;
                    border: 1px solid rgba(255,255,255,0.2);">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="width: 42px; height: 42px; background: #8f94fb; 
                            border-radius: 50%; display: flex; align-items: center; 
                            justify-content: center; color: white; font-weight: bold;">
                    {st.session_state.get('username', '?')[0].upper()}
                </div>
                <div>
                    <p style="margin: 0; font-weight: 600; color: white; font-size: 0.95rem;">
                        {st.session_state.get('username', 'Guest User')}
                    </p>
                    <p style="margin: 0; font-size: 0.8rem; color: rgba(255,255,255,0.7);">
                        Credit Officer
                    </p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Navigation Menu 
        selected = option_menu(
            menu_title=None,
            options=["Dashboard", "Application Screening", "Borrower Monitoring"],
            icons=["house", "clipboard-check", "people"],
            default_index=0,
            styles={
                "container": {
                    "padding": "8px",
                    "background-color": "rgba(255,255,255,0.05)",
                    "border-radius": "10px"
                },
                "icon": {
                    "color": "#4e54c8",
                    "font-size": "18px"
                },
                "nav-link": {
                    "font-size": "15px",
                    "color": "black",
                    "margin": "4px 0",
                    "padding": "10px 18px",
                    "border-radius": "8px",
                    "transition": "0.3s ease"
                },
                "nav-link-selected": {
                    "background-color": "#4e54c8",
                    "color": "white",
                    "font-weight": "600",
                    "box-shadow": "0 0 0 1px rgba(255,255,255,0.1) inset"
                },
                "nav-link:hover": {
                    "background-color": "rgba(255,255,255,0.15)"
                }
            }
        )

        # System Status
        st.markdown("""
        <div style="background: rgba(255,255,255,0.15);
                    backdrop-filter: blur(5px);
                    border-radius: 10px;
                    padding: 1rem;
                    margin: 1.5rem 0;
                    border: 1px solid rgba(255,255,255,0.2);">
            <h4 style="color: white; margin-top: 0; margin-bottom: 15px;">System Status</h4>
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <div style="width: 10px; height: 10px; background: #4CAF50; border-radius: 50%; margin-right: 10px;"></div>
                <span style="color: white; font-size: 0.9rem;">Operational</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <div style="width: 10px; height: 10px; background: #2196F3; border-radius: 50%; margin-right: 10px;"></div>
                <span style="color: white; font-size: 0.9rem;">Model Accuracy: 89%</span>
            </div>
            <div style="display: flex; align-items: center;">
                <div style="width: 10px; height: 10px; background: #FFC107; border-radius: 50%; margin-right: 10px;"></div>
                <span style="color: white; font-size: 0.9rem;">Last Updated: Today</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # End Session Button
        st.markdown("---")
        if st.button("⏹️ Sign Out", use_container_width=True):
            st.session_state.clear()
            st.success("Signed out successfully.")
            st.rerun()

        # Footer 
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0; font-size: 0.75rem;
                    color: rgba(255,255,255,0.5);">
            <hr style="border-color: rgba(255,255,255,0.1); margin-bottom: 10px;">
            MFI Credit Risk System • 2025
        </div>
        """, unsafe_allow_html=True)

        return selected


# Dashboard Tab
def dashboard_tab():
    st.markdown("""
    <div style="margin-bottom: 2rem;">
        <h1 style="color: #2a5298;">Credit Risk Dashboard</h1>
        <p style="color: #666;">Overview of credit risk assessment metrics and trends</p>
    </div>
    """, unsafe_allow_html=True)

    # Load data
    df = pd.read_excel("MFI_Credit_Risk_Data.xlsx", sheet_name="Loan_Screening_Model")

    # KPIs
    total_apps = len(df)
    approved = df[df["default_status"] == 0]
    approval_rate = round((len(approved) / total_apps) * 100, 1)
    avg_loan_amount = round(df["loan_amount_usd"].mean(), 2)
    high_risk = len(df[df["default_status"] == 1])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>Total Applications</h3>
            <h1>{total_apps}</h1>
            <p style="color: #4CAF50;">Live count</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>Approval Rate</h3>
            <h1>{approval_rate}%</h1>
            <p style="color: #4CAF50;">Based on defaults</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>Avg Loan Amount</h3>
            <h1>${avg_loan_amount}</h1>
            <p style="color: #666;">USD</p>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3>High Risk (Defaulted)</h3>
            <h1>{high_risk}</h1>
            <p style="color: #F44336;">Flagged</p>
        </div>
        """, unsafe_allow_html=True)

    # Charts
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="custom-card"><h2 style="color:#4b6cb7;">Income vs Loan Amount</h2>', unsafe_allow_html=True)
        fig = px.scatter(df, x="monthly_income_usd", y="loan_amount_usd",
                         color=df["default_status"].map({0: "Approved", 1: "Defaulted"}),
                         labels={"color": "Status"})
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="custom-card"><h2 style="color:#4b6cb7;">Loan Purpose Distribution</h2>', unsafe_allow_html=True)
        purpose_data = df["purpose_of_loan"].value_counts().reset_index()
        purpose_data.columns = ["Purpose", "Count"]
        fig = px.pie(purpose_data, values="Count", names="Purpose", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Application Table
    st.markdown('<div class="custom-card"><h2 style="color:#4b6cb7;">Historical Applications Data</h2>', unsafe_allow_html=True)
    st.dataframe(df.tail(10).reset_index(drop=True), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)



# Application Screening Tab 
def borrower_monitoring_tab():
    st.markdown("""
    <div style="margin-bottom: 2rem;">
        <h1 style="color: #2a5298;">📈 Borrower Monitoring</h1>
        <p style="color: #666;">Track ongoing performance of active borrowers using behavioral metrics.</p>
    </div>
    """, unsafe_allow_html=True)

    df = pd.read_excel("MFI_Credit_Risk_Data.xlsx", sheet_name="Borrower_Tracking_Data")

    # KPIs
    st.markdown("""
    <div class="custom-card" style="margin-bottom:2rem;">
        <h2 style="color:#4b6cb7;">Portfolio Overview</h2>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("Borrowers Tracked", len(df))
    col2.metric("Avg Repayment Score", f"{df['repayment_history_score'].mean():.2f}")
    col3.metric("High Risk Borrowers", len(df[df['current_risk_level'] == 'High']))

    # Risk level pie chart
    st.markdown('<div class="custom-card"><h2 style="color:#4b6cb7;">Risk Level Distribution</h2>', unsafe_allow_html=True)
    fig1 = px.pie(df, names="current_risk_level", title="Borrower Risk Categories")
    st.plotly_chart(fig1, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Top risky borrowers table
    st.markdown('<div class="custom-card"><h2 style="color:#4b6cb7;">🔍 High Risk Borrowers</h2>', unsafe_allow_html=True)
    risky = df[df["current_risk_level"] == "High"].sort_values(by="repayment_history_score")
    st.dataframe(risky.head(10), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    

# Borrower Monitoring Tab 
def application_screening_tab():
    st.markdown("""
    <div style="margin-bottom: 2rem;">
        <h1 style="color: #2a5298;">📋 Application Screening</h1>
        <p style="color: #666;">Enter borrower information and assess their credit risk.</p>
    </div>
    """, unsafe_allow_html=True)

    # Load model
    model_bundle = joblib.load("credit_risk_gb_model.pkl")
    model = model_bundle["model"]
    scaler = model_bundle["scaler"]
    label_encoders = model_bundle["label_encoders"]
    

    # Input form
    with st.form("screening_form"):
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Age", 18, 70, value=30)
            gender = st.selectbox("Gender", ["Male", "Female"])
            marital_status = st.selectbox("Marital Status", ["Single", "Married", "Divorced", "Widowed"])
            employment_type = st.selectbox("Employment Type", ["Formal", "Self-Employed", "Informal", "Unemployed"])
            monthly_income = st.number_input("Monthly Income (USD)", 0.0, 2000.0, value=250.0)
            number_of_dependents = st.slider("Number of Dependents", 0, 10, 1)

        with col2:
            education_level = st.selectbox("Education Level", ["None", "Primary", "Secondary", "Tertiary"])
            loan_amount_usd = st.number_input("Requested Loan Amount (USD)", 50.0, 1500.0, value=300.0)
            loan_type = st.selectbox("Loan Type", ["Individual", "Group"])
            repayment_period = st.selectbox("Repayment Period (Months)", [1, 3, 6])
            interest_rate = st.slider("Interest Rate (%)", 5.0, 20.0, value=12.0)
            purpose = st.selectbox("Purpose of Loan", ["Business", "School Fees", "Medical", "Food", "Household Improvements"])

        area_type = st.selectbox("Residential Area", ["Urban", "Peri-Urban", "Rural"])
        sector = st.selectbox("Sector of Activity", ["Trading", "Agriculture", "Services"])

        submitted = st.form_submit_button("🧠 Predict Risk")

        if submitted:
            input_dict = {
                "age": age,
                "gender": label_encoders["gender"].transform([gender])[0],
                "marital_status": label_encoders["marital_status"].transform([marital_status])[0],
                "employment_type": label_encoders["employment_type"].transform([employment_type])[0],
                "monthly_income_usd": monthly_income,
                "number_of_dependents": number_of_dependents,
                "education_level": label_encoders["education_level"].transform([education_level])[0],
                "loan_amount_usd": loan_amount_usd,
                "loan_type": label_encoders["loan_type"].transform([loan_type])[0],
                "repayment_period_months": repayment_period,
                "interest_rate_percent": interest_rate,
                "purpose_of_loan": label_encoders["purpose_of_loan"].transform([purpose])[0],
                "residential_area_type": label_encoders["residential_area_type"].transform([area_type])[0],
                "sector_of_activity": label_encoders["sector_of_activity"].transform([sector])[0]
            }

            input_array = scaler.transform([list(input_dict.values())])
            model_pred = model.predict(input_array)[0]
            pd_score = model.predict_proba(input_array)[0][1]  # Probability of default (class 1)

            # Rule-based assessment
            rule_flags = []
            critical_violations = 0

            # Rule 1: Age extremes
            if age < 21 or age > 60:
                rule_flags.append("Age is outside the preferred lending bracket (21–60)")
                critical_violations += 1

            # Rule 2: High number of dependents
            if number_of_dependents > 3:
                rule_flags.append("More than 3 dependents may strain income")
                critical_violations += 1

            # Rule 3: Income-to-loan ratio
            monthly_instalment_est = (loan_amount_usd * (1 + (interest_rate / 100))) / repayment_period
            if monthly_instalment_est > 0.4 * monthly_income:
                rule_flags.append(f"Loan burden ({monthly_instalment_est:.2f}) exceeds 40% of monthly income ({monthly_income:.2f})")
                critical_violations += 1

            # Rule 4: Very low income
            if monthly_income < 80:
                rule_flags.append("Monthly income is below sustainable threshold ($80)")
                critical_violations += 1

            # Rule 5: Unemployed applicants
            if employment_type == "Unemployed":
                rule_flags.append("Unemployment increases risk of default")
                critical_violations += 1

            # Final logic: Override model if 2+ critical rules triggered
            if critical_violations >= 2:
                final_prediction = 1
                overridden = True
            else:
                final_prediction = model_pred
                overridden = False

            # Display results
            risk_label = "✅ Low Risk" if final_prediction == 0 else "⚠️ High Risk"
            st.success(f"**Final Risk Assessment:** {risk_label}")
            st.info(f"**Model-predicted Probability of Default (PD):** {pd_score:.2%}")

            if rule_flags:
                st.warning("📋 Rule-based risk insights:")
                for flag in rule_flags:
                    st.markdown(f"- {flag}")

            if overridden:
                st.markdown("🔁 *Model risk prediction overridden based on multiple high-risk flags*")

        
# Main App
def main_app():
    selected_tab = sidebar()
    
    if selected_tab == "Dashboard":
        dashboard_tab()
    elif selected_tab == "Application Screening":
        application_screening_tab()
    elif selected_tab == "Borrower Monitoring":
        borrower_monitoring_tab()

# Initialize database
init_db()

# Check authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if st.session_state.authenticated:
    main_app()
else:
    login_page()