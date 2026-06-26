# ============================================================
# RAZORPAY WEBHOOK HANDLER
# Receives payment confirmation from Razorpay
# Phase 1 (June 18, 2026): Initial webhook handler.
# Phase 2 (June 25, 2026): Added Razorpay webhook secret from Key Vault.
# Phase 3 (June 26, 2026): ENHANCED - Added retry logic for database operations.
#                         Better error handling for Azure SQL.
#                         Added logging for debugging.
#                         Added transaction management.
# ============================================================
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, TimeoutError as SQLTimeoutError
from datetime import datetime
import hmac
import hashlib
import json
import logging

from app.database import get_db, retry_on_db_error
from app.models import Payment, TeacherGroup, CelebrationGroup
from app.config import settings

# ============================================================
# LOGGING SETUP
# ============================================================
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payment", tags=["Payment Webhook"])


# ============================================================
# ✅ ADDED: HELPER FOR DATABASE ERROR HANDLING
# ============================================================
def handle_db_error(e: Exception, operation: str) -> HTTPException:
    """
    Convert database errors to user-friendly HTTP exceptions.
    """
    logger.error(f"❌ Database error during {operation}: {str(e)}")
    
    if "timeout" in str(e).lower() or "connection" in str(e).lower():
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again in a moment."
        )
    else:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error. Please try again later."
        )


# ============================================================
# ✅ ADDED: HELPER TO ACTIVATE GROUP
# ============================================================
def activate_group(db: Session, payment_record: Payment):
    """
    Activate the group associated with a payment record.
    Returns the activated group.
    """
    if payment_record.group_type == "teacher":
        group = retry_on_db_error(
            lambda: db.query(TeacherGroup).filter(
                TeacherGroup.id == payment_record.teacher_group_id
            ).first()
        )
        if group:
            group.status = "active"
            logger.info(f"✅ Teacher group activated: {group.group_id}")
            return group
        else:
            logger.warning(f"⚠️ Teacher group not found for payment: {payment_record.id}")
    else:
        group = retry_on_db_error(
            lambda: db.query(CelebrationGroup).filter(
                CelebrationGroup.id == payment_record.celebration_group_id
            ).first()
        )
        if group:
            group.status = "active"
            logger.info(f"✅ Celebration group activated: {group.group_id}")
            return group
        else:
            logger.warning(f"⚠️ Celebration group not found for payment: {payment_record.id}")
    
    return None


@router.post("/webhook")
async def razorpay_webhook(request: Request):
    """
    Webhook endpoint that Razorpay calls when payment status changes
    IMPORTANT: Add this URL to Razorpay Dashboard → Webhooks
    URL: https://your-domain.com/api/payment/webhook
    """
    
    logger.info("📨 Webhook received from Razorpay")
    
    try:
        # Get the webhook payload
        body = await request.body()
        signature = request.headers.get("X-Razorpay-Signature")
        
        # ✅ Validate webhook signature
        if not signature:
            logger.error("❌ Missing webhook signature")
            raise HTTPException(status_code=401, detail="Missing webhook signature")
        
        # Verify webhook signature (security)
        expected_signature = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        if signature != expected_signature:
            logger.error("❌ Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Parse payload
        payload = json.loads(body)
        event = payload.get("event")
        
        logger.info(f"📨 Webhook event: {event}")
        
        if event == "payment.captured":
            # Payment successful
            payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
            order_id = payment_entity.get("order_id")
            payment_id = payment_entity.get("id")
            amount = payment_entity.get("amount", 0) / 100  # Convert paise to rupees
            
            logger.info(f"💰 Payment captured: order_id={order_id}, payment_id={payment_id}, amount={amount}")
            
            if not order_id:
                logger.error("❌ Missing order_id in webhook payload")
                return {"status": "ignored", "reason": "missing_order_id"}
            
            # ✅ Get database session with retry
            db = next(get_db())
            
            try:
                # ✅ Find payment record with retry
                payment_record = retry_on_db_error(
                    lambda: db.query(Payment).filter(
                        Payment.razorpay_order_id == order_id
                    ).first()
                )
                
                if not payment_record:
                    logger.warning(f"⚠️ Payment record not found for order: {order_id}")
                    db.close()
                    return {"status": "ignored", "reason": "payment_record_not_found"}
                
                logger.info(f"✅ Payment record found: id={payment_record.id}, status={payment_record.status}")
                
                # ✅ Check if already processed
                if payment_record.status == "success":
                    logger.info(f"ℹ️ Payment {payment_id} already processed")
                    db.close()
                    return {"status": "ok", "message": "already_processed"}
                
                # ✅ Update payment status
                payment_record.status = "success"
                payment_record.razorpay_payment_id = payment_id
                payment_record.paid_at = datetime.utcnow()
                
                # ✅ Activate the group
                group = activate_group(db, payment_record)
                
                if group:
                    logger.info(f"✅ Group activated: {group.group_id}")
                else:
                    logger.warning(f"⚠️ Group not activated for payment: {payment_record.id}")
                
                # ✅ Commit transaction
                db.commit()
                logger.info(f"✅ Webhook: Payment {payment_id} confirmed. Group activated.")
                
                db.close()
                return {"status": "ok"}
                
            except OperationalError as e:
                db.rollback()
                logger.error(f"❌ Database error processing webhook: {e}")
                db.close()
                raise HTTPException(
                    status_code=503,
                    detail="Database temporarily unavailable. Please try again."
                )
            except SQLTimeoutError as e:
                db.rollback()
                logger.error(f"❌ Database timeout processing webhook: {e}")
                db.close()
                raise HTTPException(
                    status_code=503,
                    detail="Database connection timeout. Please try again."
                )
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Unexpected error processing webhook: {e}")
                db.close()
                raise HTTPException(
                    status_code=500,
                    detail=f"Webhook processing failed: {str(e)}"
                )
        
        elif event == "payment.failed":
            logger.warning(f"⚠️ Payment failed: {payload.get('payload', {}).get('payment', {}).get('entity', {})}")
            # Optionally handle failed payments
            return {"status": "ok"}
        
        else:
            logger.info(f"ℹ️ Unhandled webhook event: {event}")
            return {"status": "ok", "event": event}
            
    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"❌ Unexpected webhook error: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")