# IdeaGuard: Smart Risk Assessment Solution for First-Time Entrepreneurs

## 📋 Project Overview

IdeaGuard is a comprehensive risk assessment platform designed specifically for first-time entrepreneurs. It provides AI-powered insights, risk scoring, and connects entrepreneurs with potential investors and organizations.

### Key Features
- **Risk Assessment Engine**: Advanced algorithm for startup risk evaluation
- **AI-Powered Insights**: SWOT analysis and company comparisons
- **Organization Directory**: Connect with potential investors
- **PDF Report Generation**: Professional risk assessment reports
- **AI Advisor Chat**: Interactive guidance for entrepreneurs

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- SQLite3
- Google Gemini API (optional, for AI features)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd fixed9setup
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables** (optional)
   ```bash
   # For AI features, add your Gemini API key
   export GEMINI_API_KEY="your_api_key_here"
   ```

4. **Initialize the database**
   ```bash
   python app.py
   # The database will be created automatically on first run
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   - Open: `http://localhost:5000`
   - Register as a user or organization
   - Start your risk assessment journey

## 🏗️ Project Structure

```
fixed9setup/
├── app.py                      # Main Flask application
├── risk_calculator.py          # Risk assessment algorithms
├── gemini_service.py           # AI integration services
├── gemini_advisor_service.py   # AI advisor functionality
├── requirements.txt            # Python dependencies
├── templates/                  # HTML templates
│   ├── base.html              # Base template with navigation
│   ├── index.html             # Homepage
│   ├── login.html             # Login page
│   ├── register.html          # Registration page
│   ├── assessment.html        # Risk assessment form
│   ├── results.html           # Assessment results
│   ├── compare.html           # Company comparison
│   ├── advisor.html           # AI advisor chat
│   └── organizations_list.html # Organization directory
└── README.md                  # This documentation
```

## 🔧 Core Components

### 1. Risk Assessment Engine (`risk_calculator.py`)
- **Financial Risk Analysis**: Budget, revenue, expense evaluation
- **Team Risk Assessment**: Co-founder analysis, technical complexity
- **Timeline & Scope Risk**: Project duration and location impact
- **Smart Scoring**: Weighted algorithm with hard rules and scoring system

### 2. AI Integration (`gemini_service.py`)
- **SWOT Analysis**: AI-generated strengths, weaknesses, opportunities, threats
- **Company Comparison**: Success/failure case studies
- **Recommendations**: Actionable insights for risk mitigation

### 3. User Management
- **User Registration**: Individual entrepreneurs
- **Organization Registration**: Investors and support organizations
- **Session Management**: Secure login/logout system

## 🔄 Workflows

### 1. User Registration & Assessment Workflow
```
1. User registers → 2. Completes assessment → 3. Gets risk score → 4. Views results → 5. Generates PDF → 6. Contacts organizations
```

### 2. Organization Registration Workflow
```
1. Organization registers → 2. Provides contact details → 3. Gets listed in directory → 4. Receives funding requests from users
```

### 3. Risk Assessment Workflow
```
1. User inputs project details → 2. System calculates risk score → 3. AI generates insights → 4. User views comprehensive analysis → 5. Can export PDF report
```

### 4. Funding Request Workflow
```
1. User views organizations → 2. Clicks contact → 3. Gmail opens with pre-filled template → 4. User customizes with project details → 5. Sends funding request
```

## 📊 Risk Assessment Algorithm

### Scoring Factors
- **Financial Risk** (0-30 points): Profit margins, budget adequacy
- **Timeline Risk** (0-8 points): Project duration analysis
- **Location Risk** (0-4 points): Market scope evaluation
- **Team Risk** (0-8 points): Co-founder strength
- **Technical Risk** (0-15 points): Complexity assessment

### Risk Levels
- **Low Risk**: 0-44 points
- **Medium Risk**: 45-74 points
- **High Risk**: 75+ points

### Hard Rules (Immediate High Risk)
- No revenue + expenses > 80% of budget
- Expenses > 3x revenue
- Single founder + high technical complexity (8+)
- Budget < 50% of expenses

## 🗄️ Database Schema

### Users Table
- User registration and authentication
- Personal and professional details

### Assessments Table
- Risk assessment results
- Project details and scores
- AI-generated insights

### Organizations Table
- Organization contact information
- Available for funding requests

## 🔐 Security Features

- **Password Hashing**: Secure password storage
- **Session Management**: Protected routes
- **Input Validation**: Form data sanitization
- **SQL Injection Protection**: Parameterized queries

## 🎨 UI/UX Features

- **Responsive Design**: Works on all devices
- **Modern Interface**: Clean, professional design
- **Interactive Elements**: Dynamic forms and charts
- **Accessibility**: Screen reader friendly

## 📈 Future Enhancements

- **Advanced Analytics**: More detailed risk metrics
- **Investor Dashboard**: Organization management tools
- **Real-time Chat**: Direct messaging between users and organizations
- **Mobile App**: Native mobile application
- **API Integration**: Third-party service connections

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is proprietary software. All rights reserved.

## 📞 Support

For technical support or questions:
- Check the documentation
- Review the code comments
- Contact the development team

---

**IdeaGuard** - Empowering first-time entrepreneurs with smart risk assessment and AI-powered insights. 