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

# ============================================================
# 🔍 DEBUG: Log when the router is loaded
# ============================================================
print("🚀 Payment router loaded successfully")
print(f"🔑 RAZORPAY_KEY_ID: {settings.RAZORPAY_KEY_ID[:10]}...")
print(f"📂 DATABASE_URL: {settings.DATABASE_URL}")

# ============================================================
# CREATE ORDER
# ============================================================
@router.post("/create-order")
def create_payment_order(
    request: dict,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    print("\n" + "="*60)
    print("💰 CREATE ORDER STARTED")
    print("="*60)
    
    # DEBUG LINE 1
    print(f"📥 Request received: amount={request.get('amount')}, group_id={request.get('group_id')}, group_type={request.get('group_type')}")
    
    amount = request.get("amount")
    group_id = request.get("group_id")
    group_type = request.get("group_type")
    
    if not amount or not group_id:
        print("❌ Missing amount or group_id")
        raise HTTPException(status_code=400, detail="Amount and group_id required")
    
    try:
        amount_value = float(amount)
        print(f"✅ Amount validated: ₹{amount_value}")
    except (TypeError, ValueError):
        print("❌ Invalid amount format")
        raise HTTPException(status_code=400, detail="Amount must be a valid number")
    
    if amount_value <= 0:
        print("❌ Amount must be greater than zero")
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")
    
    # DEBUG LINE 2
    print(f"🔍 Looking for group: group_type={group_type}, group_id={group_id}")
    
    # Verify group
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
        print("❌ Group not found")
        raise HTTPException(status_code=404, detail="Group not found")
    
    # DEBUG LINE 3
    print(f"✅ Group found: ID={group.id}, Name={group.teacher_name if group_type=='teacher' else group.title}")
    
    # Create Razorpay order
    order_data = {
        "amount": int(amount * 100),
        "currency": "INR",
        "receipt": f"{group_type}_{group_id}_{current_user.id}",
        "payment_capture": 1
    }
    print(f"📤 Sending order to Razorpay: {order_data}")
    
    try:
        order = razorpay_client.order.create(data=order_data)
        
        # DEBUG LINE 4
        print(f"✅ Razorpay order created: order_id={order['id']}")
        
        # Store order in database
        print("💾 Saving payment record to database...")
        
        # DEBUG LINE 5
        print(f"🔍 Checking for existing payment: group_type={group_type}, group_id={group.id}")
        
        existing_payment = db.query(Payment).filter(
            Payment.group_type == group_type,
            Payment.teacher_group_id == group.id if group_type == "teacher" else None,
            Payment.celebration_group_id == group.id if group_type == "celebration" else None
        ).first()
        
        if existing_payment:
            # DEBUG LINE 6
            print(f"🔄 Existing payment found: ID={existing_payment.id}, updating...")
            existing_payment.razorpay_order_id = order["id"]
            existing_payment.amount = amount
            existing_payment.status = "pending"
        else:
            # DEBUG LINE 7
            print("🆕 No existing payment found. Creating new...")
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
            print(f"🆕 Payment object created (before commit): ID={new_payment.id}")
        
        # DEBUG LINE 8
        print("🔄 Committing to database...")
        db.commit()
        print("✅ Database commit successful")
        
        # DEBUG LINE 9
        if not existing_payment:
            db.refresh(new_payment)
            print(f"💾 PAYMENT SAVED: ID={new_payment.id}, OrderID={new_payment.razorpay_order_id}")
        else:
            db.refresh(existing_payment)
            print(f"💾 PAYMENT UPDATED: ID={existing_payment.id}, OrderID={existing_payment.razorpay_order_id}")
        
        # DEBUG LINE 10
        total_payments = db.query(Payment).count()
        print(f"💾 Total payments in DB: {total_payments}")
        
        # DEBUG LINE 11
        print(f"📤 Returning response to frontend: order_id={order['id']}")
        print("="*60)
        
        return {
            "success": True,
            "order_id": order["id"],
            "amount": amount,
            "key": settings.RAZORPAY_KEY_ID,
            "group_id": group_id,
            "group_type": group_type
        }
        
    except Exception as e:
        # DEBUG LINE 12
        print(f"❌ RAZORPAY ERROR: {e}")
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
    print("\n" + "="*60)
    print("🔐 VERIFY PAYMENT STARTED")
    print("="*60)
    
    # DEBUG LINE 1
    print(f"📥 Verification request: {payment_data}")
    
    try:
        print("🔑 Verifying Razorpay signature...")
        razorpay_client.utility.verify_payment_signature(payment_data)
        print("✅ Signature verified successfully")
        
        order_id = payment_data.get("order_id")
        payment_id = payment_data.get("payment_id")
        print(f"🔍 Looking for payment record: order_id={order_id}")
        
        # DEBUG LINE 2
        payment_record = db.query(Payment).filter(
            Payment.razorpay_order_id == order_id
        ).first()
        
        if not payment_record:
            print(f"❌ Payment record NOT FOUND for order_id={order_id}")
            # DEBUG LINE 3 - Check all payments
            all_payments = db.query(Payment).all()
            print(f"📋 All payments in DB: {len(all_payments)}")
            for p in all_payments:
                print(f"   - ID={p.id}, OrderID={p.razorpay_order_id}, Status={p.status}")
            raise HTTPException(status_code=404, detail="Payment record not found")
        
        # DEBUG LINE 4
        print(f"✅ Payment record found: ID={payment_record.id}, Status={payment_record.status}")
        
        # Update payment status
        payment_record.status = "success"
        payment_record.razorpay_payment_id = payment_id
        payment_record.paid_at = datetime.utcnow()
        print(f"🔄 Updated payment status to 'success'")
        
        # Activate group
        if payment_record.group_type == "teacher":
            group = db.query(TeacherGroup).filter(
                TeacherGroup.id == payment_record.teacher_group_id
            ).first()
            if group:
                group.status = "active"
                print(f"✅ Teacher group activated: ID={group.id}, Name={group.teacher_name}")
            else:
                print(f"❌ Teacher group not found: ID={payment_record.teacher_group_id}")
        else:
            group = db.query(CelebrationGroup).filter(
                CelebrationGroup.id == payment_record.celebration_group_id
            ).first()
            if group:
                group.status = "active"
                print(f"✅ Celebration group activated: ID={group.id}, Title={group.title}")
            else:
                print(f"❌ Celebration group not found: ID={payment_record.celebration_group_id}")
        
        db.commit()
        print("✅ Database commit successful")
        print("="*60)
        
        return {
            "success": True,
            "message": "Payment verified and group activated successfully!",
            "group_id": group.group_id if group else None
        }
        
    except Exception as e:
        print(f"❌ PAYMENT VERIFICATION ERROR: {e}")
        raise HTTPException(status_code=400, detail="Payment verification failed")


# ============================================================
# ORDER STATUS
# ============================================================
@router.get("/order-status/{order_id}")
def get_order_status(
    order_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    print(f"🔍 Checking order status: {order_id}")
    
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