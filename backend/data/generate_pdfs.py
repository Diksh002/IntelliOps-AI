from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

def create_pdf(filename, content):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    c.drawString(100, 750, f"CONFIDENTIAL REPORT: {filename}")
    c.drawString(100, 730, "--------------------------------------------------")
    
    y = 700
    for line in content:
        c.drawString(100, y, line)
        y -= 20
        
    c.save()
    print(f"Created {filename}")

def generate_reports():
    os.makedirs("reports", exist_ok=True)
    
    # Report 1: Q3 APAC Analysis
    create_pdf("reports/Q3_APAC_Analysis.pdf", [
        "Subject: Q3 Revenue Drop in APAC Region",
        "Date: October 15, 2024",
        "Author: Senior Analyst Team",
        "",
        "Executive Summary:",
        "Despite the successful launch of 'DataScout Pro', Q3 revenue in APAC dropped by 12%.",
        "Primary causes identified:",
        "1. Supply Chain Disruptions: The new hardware components for the on-premise",
        "   deployments were delayed by 6 weeks due to port strikes in Singapore.",
        "2. Currency Fluctuation: The local currency devaluation impacted purchasing power.",
        "3. Competitor Action: 'FinTech Corp' aggressively discounted their legacy product.",
        "",
        "Recommendations:",
        "- Accelerate the cloud-only deployment option to bypass hardware delays.",
        "- Adjust regional pricing to account for FX rates."
    ])
    
    # Report 2: Project X-Ray Overview
    create_pdf("reports/Project_X_Ray_Confidential.pdf", [
        "Project Code: X-RAY",
        "Status: Active / High Priority",
        "Budget: $5M",
        "",
        "Description:",
        "Project X-Ray is the internal initiative to acquire 'AI-Analytics Ltd'.",
        "This acquisition will bolster our NLP capabilities for the DataScout platform.",
        "Due diligence is currently 60% complete.",
        "",
        "Risks:",
        "- Regulatory approval in the EU.",
        "- Key talent retention post-acquisition."
    ])

if __name__ == "__main__":
    generate_reports()
