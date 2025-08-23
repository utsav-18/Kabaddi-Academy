// Include Razorpay Checkout script in your HTML before this file:
// <script src="https://checkout.razorpay.com/v1/checkout.js"></script>

async function fetchJSON(url, options = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    ...options
  });
  const text = await res.text();
  const ct = (res.headers.get('content-type') || '').toLowerCase();
  if (!ct.includes('application/json')) {
    // Show a short snippet of what we actually got (usually HTML)
    throw new Error(`Expected JSON but got: ${text.slice(0, 200)}`);
  }
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return JSON.parse(text);
}

async function startPayment(amountRupees, prefill = {}) {
  // 1) Get public key id from backend
  const { key } = await fetchJSON('/get_key'); // absolute path

  // 2) Create order on backend (absolute path)
  const order = await fetchJSON('/create_order', {
    method: 'POST',
    body: JSON.stringify({ amount: amountRupees })
  });

  const options = {
    key,
    amount: order.amount, // in paise
    currency: order.currency || 'INR',
    name: 'Kabaddi Academy',
    description: 'Registration Fee',
    order_id: order.id,
    prefill: {
      name: prefill.name || '',
      email: prefill.email || '',
      contact: prefill.contact || ''
    },
    handler: async function (response) {
      try {
        // 3) Verify payment on backend (absolute path)
        const verify = await fetchJSON('/payment_success', {
          method: 'POST',
          body: JSON.stringify({
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_order_id: response.razorpay_order_id,
            razorpay_signature: response.razorpay_signature
          })
        });
        alert('Payment successful!');
      } catch (e) {
        console.error(e);
        alert('Verification failed on server. Please contact support.');
      }
    },
    modal: {
      ondismiss: function () {
        // Optional: redirect to a dedicated failure page
        // window.location.href = '/payment_failed';
      }
    }
  };

  const rzp = new Razorpay(options);
  rzp.on('payment.failed', function (response) {
    console.error('Payment failed:', response.error);
    window.location.href = '/payment_failed';
  });

  rzp.open();
}

// Example usage: bind to a button click
// document.getElementById('payBtn').addEventListener('click', () => {
//   const amount = document.getElementById('amount').value; // in rupees
//   const name = document.getElementById('name').value;
//   const email = document.getElementById('email').value;
//   const contact = document.getElementById('contact').value;
//   startPayment(amount, { name, email, contact });
// });
