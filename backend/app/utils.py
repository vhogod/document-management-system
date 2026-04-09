import openai
import os
from dotenv import load_dotenv
import pdfplumber
import json
from datetime import datetime

load_dotenv()

# Initialize OpenAI client (new correct way)
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def extract_invoice_data(file_path: str):
    """Extract data from invoice PDF using AI"""
    try:
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        if not text.strip():
            return {"error": "Could not extract text from PDF"}

        prompt = f"""
        You are an expert accountant. Extract key information from this invoice or credit note.

        Return ONLY a valid JSON object with these exact keys:
        - vendor: string (company name)
        - invoice_number: string
        - date: string in YYYY-MM-DD format
        - amount: float (total amount including VAT)
        - vat: float (VAT amount, use 0 if not found)

        Document text:
        {text[:6000]}
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=300
        )

        result = response.choices[0].message.content.strip()

        # Clean JSON if it has markdown
        if result.startswith("```json"):
            result = result[7:-3].strip()
        elif result.startswith("```"):
            result = result[3:-3].strip()

        extracted = json.loads(result)
        return extracted

    except Exception as e:
        print("AI Extraction Error:", str(e))
        # Fallback
        return {
            "vendor": "Unknown",
            "invoice_number": f"INV-{datetime.now().strftime('%Y%m%d%H%M')}",
            "date": datetime.now().strftime('%Y-%m-%d'),
            "amount": 0.0,
            "vat": 0.0
        }

async def generate_spending_insights(report_data: dict):
    """Generate real AI insights"""
    try:
        prompt = f"""
        You are a senior financial analyst for a South African company.

        Analyze this spending data and give clear, actionable insights:

        Total Spend: R{report_data.get('total_spend', 0):,}
        Total Documents: {report_data.get('total_documents', 0)}
        Pending Approvals: {report_data.get('pending_count', 0)}
        Top Vendors: {report_data.get('top_vendors', [])}

        Provide insights in bullet points covering:
        - Spending trends
        - Risks or anomalies
        - Cost saving opportunities
        - Recommendations

        Use professional tone and South African Rand (R).
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert financial analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=600
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("AI Insights Error:", str(e))
        return "Unable to generate insights. Please check your OpenAI API key and internet connection."