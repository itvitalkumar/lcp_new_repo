# ============================================================
# RAZORPAY WEBHOOK HANDLER
# Receives payment confirmation from Razorpay
# ============================================================
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import hmac
import hashlib

from app.database import get_db
from app.models import Payment, TeacherGroup, CelebrationGroup
from app.config import settings

router = APIRouter(prefix="/api/payment", tags=["Payment Webhook"])


@router.post("/webhook")
async def razorpay_webhook(request: Request):
    """
    Webhook endpoint that Razorpay calls when payment status changes
    IMPORTANT: Add this URL to Razorpay Dashboard → Webhooks
    URL: https://your-domain.com/api/payment/webhook
    """
    
    # Get the webhook payload
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    
    # Verify webhook signature (security)
    expected_signature = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if signature != expected_signature:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    import json
    payload = json.loads(body)
    
    event = payload.get("event")
    
    if event == "payment.captured":
        # Payment successful
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")
        payment_id = payment_entity.get("id")
        amount = payment_entity.get("amount", 0) / 100  # Convert paise to rupees
        
        db = next(get_db())
        
        # Find payment record
        payment_record = db.query(Payment).filter(
            Payment.razorpay_order_id == order_id
        ).first()
        
        if payment_record and payment_record.status != "success":
            payment_record.status = "success"
            payment_record.razorpay_payment_id = payment_id
            payment_record.paid_at = datetime.utcnow()
            
            # Activate the group
            if payment_record.group_type == "teacher":
                group = db.query(TeacherGroup).filter(
                    TeacherGroup.id == payment_record.teacher_group_id
                ).first()
                if group:
                    group.status = "active"
            else:
                group = db.query(CelebrationGroup).filter(
                    CelebrationGroup.id == payment_record.celebration_group_id
                ).first()
                if group:
                    group.status = "active"
            
            db.commit()
            print(f"✅ Webhook: Payment {payment_id} confirmed. Group activated.")
        
        db.close()
    
    return {"status": "ok"}