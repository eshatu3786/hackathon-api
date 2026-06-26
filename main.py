import os
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# Health Endpoint
@app.get("/health")
def health_check():
    return {"status": "ok"}

# Request Schemas
class Transaction(BaseModel):
    transaction_id: str
    timestamp: str
    type: str
    amount: float
    counterparty: str
    status: str

class TicketRequest(BaseModel):
    ticket_id: str
    complaint: str
    language: Optional[str] = None
    channel: Optional[str] = None
    user_type: Optional[str] = None
    campaign_context: Optional[str] = None
    transaction_history: Optional[List[Transaction]] = []

# Investigator Endpoint
@app.post("/analyze-ticket")
def analyze_ticket(ticket: TicketRequest):
    history_text = ""
    if ticket.transaction_history:
        for tx in ticket.transaction_history:
            history_text += f"- ID: {tx.transaction_id}, Type: {tx.type}, Amount: {tx.amount} BDT, Status: {tx.status}, Counterparty: {tx.counterparty}\n"
    else:
        history_text = "No transaction history provided."

    system_instruction = f"""
    You are an expert Digital Finance Support Operations Investigator.
    Analyze the user complaint and their transaction history to determine the truth.

    CRITICAL RULES:
    1. NEVER ask for PIN, OTP, password, or card number in 'customer_reply'.
    2. NEVER explicitly confirm a refund or reversal. Use safe phrases like "any eligible amount will be returned through official channels".
    3. Determine 'evidence_verdict': 
       - 'consistent' if the transaction history matches the complaint.
       - 'inconsistent' if history contradicts the complaint.
       - 'insufficient_data' if it cannot be determined.

    You must output strictly raw JSON matching this structure exactly:
    {{
        "ticket_id": "{ticket.ticket_id}",
        "relevant_transaction_id": "TXN-ID or null",
        "evidence_verdict": "consistent OR inconsistent OR insufficient_data",
        "case_type": "wrong_transfer OR payment_failed OR refund_request OR duplicate_payment OR merchant_settlement_delay OR agent_cash_in_issue OR phishing_or_social_engineering OR other",
        "severity": "low OR medium OR high OR critical",
        "department": "customer_support OR dispute_resolution OR payments_ops OR merchant_operations OR agent_operations OR fraud_risk",
        "agent_summary": "1-2 sentence summary.",
        "recommended_next_action": "Operational next step.",
        "customer_reply": "Safe official reply.",
        "human_review_required": true,
        "confidence": 0.95,
        "reason_codes": ["code1"]
    }}
    """

    user_content = f"Complaint: {ticket.complaint}\n\nTransaction History:\n{history_text}"

    api_key = os.getenv("GEMINI_API_KEY", "YOUR_FALLBACK_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": system_instruction}, {"text": user_content}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=25)
        ai_response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        import json
        return json.loads(ai_response_text)
    except Exception as e:
        return {
            "ticket_id": ticket.ticket_id,
            "relevant_transaction_id": None,
            "evidence_verdict": "insufficient_data",
            "case_type": "other",
            "severity": "medium",
            "department": "customer_support",
            "agent_summary": "Error processing with AI system.",
            "recommended_next_action": "Manually inspect ticket details.",
            "customer_reply": "We are looking into your issue. Please keep your account secure.",
            "human_review_required": True,
            "confidence": 0.5,
            "reason_codes": ["api_error_fallback"]
        }