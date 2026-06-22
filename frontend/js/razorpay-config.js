// ============================================================
// RAZORPAY FRONTEND CONFIGURATION
// Campus Central Payment Integration
// ============================================================

// Make sure API_BASE is available (fallback to localhost if ACTIVE_CONFIG missing)
const API_BASE = (window.ACTIVE_CONFIG && window.ACTIVE_CONFIG.API_BASE_URL) 
    ? window.ACTIVE_CONFIG.API_BASE_URL 
    : 'http://localhost:8000/api';

// Global variable to track payment status
let razorpayOrderCreated = false;
let currentOrderData = null;

// ============================================================
// Load Razorpay SDK dynamically
// ============================================================
function loadRazorpayScript() {
    return new Promise((resolve, reject) => {
        // Check if already loaded
        if (window.Razorpay) {
            resolve(true);
            return;
        }
        
        const script = document.createElement('script');
        script.src = 'https://checkout.razorpay.com/v1/checkout.js';
        script.onload = () => {
            console.log('✅ Razorpay SDK loaded');
            resolve(true);
        };
        script.onerror = () => {
            console.error('❌ Failed to load Razorpay SDK');
            reject(new Error('Failed to load Razorpay SDK. Please check your internet connection.'));
        };
        document.body.appendChild(script);
    });
}

// ============================================================
// Create Razorpay Order via Backend
// ============================================================
async function createRazorpayOrder(amount, groupId, groupType) {
    const token = localStorage.getItem('authToken');
    
    if (!token) {
        alert('Please login first to make payment');
        window.location.href = 'login.html';
        return null;
    }
    
    try {
        console.log('📤 Creating Razorpay order:', { amount, groupId, groupType });
        
        const response = await fetch(`${API_BASE}/payment/create-order`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                amount: amount,
                group_id: groupId,
                group_type: groupType
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to create payment order');
        }
        
        const orderData = await response.json();
        console.log('✅ Razorpay order created:', orderData);
        return orderData;
        
    } catch (error) {
        console.error('❌ Create order error:', error);
        alert('Failed to initialize payment. Please try again.');
        return null;
    }
}

// ============================================================
// Open Razorpay Checkout
// ============================================================
async function openRazorpayCheckout(amount, groupId, groupType) {
    // Show loading indicator
    const payBtn = document.querySelector('.razorpay-pay-btn');
    if (payBtn) {
        payBtn.disabled = true;
        payBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Initializing Payment...';
    }
    
    try {
        // Step 1: Create order on backend
        const orderData = await createRazorpayOrder(amount, groupId, groupType);
        
        if (!orderData || !orderData.order_id) {
            throw new Error('Failed to create payment order');
        }
        
        // Step 2: Load Razorpay SDK
        await loadRazorpayScript();
        
        // Step 3: Get user details from localStorage
        const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
        
        // Step 4: Configure Razorpay options
        const options = {
            key: orderData.key,
            amount: orderData.amount * 100, // Convert to paise
            currency: "INR",
            name: "Campus Central",
            description: orderData.group_type === 'teacher' 
                ? 'Teacher Group Activation Fee' 
                : 'Celebration Event Activation Fee',
            image: "https://campuscentral.in/logo.png", // Optional: Add your logo URL
            order_id: orderData.order_id,
            prefill: {
                name: currentUser.full_name || '',
                email: currentUser.email || '',
                contact: currentUser.whatsapp || ''
            },
            theme: {
                color: "#e67e22"  // Campus Central orange color
            },
            modal: {
                ondismiss: function() {
                    console.log("Payment modal closed by user");
                    if (payBtn) {
                        payBtn.disabled = false;
                        payBtn.innerHTML = '<i class="fas fa-credit-card"></i> Pay via Credit/Debit Card, UPI, NetBanking →';
                    }
                }
            },
            handler: function(response) {
                // Payment successful - verify with backend
                console.log("Payment success response:", response);
                verifyPaymentWithBackend(response, orderData);
            }
        };
        
        // Step 5: Open Razorpay checkout
        const razorpay = new Razorpay(options);
        razorpay.open();
        
        currentOrderData = orderData;
        
        if (payBtn) {
            payBtn.disabled = false;
            payBtn.innerHTML = '<i class="fas fa-credit-card"></i> Pay via Credit/Debit Card, UPI, NetBanking →';
        }
        
    } catch (error) {
        console.error('❌ Razorpay checkout error:', error);
        alert('Payment initialization failed: ' + error.message);
        if (payBtn) {
            payBtn.disabled = false;
            payBtn.innerHTML = '<i class="fas fa-credit-card"></i> Pay via Credit/Debit Card, UPI, NetBanking →';
        }
    }
}

// ============================================================
// Verify Payment with Backend
// ============================================================
async function verifyPaymentWithBackend(paymentResponse, orderData) {
    const token = localStorage.getItem('authToken');
    
    if (!token) {
        alert('Session expired. Please login again.');
        window.location.href = 'login.html';
        return;
    }
    
    // Show verification message
    const resultDiv = document.getElementById('paymentResult');
    if (resultDiv) {
        resultDiv.innerHTML = '<div class="loading-spinner">⏳ Verifying payment...</div>';
        resultDiv.classList.remove('hidden');
    }
    
    try {
        const verifyData = {
            razorpay_payment_id: paymentResponse.razorpay_payment_id,
            razorpay_order_id: paymentResponse.razorpay_order_id,
            razorpay_signature: paymentResponse.razorpay_signature,
            group_id: orderData.group_id,
            group_type: orderData.group_type
        };
        
        console.log('📤 Verifying payment:', verifyData);
        
        const response = await fetch(`${API_BASE}/payment/verify-payment`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(verifyData)
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            console.log('✅ Payment verified successfully');
            
            if (resultDiv) {
                resultDiv.innerHTML = '<div class="success-msg">✅ Payment successful! Activating your group...</div>';
            }
            
            // Show success modal with confetti
            showPaymentSuccess(result.group_id);
            
        } else {
            console.error('❌ Verification failed:', result);
            if (resultDiv) {
                resultDiv.innerHTML = `<div class="error-msg">❌ Payment verification failed: ${result.message || 'Please contact support'}</div>`;
            }
            alert('Payment verification failed. Please contact support with your transaction ID.');
        }
        
    } catch (error) {
        console.error('❌ Verification error:', error);
        if (resultDiv) {
            resultDiv.innerHTML = '<div class="error-msg">❌ Network error during verification. Please check your connection.</div>';
        }
        alert('Payment verification failed due to network error. Please contact support.');
    }
}

// ============================================================
// Show Payment Success and Redirect
// ============================================================
function showPaymentSuccess(groupId) {
    // Create confetti celebration
    for (let i = 0; i < 100; i++) {
        createConfetti();
    }
    
    // Show success message
    const successHtml = `
        <div style="text-align: center; padding: 1rem;">
            <i class="fas fa-check-circle" style="font-size: 3rem; color: #2ecc71;"></i>
            <h3 style="color: #0f4c5c; margin: 0.5rem 0;">🎉 Payment Successful!</h3>
            <p>Your group has been activated successfully.</p>
            <p>Redirecting to dashboard...</p>
        </div>
    `;
    
    const resultDiv = document.getElementById('paymentResult');
    if (resultDiv) {
        resultDiv.innerHTML = successHtml;
        resultDiv.classList.remove('hidden');
    }
    
    // Redirect to dashboard after 3 seconds
    setTimeout(() => {
        window.location.href = `student_dashboard.html?highlight=${groupId}`;
    }, 3000);
}

// ============================================================
// Confetti Effect Helper
// ============================================================
function createConfetti() {
    setTimeout(() => {
        const confetti = document.createElement('div');
        const icons = ['🎉', '✨', '🎊', '🎈', '🌸', '💛', '⭐', '🎂', '🍾'];
        confetti.innerHTML = icons[Math.floor(Math.random() * icons.length)];
        confetti.style.position = 'fixed';
        confetti.style.left = Math.random() * 100 + '%';
        confetti.style.top = '-20px';
        confetti.style.fontSize = (Math.random() * 20 + 15) + 'px';
        confetti.style.pointerEvents = 'none';
        confetti.style.zIndex = '9999';
        confetti.style.animation = 'confettiFall 2s linear forwards';
        document.body.appendChild(confetti);
        setTimeout(() => confetti.remove(), 2000);
    }, Math.random() * 100);
}

// Add confetti animation CSS if not exists
if (!document.querySelector('#confetti-style')) {
    const style = document.createElement('style');
    style.id = 'confetti-style';
    style.textContent = `
        @keyframes confettiFall {
            0% { transform: translateY(0) rotate(0deg); opacity: 1; }
            100% { transform: translateY(100vh) rotate(360deg); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
}

// ============================================================
// Alternative: Manual UPI Payment (Fallback for Desktop)
// ============================================================
function openManualUPIPayment(amount, upiId) {
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    
    if (isMobile) {
        const payUrl = `upi://pay?pa=${upiId}&pn=Campus%20Central&am=${amount}&cu=INR`;
        window.location.href = payUrl;
        setTimeout(() => {
            alert(`✅ Payment of ₹${amount} initiated.\n\nAfter completing payment, click "I have completed payment" button.`);
        }, 1000);
    } else {
        alert(`💳 DESKTOP PAYMENT INSTRUCTIONS\n\nAmount: ₹${amount}\nUPI ID: ${upiId}\n\nPlease follow these steps:\n\n1. Open any UPI app (GPay/PhonePe/Paytm) on your MOBILE phone\n2. Pay ₹${amount} to UPI ID: ${upiId}\n3. Click "I have completed payment" button below\n\n(UPI payments only work on mobile phones)`);
    }
}