import os
import json
import random
import time
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g, flash
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.colors import HexColor, black, green, yellow, red, blue, purple, orange
from reportlab.lib.units import inch # Import inch for spacing
from io import BytesIO # For PDF generation
from dotenv import load_dotenv
import fitz # PyMuPDF
from datetime import datetime
from functools import wraps

# Import services
from gemini_service import get_gemini_insights, get_mock_swot_analysis, get_mock_company_comparison
from risk_calculator import calculate_better_risk_assessment # UPDATED: Import new risk calculation function
from gemini_advisor_service import get_advisor_response # NEW: Import for advisor chat

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecretkey') # Use environment variable for secret key
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB limit

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Database Setup (SQLite) ---
DATABASE = 'database.db'

def get_db_connection():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row # This allows accessing columns by name
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            company TEXT,
            job_title TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            project_name TEXT NOT NULL,
            industry TEXT NOT NULL,
            description TEXT NOT NULL,
            budget REAL NOT NULL,
            timeline TEXT NOT NULL,
            location TEXT NOT NULL,
            number_of_cofounders INTEGER NOT NULL,
            technical_complexity INTEGER NOT NULL,
            total_expense REAL NOT NULL,
            total_revenue REAL NOT NULL,
            resumes_uploaded INTEGER DEFAULT 0,
            overall_risk REAL NOT NULL,
            risk_level TEXT NOT NULL,
            z_score_analysis TEXT NOT NULL, -- Store as JSON string (now stores explanation)
            gemini_analysis TEXT, -- Store as JSON string (now stores combined SWOT and comparison)
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    # NEW: Organizations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE, -- User who registered/owns this organization
            name TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            contact_person TEXT,
            logo_url TEXT, -- Optional URL for logo
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()

# Initialize the database when the app starts
with app.app_context():
    init_db()

# --- Authentication Decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        # Check if user is an organization - if so, redirect to main page
        conn = get_db_connection()
        org_check = conn.execute('SELECT id FROM organizations WHERE user_id = ?', (session['user_id'],)).fetchone()
        # Don't close connection here - let teardown_appcontext handle it
        
        if org_check:
            # User is an organization - redirect to main page with message
            flash('Organizations cannot access the dashboard. Your information is available for users to contact you.', 'info')
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return decorated_function

# Helper function to format currency
def format_currency_inr(amount):
    if amount is None:
        return "N/A"
    return "₹{:,}".format(int(amount))

app.jinja_env.filters['format_currency_inr'] = format_currency_inr

# --- Global ReportLab Styles (Defined once) ---
# This prevents "Style 'BodyText' already defined in stylesheet" error
_styles = getSampleStyleSheet()

_styles['h1'].fontSize = 24
_styles['h1'].spaceAfter = 20
_styles['h1'].alignment = TA_CENTER
_styles['h1'].textColor = HexColor('#1a202c') # gray-900

_styles['h2'].fontSize = 18
_styles['h2'].spaceBefore = 20
_styles['h2'].spaceAfter = 10
_styles['h2'].textColor = HexColor('#2d3748') # gray-800

_styles['h3'].fontSize = 14
_styles['h3'].spaceBefore = 15
_styles['h3'].spaceAfter = 5
_styles['h3'].textColor = HexColor('#4a5568') # gray-700

_styles.add(ParagraphStyle(name='BodyTextCustom',
                          parent=_styles['Normal'],
                          fontSize=10,
                          leading=14,
                          spaceAfter=6,
                          textColor=HexColor('#4a5568'))) # gray-700

_styles.add(ParagraphStyle(name='ListItemStyleCustom',
                          parent=_styles['Normal'],
                          fontSize=10,
                          leading=14,
                          spaceAfter=3,
                          leftIndent=20, # Increased indent for list items
                          firstLineIndent=-10, # Adjust for bullet
                          textColor=HexColor('#4a5568')))

_styles.add(ParagraphStyle(name='OverallRiskStyleCustom',
                          parent=_styles['h2'], # Inherit from h2 for font size/weight
                          fontSize=20, # Override font size
                          spaceBefore=15,
                          spaceAfter=15,
                          alignment=TA_CENTER)) # Color set dynamically

_styles.add(ParagraphStyle(name='ExplanationStyleCustom',
                          parent=_styles['BodyTextCustom'], # Parent from my custom BodyText
                          fontSize=11,
                          leading=16,
                          spaceBefore=10,
                          spaceAfter=15,
                          textColor=HexColor('#334155'))) # slate-700


@app.route('/')
@login_required
def index():
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    # Don't close connection here - let teardown_appcontext handle it

    # Mock stats for now, can be replaced with actual DB counts later
    stats = {
        "total_assessments": 1247,
        "high_risk_items": 23,
        "medium_risk_items": 156,
        "low_risk_items": 1068,
    }
    features = [
        {"icon": "shield", "title": "Risk Assessment", "description": "Comprehensive risk evaluation with AI-powered analysis", "href": url_for('assessment')},
        {"icon": "bar-chart", "title": "Risk Comparison", "description": "Compare multiple risk scenarios side by side", "href": url_for('compare')},
        {"icon": "file-text", "title": "Generate Reports", "description": "Create detailed PDF reports for stakeholders", "href": url_for('results')},
        {"icon": "users", "title": "Advisory Services", "description": "Get expert advice on risk mitigation strategies", "href": url_for('advisor')},
    ]
    return render_template('index.html', user=user, stats=stats, features=features)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        # Check if user is an organization
        org_check = None
        if user:
            org_check = conn.execute('SELECT id FROM organizations WHERE user_id = ?', (user['id'],)).fetchone()
        # Don't close connection here - let teardown_appcontext handle it

        if user and check_password_hash(user['password_hash'], password):
            # Check if user is an organization
            if org_check:
                # Organization trying to login - redirect to main page with message
                flash('Organizations cannot access the dashboard. Your information is available for users to contact you.', 'info')
                return redirect(url_for('login'))
            else:
                # Regular user - allow login and redirect to dashboard
                session['user_id'] = user['id']
                session['user_email'] = user['email']
                session['user_first_name'] = user['first_name']
                session['user_last_name'] = user['last_name']
                return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid email or password")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        company = request.form.get('company')
        job_title = request.form.get('job_title')
        agree_terms = 'agree_terms' in request.form
        
        # NEW: Organization fields
        register_as_organization = 'register_as_organization' in request.form
        org_name = request.form.get('org_name')
        contact_person = request.form.get('contact_person')
        logo_url = request.form.get('logo_url')

        errors = {}
        conn = get_db_connection()
        existing_user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()

        if not first_name.strip(): errors['first_name'] = "First name is required"
        if not last_name.strip(): errors['last_name'] = "Last name is required"
        if not email.strip(): errors['email'] = "Email is required"
        elif not "@" in email or not "." in email: errors['email'] = "Email is invalid"
        if not password: errors['password'] = "Password is required"
        elif len(password) < 8: errors['password'] = "Password must be at least 8 characters"
        if password != confirm_password: errors['confirm_password'] = "Passwords don't match"
        if not agree_terms: errors['agree_terms'] = "You must agree to the terms and conditions"
        if existing_user: errors['email'] = "Email already registered"

        # NEW: Validate organization fields if registering as organization
        if register_as_organization:
            if not org_name or not org_name.strip(): errors['org_name'] = "Organization name is required."
            
            existing_org_name = conn.execute('SELECT id FROM organizations WHERE name = ?', (org_name,)).fetchone()
            if existing_org_name: errors['org_name'] = "An organization with this name already exists."


        if errors:
            return render_template('register.html', errors=errors, form_data=request.form)
        
        password_hash = generate_password_hash(password)
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (first_name, last_name, email, password_hash, company, job_title) VALUES (?, ?, ?, ?, ?, ?)',
                (first_name, last_name, email, password_hash, company, job_title)
            )
            conn.commit()
            user_id = cursor.lastrowid

            # NEW: Register organization if selected
            if register_as_organization and not errors: # Re-check errors to be safe
                cursor.execute(
                    'INSERT INTO organizations (user_id, name, email, contact_person, logo_url) VALUES (?, ?, ?, ?, ?)',
                    (user_id, org_name, email, contact_person, logo_url)
                )
                conn.commit()
                
                # For organizations: show success message and redirect to main page
                flash('Organization successfully registered! Users can now contact you through our platform.', 'success')
                return redirect(url_for('login'))
            else:
                # For regular users: set session and redirect to assessment
                session['user_id'] = user_id
                session['user_email'] = email
                session['user_first_name'] = first_name
                session['user_last_name'] = last_name
                return redirect(url_for('assessment'))

        except sqlite3.Error as e:
            conn.rollback()
            errors['db_error'] = f"Database error: {e}"
            return render_template('register.html', errors=errors, form_data=request.form)
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_email', None)
    session.pop('user_first_name', None)
    session.pop('user_last_name', None)
    return redirect(url_for('index'))

@app.route('/assessment', methods=['GET'])
@login_required
def assessment():
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    # Don't close connection here - let teardown_appcontext handle it
    return render_template('assessment.html', user=user)

@app.route('/results')
@login_required
def results():
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    latest_assessment = conn.execute(
        'SELECT * FROM assessments WHERE user_id = ? ORDER BY created_at DESC LIMIT 1',
        (session['user_id'],)
    ).fetchone()
    # Don't close connection here - let teardown_appcontext handle it

    if latest_assessment:
        # Convert Row object to dictionary for easier access in JS
        latest_assessment_dict = dict(latest_assessment)
        # Parse JSON strings back to Python objects
        # The z_score_analysis now contains the explanation from the new risk calculation
        latest_assessment_dict['z_score_analysis'] = json.loads(latest_assessment_dict['z_score_analysis'])
        if latest_assessment_dict['gemini_analysis']:
            latest_assessment_dict['gemini_analysis'] = json.loads(latest_assessment_dict['gemini_analysis'])
        return render_template('results.html', assessment=latest_assessment_dict, user=user)
    
    return render_template('results.html', assessment=None, user=user)

@app.route('/compare')
@login_required
def compare():
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    # Fetch the latest assessment for AI comparison insights and overall risk display
    latest_assessment = conn.execute(
        'SELECT * FROM assessments WHERE user_id = ? ORDER BY created_at DESC LIMIT 1',
        (session['user_id'],)
    ).fetchone()
    # Don't close connection here - let teardown_appcontext handle it

    gemini_comparison_data = None
    latest_assessment_dict = None

    if latest_assessment:
        latest_assessment_dict = dict(latest_assessment)
        if latest_assessment_dict['gemini_analysis']:
            try:
                parsed_gemini_analysis = json.loads(latest_assessment_dict['gemini_analysis'])
                gemini_comparison_data = parsed_gemini_analysis.get('comparison')
            except json.JSONDecodeError as e:
                print(f"Error parsing gemini_analysis for comparison page: {e}")
                gemini_comparison_data = None # Ensure it's None if parsing fails
    
    return render_template('compare.html', 
                           user=user,
                           latest_assessment=latest_assessment_dict, # Pass latest assessment for risk display
                           gemini_comparison=gemini_comparison_data) # Pass AI comparison data

@app.route('/advisor')
@login_required
def advisor():
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    latest_assessment = conn.execute(
        'SELECT * FROM assessments WHERE user_id = ? ORDER BY created_at DESC LIMIT 1',
        (session['user_id'],)
    ).fetchone()
    # Don't close connection here - let teardown_appcontext handle it
    
    # Pass user details as a dictionary to the template
    user_details = {
        "first_name": user['first_name'],
        "last_name": user['last_name'],
        "email": user['email'],
        "company": user['company'],
        "job_title": user['job_title']
    } if user else {}

    # Pass latest assessment data to the template for suggested questions
    latest_assessment_dict = None
    if latest_assessment:
        latest_assessment_dict = dict(latest_assessment)
        # Ensure z_score_analysis is parsed if it's a JSON string
        if isinstance(latest_assessment_dict.get('z_score_analysis'), str):
            latest_assessment_dict['z_score_analysis'] = json.loads(latest_assessment_dict['z_score_analysis'])

    return render_template('advisor.html', user=user, user_details=json.dumps(user_details), latest_assessment=latest_assessment_dict)

# NEW: Organizations List Route
@app.route('/organizations', methods=['GET'])
@login_required
def organizations_list():
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone() # For base.html
    organizations = conn.execute('SELECT * FROM organizations ORDER BY name ASC').fetchall()
    # Don't close connection here - let teardown_appcontext handle it
    return render_template('organizations_list.html', user=user, organizations=organizations)


@app.route('/api/submit-assessment', methods=['POST'])
@login_required
def api_submit_assessment():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401

        form_data = request.form
        
        assessment_data = {
            "project_name": form_data.get("projectName"),
            "industry": form_data.get("industry"),
            "description": form_data.get("description"),
            "budget": int(form_data.get("budget")),
            "timeline": form_data.get("timeline"),
            "location": form_data.get("location"),
            "number_of_cofounders": int(form_data.get("numberOfCofounders")),
            "technical_complexity": int(form_data.get("technicalComplexity")),
            "total_expense": int(form_data.get("totalExpense")), # Corrected to totalExpense
            "total_revenue": int(form_data.get("totalRevenue"))
        }
        
        # Validate required fields (simplified for brevity, full validation in JS)
        required_fields = ["project_name", "industry", "description", "budget", "timeline", "location",
                           "number_of_cofounders", "technical_complexity", "total_expense", "total_revenue"]
        for field in required_fields:
            if not assessment_data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # UPDATED: Call the new risk assessment function
        risk_assessment_results = calculate_better_risk_assessment(assessment_data)

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO assessments (
                    user_id, project_name, industry, description, budget, timeline, location,
                    number_of_cofounders, technical_complexity, total_expense, total_revenue,
                    resumes_uploaded, overall_risk, risk_level, z_score_analysis
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    user_id,
                    assessment_data["project_name"],
                    assessment_data["industry"],
                    assessment_data["description"],
                    assessment_data["budget"],
                    assessment_data["timeline"],
                    assessment_data["location"],
                    assessment_data["number_of_cofounders"],
                    assessment_data["technical_complexity"],
                    assessment_data["total_expense"],
                    assessment_data["total_revenue"],
                    0, # resumes_uploaded_count
                    risk_assessment_results["risk_score"], # Use new risk_score
                    risk_assessment_results["risk_level"], # Use new risk_level
                    json.dumps({"explanation": risk_assessment_results["explanation"]}) # Store explanation as JSON
                )
            )
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            print(f"Database error on assessment submission: {e}")
            return jsonify({"error": "Failed to save assessment to database"}), 500
        # Removed finally: conn.close() - rely on teardown_appcontext

        return jsonify({"success": True, "message": "Assessment submitted successfully"})
    except Exception as e:
        print(f"Error processing assessment: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/get-latest-assessment', methods=['GET'])
@login_required
def api_get_latest_assessment():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db_connection()
    latest_assessment = conn.execute(
        'SELECT * FROM assessments WHERE user_id = ? ORDER BY created_at DESC LIMIT 1',
        (user_id,)
    ).fetchone()
    # Don't close connection here - let teardown_appcontext handle it

    if latest_assessment:
        assessment_dict = dict(latest_assessment)
        # Parse JSON strings back to Python objects
        # z_score_analysis now contains the explanation
        assessment_dict['z_score_analysis'] = json.loads(assessment_dict['z_score_analysis'])
        if assessment_dict['gemini_analysis']:
            assessment_dict['gemini_analysis'] = json.loads(assessment_dict['gemini_analysis'])
        return jsonify(assessment_dict), 200
    return jsonify({"error": "No assessment found"}), 404

def generate_risk_report_pdf(assessment_data, gemini_analysis):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)
    
    # Use the globally defined styles
    styles = _styles 

    elements = []

    # Title Page
    elements.append(Paragraph("SmartRisk AI Assessment Report", styles['h1'])) # Use h1
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(Paragraph(f"Project: {assessment_data.get('project_name', 'N/A')}", styles['h2'])) # Use h2
    elements.append(Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}", styles['BodyTextCustom']))
    elements.append(Spacer(1, 1 * inch))
    elements.append(Paragraph("Confidential Report", styles['BodyTextCustom']))
    elements.append(PageBreak())

    # Project Overview
    elements.append(Paragraph("1. Project Overview", styles['h2'])) # Use h2
    elements.append(Paragraph(f"<b>Project Name:</b> {assessment_data.get('project_name', 'N/A')}", styles['BodyTextCustom']))
    elements.append(Paragraph(f"<b>Industry:</b> {assessment_data.get('industry', 'N/A')}", styles['BodyTextCustom']))
    elements.append(Paragraph(f"<b>Description:</b> {assessment_data.get('description', 'N/A')}", styles['BodyTextCustom']))
    elements.append(Paragraph(f"<b>Budget:</b> {format_currency_inr(assessment_data.get('budget', 0))}", styles['BodyTextCustom']))
    elements.append(Paragraph(f"<b>Timeline:</b> {assessment_data.get('timeline', 'N/A')}", styles['BodyTextCustom']))
    elements.append(Paragraph(f"<b>Location:</b> {assessment_data.get('location', 'N/A')}", styles['BodyTextCustom']))
    elements.append(Paragraph(f"<b>Co-founders:</b> {assessment_data.get('number_of_cofounders', 'N/A')}", styles['BodyTextCustom']))
    elements.append(Paragraph(f"<b>Technical Complexity:</b> {assessment_data.get('technical_complexity', 'N/A')}/10", styles['BodyTextCustom']))
    elements.append(Paragraph(f"<b>Expected Revenue:</b> {format_currency_inr(assessment_data.get('total_revenue', 0))}", styles['BodyTextCustom']))
    elements.append(Paragraph(f"<b>Expected Expense:</b> {format_currency_inr(assessment_data.get('total_expense', 0))}", styles['BodyTextCustom']))
    elements.append(Spacer(1, 0.2 * inch))

    # Overall Risk
    risk_level = assessment_data.get('risk_level', 'N/A')
    overall_risk_score = assessment_data.get('overall_risk', 'N/A')
    risk_color = black
    if risk_level == 'Low': risk_color = green
    elif risk_level == 'Medium': risk_color = orange
    elif risk_level == 'High': risk_color = red
    
    styles['OverallRiskStyleCustom'].textColor = risk_color
    elements.append(Paragraph(f"Overall Risk: {risk_level} ({overall_risk_score:.0f}%)", styles['OverallRiskStyleCustom']))
    
    # Add the explanation from the new risk calculation
    explanation_data = assessment_data.get('z_score_analysis', {}) # z_score_analysis now holds the explanation
    explanation_text = explanation_data.get('explanation', 'No detailed explanation available.')
    elements.append(Paragraph(f"<b>Explanation:</b> {explanation_text}", styles['ExplanationStyleCustom']))
    elements.append(Spacer(1, 0.2 * inch))

    # AI-Powered Insights (SWOT)
    elements.append(Paragraph("2. AI-Powered Insights: SWOT Analysis", styles['h2'])) # Re-numbered heading
    swot = gemini_analysis.get('swot', get_mock_swot_analysis()) # Fallback to mock if not present

    elements.append(Paragraph("Strengths:", styles['h3'])) # Use h3
    elements.append(ListFlowable([ListItem(Paragraph(s, styles['ListItemStyleCustom'])) for s in swot.get('strengths', [])],
                                 bulletType='bullet',
                                 bulletColor=green,
                                 start='bullet',
                                 leftIndent=20,
                                 bulletIndent=10))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(Paragraph("Weaknesses:", styles['h3'])) # Use h3
    elements.append(ListFlowable([ListItem(Paragraph(s, styles['ListItemStyleCustom'])) for s in swot.get('weaknesses', [])],
                                 bulletType='bullet',
                                 bulletColor=red,
                                 start='bullet',
                                 leftIndent=20,
                                 bulletIndent=10))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(Paragraph("Opportunities:", styles['h3'])) # Use h3
    elements.append(ListFlowable([ListItem(Paragraph(s, styles['ListItemStyleCustom'])) for s in swot.get('opportunities', [])],
                                 bulletType='bullet',
                                 bulletColor=blue,
                                 start='bullet',
                                 leftIndent=20,
                                 bulletIndent=10))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(Paragraph("Threats:", styles['h3'])) # Use h3
    elements.append(ListFlowable([ListItem(Paragraph(s, styles['ListItemStyleCustom'])) for s in swot.get('threats', [])],
                                 bulletType='bullet',
                                 bulletColor=orange,
                                 start='bullet',
                                 leftIndent=20,
                                 bulletIndent=10))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(Paragraph("Recommendations:", styles['h3'])) # Use h3
    elements.append(ListFlowable([ListItem(Paragraph(s, styles['ListItemStyleCustom'])) for s in swot.get('recommendations', [])],
                                 bulletType='bullet',
                                 bulletColor=purple,
                                 start='bullet',
                                 leftIndent=20,
                                 bulletIndent=10))
    elements.append(Spacer(1, 0.2 * inch))

    # AI-Powered Insights (Company Comparison)
    elements.append(Paragraph("3. AI-Powered Insights: Company Comparison", styles['h2'])) # Re-numbered heading
    comparison = gemini_analysis.get('comparison', get_mock_company_comparison()) # Fallback to mock if not present

    elements.append(Paragraph(f"<b>Successful Company:</b> {comparison.get('successful_company', {}).get('name', 'N/A')}", styles['BodyTextCustom']))
    elements.append(Paragraph(f"<i>Industry: {comparison.get('successful_company', {}).get('industry', 'N/A')}</i>", styles['BodyTextCustom']))
    elements.append(Paragraph("Key Factors for Success:", styles['h3'])) # Use h3
    elements.append(ListFlowable([ListItem(Paragraph(s, styles['ListItemStyleCustom'])) for s in comparison.get('successful_company', {}).get('insights', [])],
                                 bulletType='bullet',
                                 bulletColor=green,
                                 start='bullet',
                                 leftIndent=20,
                                 bulletIndent=10))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(Paragraph(f"<b>Failed Company:</b> {comparison.get('failed_company', {}).get('name', 'N/A')}", styles['BodyTextCustom']))
    elements.append(Paragraph(f"<i>Industry: {comparison.get('failed_company', {}).get('industry', 'N/A')}</i>", styles['BodyTextCustom']))
    elements.append(Paragraph("Key Factors for Failure:", styles['h3'])) # Use h3
    elements.append(ListFlowable([ListItem(Paragraph(s, styles['ListItemStyleCustom'])) for s in comparison.get('failed_company', {}).get('insights', [])],
                                 bulletType='bullet',
                                 bulletColor=red,
                                 start='bullet',
                                 leftIndent=20,
                                 bulletIndent=10))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(Paragraph("Lessons Learned for Your Project:", styles['h3'])) # Use h3
    elements.append(ListFlowable([ListItem(Paragraph(s, styles['ListItemStyleCustom'])) for s in comparison.get('lessons_learned', [])],
                                 bulletType='bullet',
                                 bulletColor=purple,
                                 start='bullet',
                                 leftIndent=20,
                                 bulletIndent=10))
    elements.append(Spacer(1, 0.2 * inch))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

@app.route('/api/gemini-analysis', methods=['POST'])
@login_required
def api_gemini_analysis():
    try:
        data = request.json
        assessment_data = data.get("assessmentData")
        assessment_id = data.get("assessmentId") # Get assessment ID from frontend

        if not assessment_data or not assessment_id:
            return jsonify({"error": "Assessment data or ID not provided"}), 400

        # The z_score_analysis now contains the explanation, not individual z_scores
        # So, no need to parse it as individual z_scores here for Gemini prompt
        # We can pass the raw assessment_data to Gemini service, it will use relevant fields
        
        # Call the combined Gemini insights function from gemini_service
        gemini_insights = get_gemini_insights(assessment_data)

        # Update the assessment in the database with the combined Gemini analysis
        user_id = session.get('user_id')
        if user_id:
            conn = get_db_connection()
            try:
                conn.execute(
                    'UPDATE assessments SET gemini_analysis = ? WHERE id = ? AND user_id = ?',
                    (json.dumps(gemini_insights), assessment_id, user_id)
                )
                conn.commit()
            except sqlite3.Error as e:
                print(f"Database error updating Gemini analysis: {e}")
            finally:
                conn.close()

        return jsonify(gemini_insights)

    except Exception as e:
        print(f"Error with Gemini API call in app.py: {e}")
        # Fallback to mock data if any error occurs during the process
        return jsonify({
            "swot": get_mock_swot_analysis(),
            "comparison": get_mock_company_comparison()
        }), 500

@app.route('/api/generate-pdf', methods=['POST'])
@login_required
def api_generate_pdf():
    try:
        data = request.json
        assessment_data = data.get("assessmentData")
        gemini_analysis = data.get("geminiAnalysis") # This will now contain both SWOT and comparison

        # Ensure gemini_analysis is not None and has the expected structure
        if not gemini_analysis or not gemini_analysis.get('swot') or not gemini_analysis.get('comparison'):
            # Fallback to mock if analysis is incomplete
            swot_data = get_mock_swot_analysis()
            comparison_data = get_mock_company_comparison()
        else:
            swot_data = gemini_analysis['swot']
            comparison_data = gemini_analysis['comparison']

        pdf_bytes = generate_risk_report_pdf(assessment_data, {"swot": swot_data, "comparison": comparison_data})
        
        response = app.make_response(pdf_bytes)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = 'attachment; filename="ai-risk-assessment-report.pdf"'
        return response

    except Exception as e:
        print(f"Error generating PDF: {e}")
        return jsonify({"error": "Failed to generate PDF"}), 500

@app.route('/api/compare-companies', methods=['POST'])
@login_required
def api_compare_companies():
    # This route is now redundant as comparison is part of api_gemini_analysis
    # It can be removed or repurposed if needed for other comparison types.
    return jsonify({"error": "This endpoint is deprecated. Use /api/gemini-analysis for combined insights."}), 400

# NEW: AI Advisor Chat API Endpoint
@app.route('/api/chat-advisor', methods=['POST'])
@login_required
def api_chat_advisor():
    try:
        data = request.json
        user_message = data.get('message')
        chat_history = data.get('history', []) # Get chat history from frontend
        user_context = data.get('user_context', {}) # Get user context from frontend

        if not user_message:
            return jsonify({"error": "No message provided"}), 400

        # Get response from the advisor service, passing user_context
        advisor_response = get_advisor_response(user_message, chat_history, user_context)

        return jsonify({"response": advisor_response})

    except Exception as e:
        print(f"Error in /api/chat-advisor: {e}")
        return jsonify({"error": "Internal server error during chat processing"}), 500

def get_risk_color_hex(score):
    if score <= 50: return '#22c55e' # green-500
    if score <= 70: return '#eab308' # yellow-500
    return '#ef4444' # red-500

if __name__ == '__main__':
    # Set a mock date for PDF generation
    os.environ['CURRENT_DATE'] = 'June 28, 2025'
    app.run(debug=True)
