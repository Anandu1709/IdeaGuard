import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

genai_model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        genai_model = genai.GenerativeModel('gemini-2.5-flash') # Using gemini-2.5-flash as per your screenshot
    except Exception as e:
        print(f"Error configuring Gemini API with provided key: {e}. AI insights will use mock data.")
else:
    print("GEMINI_API_KEY not found in .env. AI insights will use mock data.")

def get_mock_swot_analysis():
    return {
        "strengths": [
            "Clear vision and mission statement.",
            "Dedicated and skilled core team.",
            "Identified market need or gap.",
            "Agile and adaptable to change."
        ],
        "weaknesses": [
            "Limited initial funding or capital.",
            "Small team size may lead to resource constraints.",
            "Lack of established brand recognition.",
            "Dependency on a few key individuals."
        ],
        "opportunities": [
            "Growing market demand for innovative solutions.",
            "Potential for strategic partnerships.",
            "Emerging technologies can enhance product/service.",
            "Untapped niche markets."
        ],
        "threats": [
            "Intense competition from established players.",
            "Rapid technological changes requiring constant adaptation.",
            "Economic downturns affecting consumer spending.",
            "Regulatory changes impacting operations."
        ],
        "recommendations": [
            "Focus on building a strong Minimum Viable Product (MVP) to validate core assumptions quickly.",
            "Actively seek early customer feedback to iterate and improve.",
            "Explore diverse funding options, including grants, angel investors, or crowdfunding.",
            "Develop a robust marketing strategy to build brand awareness and reach target customers.",
            "Invest in continuous learning and skill development for the team.",
            "Monitor market trends and competitor activities closely to adapt your strategy."
        ],
    }

def get_mock_company_comparison():
    return {
        "successful_company": {
            "name": "Netflix",
            "industry": "Entertainment/Streaming",
            "insights": [
                "Pioneered the subscription model for content delivery.",
                "Continuously innovated, moving from DVDs to streaming and original content.",
                "Strong focus on data-driven content recommendations and user experience."
            ]
        },
        "failed_company": {
            "name": "Blockbuster",
            "industry": "Video Rental",
            "insights": [
                "Failed to adapt to changing consumer preferences and digital disruption.",
                "Relied too heavily on physical stores and late fees.",
                "Underestimated the threat from online streaming services."
            ]
        },
        "lessons_learned": [
            "Embrace innovation and be willing to disrupt your own business model.",
            "Prioritize customer convenience and evolving preferences.",
            "Don't underestimate emerging competitors, even if they seem small initially.",
            "Diversify revenue streams and adapt to new technologies.",
            "A strong digital strategy is crucial in today's market."
        ]
    }

def get_gemini_insights(assessment_data):
    """
    Generates combined SWOT analysis and company comparison insights using Gemini API.
    Returns mock data if API is not configured or an error occurs during the API call.
    """
    if not genai_model:
        return {
            "swot": get_mock_swot_analysis(),
            "comparison": get_mock_company_comparison(),
            "mock_message": "AI assistance is not available at the moment, but here are a few general tips:"
        }

    # Prepare prompt for SWOT analysis
    swot_prompt = f"""
    Analyze the following business project assessment data and provide a comprehensive SWOT analysis and recommendations.
    Focus on actionable insights based on the scores and project parameters. Higher scores indicate higher risk/deviation from industry norms.
    Provide concise bullet points, with a maximum of 4-5 points per section (Strengths, Weaknesses, Opportunities, Threats, Recommendations).

    Project Details:
    - Project Name: {assessment_data.get("project_name", "N/A")}
    - Industry: {assessment_data.get("industry", "N/A")}
    - Description: {assessment_data.get("description", "N/A")}
    - Budget: ₹{assessment_data.get("budget", 0):,.0f}
    - Timeline: {assessment_data.get("timeline", "N/A")}
    - Location Scope: {assessment_data.get("location", "N/A")}
    - Team Size: {assessment_data.get("number_of_cofounders", 1)} co-founders
    - Technical Complexity: {assessment_data.get("technical_complexity", 5)}/10
    - Expected Revenue: ₹{assessment_data.get("total_revenue", 0):,.0f}
    - Expected Expenses: ₹{assessment_data.get("total_expense", 0):,.0f}

    Z-Score Analysis (converted to 0-100 scale where higher = more risk):
    - Budget Score: {assessment_data["z_score_analysis"].get("budget", 0) * 20 + 50:.0f}/100
    - Timeline Score: {assessment_data["z_score_analysis"].get("timeline", 0) * 20 + 50:.0f}/100
    - Location Score: {assessment_data["z_score_analysis"].get("location", 0) * 20 + 50:.0f}/100
    - Team Score: {assessment_data["z_score_analysis"].get("cofounders", 0) * 20 + 50:.0f}/100
    - Technical Complexity Score: {assessment_data["z_score_analysis"].get("technical_complexity", 0) * 20 + 50:.0f}/100
    - Combined Score: {assessment_data["z_score_analysis"].get("combined_z_score", 0) * 20 + 50:.0f}/100

    Provide the SWOT analysis and recommendations in the following JSON format:
    {{
        "strengths": ["strength 1", "strength 2", "strength 3", "strength 4"],
        "weaknesses": ["weakness 1", "weakness 2", "weakness 3", "weakness 4"],
        "opportunities": ["opportunity 1", "opportunity 2", "opportunity 3", "opportunity 4"],
        "threats": ["threat 1", "threat 2", "threat 3", "threat 4"],
        "recommendations": ["recommendation 1", "recommendation 2", "recommendation 3", "recommendation 4", "recommendation 5", "recommendation 6"]
    }}
    """

    # Prepare prompt for company comparison
    comparison_prompt = f"""
    Based on the following project details, identify one highly successful company and one notable failed company within the {assessment_data.get("industry", "general")} industry or a closely related field.
    For each company, provide 3 concise bullet points (max) key insights into why they succeeded or failed.
    Finally, provide 3 concise bullet points (max) actionable lessons that the user can infer and apply to their own project: "{assessment_data.get("project_name", "N/A")}" (Description: {assessment_data.get("description", "N/A")}).

    Provide the output in the following JSON format:
    {{
        "successful_company": {{
            "name": "Successful Company Name",
            "industry": "Industry",
            "insights": ["insight 1", "insight 2", "insight 3"]
        }},
        "failed_company": {{
            "name": "Failed Company Name",
            "industry": "Industry",
            "insights": ["insight 1", "insight 2", "insight 3"]
        }},
        "lessons_learned": ["lesson 1", "lesson 2", "lesson 3"]
    }}
    """

    try:
        swot_response = genai_model.generate_content(swot_prompt)
        swot_text = swot_response.text
        swot_analysis = {}
        try:
            start_idx = swot_text.find("{")
            end_idx = swot_text.rfind("}") + 1
            if start_idx != -1 and end_idx != -1:
                json_str = swot_text[start_idx:end_idx]
                swot_analysis = json.loads(json_str)
            else:
                print("Could not parse SWOT JSON from Gemini response, using mock.")
                swot_analysis = get_mock_swot_analysis()
        except json.JSONDecodeError as parse_error:
            print(f"Error parsing SWOT response: {parse_error}, using mock.")
            swot_analysis = get_mock_swot_analysis()

        comparison_response = genai_model.generate_content(comparison_prompt)
        comparison_text = comparison_response.text
        company_comparison = {}
        try:
            start_idx = comparison_text.find("{")
            end_idx = comparison_text.rfind("}") + 1
            if start_idx != -1 and end_idx != -1:
                json_str = comparison_text[start_idx:end_idx]
                company_comparison = json.loads(json_str)
            else:
                print("Could not parse Comparison JSON from Gemini response, using mock.")
                company_comparison = get_mock_company_comparison()
        except json.JSONDecodeError as parse_error:
            print(f"Error parsing Comparison response: {parse_error}, using mock.")
            company_comparison = get_mock_company_comparison()

        return {
            "swot": swot_analysis,
            "comparison": company_comparison
        }

    except Exception as e:
        print(f"Error during Gemini API call in get_gemini_insights: {e}. Returning mock insights.")
        return {
            "swot": get_mock_swot_analysis(),
            "comparison": get_mock_company_comparison(),
            "mock_message": "AI assistance is not available at the moment, but here are a few general tips:"
        }
