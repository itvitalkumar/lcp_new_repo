# ============================================================
# RAZORPAY PAYMENT INTEGRATION
# Phase 1 (June 18, 2026): Initial payment integration.
# Phase 2 (June 25, 2026): Added Razorpay keys from Key Vault.
# Phase 3 (June 26, 2026): ENHANCED - Added retry logic for database operations.
#                         Better error handling for Azure SQL.
#                         Added logging instead of print statements.
#                         Added transaction management.
# ============================================================
import razorpay
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, TimeoutError as SQLTimeoutError
from datetime import datetime
import logging

from app.database import get_db, retry_database_operation
from app.models import TeacherGroup, CelebrationGroup, Payment
from app.auth import get_current_user
from app.config import settings

# ============================================================
# LOGGING SETUP
# ============================================================
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payment", tags=["Payment"])

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# ============================================================
# 🔍 DEBUG: Log when the router is loaded
# ============================================================
logger.info("🚀 Payment router loaded successfully")
logger.info(f"🔑 RAZORPAY_KEY_ID: {settings.RAZORPAY_KEY_ID[:10]}...")


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
# CREATE ORDER
# ============================================================
@router.post("/create-order")
def create_payment_order(
    request: dict,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info("💰 CREATE ORDER STARTED")
    logger.info(f"📥 Request received: amount={request.get('amount')}, group_id={request.get('group_id')}, group_type={request.get('group_type')}")
    
    amount = request.get("amount")
    group_id = request.get("group_id")
    group_type = request.get("group_type")
    
    if not amount or not group_id:
        logger.error("❌ Missing amount or group_id")
        raise HTTPException(status_code=400, detail="Amount and group_id required")
    
    try:
        amount_value = float(amount)
        logger.info(f"✅ Amount validated: ₹{amount_value}")
    except (TypeError, ValueError):
        logger.error("❌ Invalid amount format")
        raise HTTPException(status_code=400, detail="Amount must be a valid number")
    
    if amount_value <= 0:
        logger.error("❌ Amount must be greater than zero")
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")
    
    logger.info(f"🔍 Looking for group: group_type={group_type}, group_id={group_id}")
    
    try:
        # Verify group with retry
        if group_type == "teacher":
            group = retry_database_operation(
                lambda: db.query(TeacherGroup).filter(
                    TeacherGroup.group_id == group_id,
                    TeacherGroup.created_by == current_user.id
                ).first()
            )
        else:
            group = retry_database_operation(
                lambda: db.query(CelebrationGroup).filter(
                    CelebrationGroup.group_id == group_id,
                    CelebrationGroup.created_by == current_user.id
                ).first()
            )
        
        if not group:
            logger.error("❌ Group not found")
            raise HTTPException(status_code=404, detail="Group not found")
        
        logger.info(f"✅ Group found: ID={group.id}, Name={group.teacher_name if group_type=='teacher' else group.title}")
        
        # Create Razorpay order
        order_data = {
            "amount": int(amount * 100),
            "currency": "INR",
            "receipt": f"{group_type}_{group_id}_{current_user.id}",
            "payment_capture": 1
        }
        logger.info(f"📤 Sending order to Razorpay: {order_data}")
        
        try:
            order = razorpay_client.order.create(data=order_data)
            logger.info(f"✅ Razorpay order created: order_id={order['id']}")
        except Exception as e:
            logger.error(f"❌ Razorpay order creation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Razorpay error: {str(e)}")
        
        # Store order in database
        logger.info("💾 Saving payment record to database...")
        
        # Check for existing payment with retry
        existing_payment = retry_database_operation(
            lambda: db.query(Payment).filter(
                Payment.group_type == group_type,
                Payment.teacher_group_id == group.id if group_type == "teacher" else None,
                Payment.celebration_group_id == group.id if group_type == "celebration" else None
            ).first()
        )
        
        if existing_payment:
            logger.info(f"🔄 Existing payment found: ID={existing_payment.id}, updating...")
            existing_payment.razorpay_order_id = order["id"]
            existing_payment.amount = amount
            existing_payment.status = "pending"
        else:
            logger.info("🆕 No existing payment found. Creating new...")
            new_payment = Payment(
                group_type=group_type,
                teacher_group_id=group.id if group_type == "teacher" else None,
                celebration_group_id=group.id if group_type == "celebration" else None,
                user_id=current_user.id,
                amount=amount,
                status="pending",
                razorpay_order_id=order["id"]
            )
            db.add(new_payment)
        
        # Commit transaction
        db.commit()
        logger.info("✅ Database commit successful")
        
        if not existing_payment:
            db.refresh(new_payment)
            logger.info(f"💾 PAYMENT SAVED: ID={new_payment.id}, OrderID={new_payment.razorpay_order_id}")
        else:
            db.refresh(existing_payment)
            logger.info(f"💾 PAYMENT UPDATED: ID={existing_payment.id}, OrderID={existing_payment.razorpay_order_id}")
        
        # Get total payments count
        total_payments = retry_database_operation(lambda: db.query(Payment).count())
        logger.info(f"💾 Total payments in DB: {total_payments}")
        
        logger.info(f"📤 Returning response to frontend: order_id={order['id']}")
        
        return {
            "success": True,
            "order_id": order["id"],
            "amount": amount,
            "key": settings.RAZORPAY_KEY_ID,
            "group_id": group_id,
            "group_type": group_type
        }
        
    except HTTPException:
        raise
    except OperationalError as e:
        db.rollback()
        raise handle_db_error(e, "creating payment order")
    except SQLTimeoutError as e:
        db.rollback()
        raise handle_db_error(e, "creating payment order")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Unexpected error creating payment order: {e}")
        raise HTTPException(status_code=500, detail=f"Payment initialization failed: {str(e)}")


# ============================================================
# VERIFY PAYMENT
# ============================================================
@router.post("/verify-payment")
def verify_payment(
    payment_data: dict,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info("🔐 VERIFY PAYMENT STARTED")
    logger.info(f"📥 Verification request: {payment_data}")
    
    try:
        logger.info("🔑 Verifying Razorpay signature...")
        razorpay_client.utility.verify_payment_signature(payment_data)
        logger.info("✅ Signature verified successfully")
        
        # Use razorpay_order_id (not order_id)
        order_id = payment_data.get("razorpay_order_id")
        payment_id = payment_data.get("razorpay_payment_id")
        logger.info(f"🔍 Looking for payment record: order_id={order_id}")
        
        # Find payment record with retry
        payment_record = retry_database_operation(
            lambda: db.query(Payment).filter(
                Payment.razorpay_order_id == order_id
            ).first()
        )
        
        if not payment_record:
            logger.error(f"❌ Payment record NOT FOUND for order_id={order_id}")
            # Log all payments for debugging
            all_payments = retry_database_operation(lambda: db.query(Payment).all())
            logger.info(f"📋 All payments in DB: {len(all_payments)}")
            for p in all_payments:
                logger.info(f"   - ID={p.id}, OrderID={p.razorpay_order_id}, Status={p.status}")
            raise HTTPException(status_code=404, detail="Payment record not found")
        
        logger.info(f"✅ Payment record found: ID={payment_record.id}, Status={payment_record.status}")
        
        # Check if already processed
        if payment_record.status == "success":
            logger.info(f"ℹ️ Payment {payment_id} already verified")
            return {
                "success": True,
                "message": "Payment already verified",
                "group_id": payment_record.teacher_group_id or payment_record.celebration_group_id
            }
        
        # Update payment status
        payment_record.status = "success"
        payment_record.razorpay_payment_id = payment_id
        payment_record.paid_at = datetime.utcnow()
        logger.info(f"🔄 Updated payment status to 'success'")
        
        # Activate group
        group = None
        if payment_record.group_type == "teacher":
            group = retry_database_operation(
                lambda: db.query(TeacherGroup).filter(
                    TeacherGroup.id == payment_record.teacher_group_id
                ).first()
            )
            if group:
                group.status = "active"
                logger.info(f"✅ Teacher group activated: ID={group.id}, Name={group.teacher_name}")
            else:
                logger.error(f"❌ Teacher group not found: ID={payment_record.teacher_group_id}")
        else:
            group = retry_database_operation(
                lambda: db.query(CelebrationGroup).filter(
                    CelebrationGroup.id == payment_record.celebration_group_id
                ).first()
            )
            if group:
                group.status = "active"
                logger.info(f"✅ Celebration group activated: ID={group.id}, Title={group.title}")
            else:
                logger.error(f"❌ Celebration group not found: ID={payment_record.celebration_group_id}")
        
        db.commit()
        logger.info("✅ Database commit successful")
        
        return {
            "success": True,
            "message": "Payment verified and group activated successfully!",
            "group_id": group.group_id if group else None
        }
        
    except HTTPException:
        raise
    except OperationalError as e:
        db.rollback()
        raise handle_db_error(e, "verifying payment")
    except SQLTimeoutError as e:
        db.rollback()
        raise handle_db_error(e, "verifying payment")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Payment verification error: {e}")
        raise HTTPException(status_code=400, detail=f"Payment verification failed: {str(e)}")


# ============================================================
# ORDER STATUS
# ============================================================
@router.get("/order-status/{order_id}")
def get_order_status(
    order_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"🔍 Checking order status: {order_id}")
    
    try:
        payment_record = retry_database_operation(
            lambda: db.query(Payment).filter(
                Payment.razorpay_order_id == order_id
            ).first()
        )
        
        if not payment_record:
            return {"status": "not_found"}
        
        return {
            "status": payment_record.status,
            "amount": payment_record.amount,
            "paid_at": payment_record.paid_at
        }
        
    except OperationalError as e:
        raise handle_db_error(e, "checking order status")
    except SQLTimeoutError as e:
        raise handle_db_error(e, "checking order status")
    except Exception as e:
        logger.error(f"❌ Unexpected error checking order status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )