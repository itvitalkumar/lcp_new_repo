# ============================================================
# RAZORPAY PAYMENT INTEGRATION
# ============================================================
import razorpay
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models import TeacherGroup, CelebrationGroup, Payment
from app.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/payment", tags=["Payment"])

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


@router.post("/create-order")
def create_payment_order(
    request: dict,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Razorpay order for payment
    Called from frontend when user clicks "Pay"
    """
    amount = request.get("amount")  # in rupees
    group_id = request.get("group_id")
    group_type = request.get("group_type")  # "teacher" or "celebration"
    
    if not amount or not group_id:
        raise HTTPException(status_code=400, detail="Amount and group_id required")
    
    # ========== NEW VALIDATION (fix for negative/zero amounts) ==========
    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Amount must be a valid number")
    
    if amount_value <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")
    # =====================================================================
    
    # Verify group exists and belongs to user
    if group_type == "teacher":
        group = db.query(TeacherGroup).filter(
            TeacherGroup.group_id == group_id,
            TeacherGroup.created_by == current_user.id
        ).first()
    else:
        group = db.query(CelebrationGroup).filter(
            CelebrationGroup.group_id == group_id,
            CelebrationGroup.created_by == current_user.id
        ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Create Razorpay order
    order_data = {
        "amount": int(amount * 100),  # Convert to paise
        "currency": "INR",
        "receipt": f"{group_type}_{group_id}_{current_user.id}",
        "payment_capture": 1  # Auto-capture payment
    }
    
    try:
        order = razorpay_client.order.create(data=order_data)
        
        # Store order in database
        existing_payment = db.query(Payment).filter(
            Payment.group_type == group_type,
            Payment.teacher_group_id == group.id if group_type == "teacher" else None,
            Payment.celebration_group_id == group.id if group_type == "celebration" else None
        ).first()
        
        if existing_payment:
            existing_payment.razorpay_order_id = order["id"]
            existing_payment.amount = amount
            existing_payment.status = "pending"
        else:
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
        
        db.commit()
        
        return {
            "success": True,
            "order_id": order["id"],
            "amount": amount,
            "key": settings.RAZORPAY_KEY_ID,
            "group_id": group_id,
            "group_type": group_type
        }
        
    except Exception as e:
        print(f"Razorpay order creation error: {e}")
        raise HTTPException(status_code=500, detail=f"Payment initialization failed: {str(e)}")


@router.post("/verify-payment")
def verify_payment(
    payment_data: dict,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify payment signature and activate group
    Called from frontend after successful payment
    """
    try:
        # Verify signature
        razorpay_client.utility.verify_payment_signature(payment_data)
        
        # Payment is verified
        order_id = payment_data.get("order_id")
        payment_id = payment_data.get("payment_id")
        
        # Find payment record
        payment_record = db.query(Payment).filter(
            Payment.razorpay_order_id == order_id
        ).first()
        
        if not payment_record:
            raise HTTPException(status_code=404, detail="Payment record not found")
        
        # Update payment status
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
        
        return {
            "success": True,
            "message": "Payment verified and group activated successfully!",
            "group_id": group.group_id if group else None
        }
        
    except Exception as e:
        print(f"Payment verification error: {e}")
        raise HTTPException(status_code=400, detail="Payment verification failed")


@router.get("/order-status/{order_id}")
def get_order_status(
    order_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check status of a payment order"""
    payment_record = db.query(Payment).filter(
        Payment.razorpay_order_id == order_id
    ).first()
    
    if not payment_record:
        return {"status": "not_found"}
    
    return {
        "status": payment_record.status,
        "amount": payment_record.amount,
        "paid_at": payment_record.paid_at
    }