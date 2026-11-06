document.addEventListener('DOMContentLoaded', function () {
    const alertCloseButtons = document.querySelectorAll('.alert-close-btn');
    alertCloseButtons.forEach(function (btn) {
        btn.addEventListener('click', function () {
            const alertBanner = btn.closest('.alert-banner');
            if (alertBanner) {
                alertBanner.remove();
            }
        });
    });

    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function () {
            sidebar.classList.toggle('-translate-x-full');
        });
    }

    const posCartContainer = document.getElementById('posCartContainer');
    if (!posCartContainer) return;

    let cart = [];

    const cartItemsList = document.getElementById('cartItemsList');
    const cartSubtotalEl = document.getElementById('cartSubtotal');
    const cartTotalEl = document.getElementById('cartTotal');
    const amountTenderedInput = document.getElementById('amountTendered');
    const changeAmountEl = document.getElementById('changeAmount');
    const clearCartBtn = document.getElementById('clearCartBtn');
    const checkoutBtn = document.getElementById('checkoutBtn');
    const paymentMethodSelect = document.getElementById('paymentMethod');

    const addToCartBtns = document.querySelectorAll('.add-to-cart-btn');
    addToCartBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            const productId = parseInt(btn.dataset.productId);
            const productName = btn.dataset.productName;
            const price = parseFloat(btn.dataset.price);
            const stock = parseInt(btn.dataset.stock);

            addToCart(productId, productName, price, stock);
        });
    });

    function addToCart(productId, productName, price, stock) {
        const existingItem = cart.find(item => item.product_id === productId);

        if (existingItem) {
            if (existingItem.quantity + 1 > stock) {
                alert(`Cannot add more "${productName}". Available stock limit (${stock}) reached.`);
                return;
            }
            existingItem.quantity += 1;
        } else {
            if (stock < 1) {
                alert(`"${productName}" is currently out of stock.`);
                return;
            }
            cart.push({
                product_id: productId,
                product_name: productName,
                unit_price: price,
                quantity: 1,
                max_stock: stock
            });
        }
        renderCart();
    }

    function removeFromCart(productId) {
        cart = cart.filter(item => item.product_id !== productId);
        renderCart();
    }

    function updateQuantity(productId, newQty) {
        const item = cart.find(item => item.product_id === productId);
        if (!item) return;

        if (newQty <= 0) {
            removeFromCart(productId);
            return;
        }

        if (newQty > item.max_stock) {
            alert(`Stock limit reached. Maximum available is ${item.max_stock}.`);
            return;
        }

        item.quantity = newQty;
        renderCart();
    }

    function calculateCartTotals() {
        return cart.reduce((sum, item) => sum + (item.unit_price * item.quantity), 0);
    }

    function updateChange() {
        const total = calculateCartTotals();
        const tendered = parseFloat(amountTenderedInput ? amountTenderedInput.value : 0) || 0;
        const change = tendered - total;

        if (changeAmountEl) {
            changeAmountEl.textContent = `₱${(change > 0 ? change : 0).toFixed(2)}`;
        }
    }

    if (amountTenderedInput) {
        amountTenderedInput.addEventListener('input', updateChange);
    }

    if (clearCartBtn) {
        clearCartBtn.addEventListener('click', function () {
            cart = [];
            if (amountTenderedInput) amountTenderedInput.value = '';
            renderCart();
        });
    }

    function renderCart() {
        if (!cartItemsList) return;
        cartItemsList.innerHTML = '';

        if (cart.length === 0) {
            cartItemsList.innerHTML = '<li class="text-gray-500 text-center py-4">Cart is empty</li>';
            if (cartSubtotalEl) cartSubtotalEl.textContent = '₱0.00';
            if (cartTotalEl) cartTotalEl.textContent = '₱0.00';
            updateChange();
            return;
        }

        const total = calculateCartTotals();

        cart.forEach(item => {
            const itemSubtotal = item.unit_price * item.quantity;
            const li = document.createElement('li');
            li.className = 'flex items-center justify-between py-2 border-b border-gray-100';

            li.innerHTML = `
                <div class="flex-1">
                    <h4 class="font-medium text-gray-800 text-sm">${item.product_name}</h4>
                    <span class="text-xs text-gray-500">₱${item.unit_price.toFixed(2)} x ${item.quantity}</span>
                </div>
                <div class="flex items-center space-x-2">
                    <button class="qty-btn-minus px-2 py-1 bg-gray-200 text-gray-700 text-xs rounded hover:bg-gray-300" data-id="${item.product_id}">-</button>
                    <span class="text-sm font-semibold text-gray-700">${item.quantity}</span>
                    <button class="qty-btn-plus px-2 py-1 bg-gray-200 text-gray-700 text-xs rounded hover:bg-gray-300" data-id="${item.product_id}">+</button>
                    <span class="text-sm font-bold text-gray-900 ml-2">₱${itemSubtotal.toFixed(2)}</span>
                    <button class="remove-btn text-red-500 hover:text-red-700 ml-2 text-xs font-bold" data-id="${item.product_id}">✕</button>
                </div>
            `;
            cartItemsList.appendChild(li);
        });

        cartItemsList.querySelectorAll('.qty-btn-minus').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = parseInt(btn.dataset.id);
                const item = cart.find(i => i.product_id === id);
                if (item) updateQuantity(id, item.quantity - 1);
            });
        });

        cartItemsList.querySelectorAll('.qty-btn-plus').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = parseInt(btn.dataset.id);
                const item = cart.find(i => i.product_id === id);
                if (item) updateQuantity(id, item.quantity + 1);
            });
        });

        cartItemsList.querySelectorAll('.remove-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = parseInt(btn.dataset.id);
                removeFromCart(id);
            });
        });

        if (cartSubtotalEl) cartSubtotalEl.textContent = `₱${total.toFixed(2)}`;
        if (cartTotalEl) cartTotalEl.textContent = `₱${total.toFixed(2)}`;
        updateChange();
    }

    if (checkoutBtn) {
        checkoutBtn.addEventListener('click', function () {
            if (cart.length === 0) {
                alert('Cart is empty. Please add items before checking out.');
                return;
            }

            const total = calculateCartTotals();
            const amountTendered = parseFloat(amountTenderedInput ? amountTenderedInput.value : 0) || 0;
            const paymentMethod = paymentMethodSelect ? paymentMethodSelect.value : 'Cash';

            if (amountTendered < total) {
                alert(`Insufficient payment tendered! Total is ₱${total.toFixed(2)}, but received ₱${amountTendered.toFixed(2)}.`);
                return;
            }

            const payload = {
                cart: cart.map(i => ({ product_id: i.product_id, quantity: i.quantity })),
                payment_method: paymentMethod,
                amount_tendered: amountTendered
            };

            checkoutBtn.disabled = true;
            checkoutBtn.textContent = 'Processing...';

            fetch('/pos/checkout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            })
            .then(response => response.json())
            .then(data => {
                checkoutBtn.disabled = false;
                checkoutBtn.textContent = 'Complete Checkout';

                if (data.success) {
                    alert(`Transaction successful! Sale #${data.sale_id} recorded. Change: ₱${data.change_amount.toFixed(2)}`);
                    cart = [];
                    if (amountTenderedInput) amountTenderedInput.value = '';
                    renderCart();
                    window.location.reload();
                } else {
                    alert(`Checkout Error: ${data.message}`);
                }
            })
            .catch(error => {
                checkoutBtn.disabled = false;
                checkoutBtn.textContent = 'Complete Checkout';
                alert(`Server Error: ${error.message}`);
            });
        });
    }
});