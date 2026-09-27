// static/js/shop.js
// Handles quantity steppers and the live order summary on the shop page.
// Quantities are stored in real <input name="qty_<id>"> fields so Django
// receives them on submit.
(function () {
  "use strict";

  var steppers = document.querySelectorAll(".qty-stepper");
  var cartLines = document.getElementById("cartLines");
  var cartTotal = document.getElementById("cartTotal");
  var sumDelivery = document.getElementById("sumDelivery");
  var continueBtn = document.getElementById("shopContinue");
  var fulfilment = document.getElementById("fulfilment");

  if (!steppers.length) return;

  function getProductName(stepper) {
    var card = stepper.closest(".product-card");
    var h4 = card ? card.querySelector(".product-info h4") : null;
    return h4 ? h4.textContent.trim() : "Item";
  }

  function renderCart() {
    var subtotal = 0;
    var lines = [];

    steppers.forEach(function (stepper) {
      var input = stepper.querySelector("input[type=number]");
      var qty = parseInt(input.value, 10) || 0;
      var price = parseFloat(stepper.dataset.price) || 0;
      if (qty > 0) {
        var name = getProductName(stepper);
        lines.push({ name: name, qty: qty, price: price });
        subtotal += qty * price;
      }
    });

    if (cartLines) {
      cartLines.innerHTML = "";
      if (!lines.length) {
        cartLines.innerHTML = '<p class="empty-note">Your cart is empty — add a tree to continue.</p>';
      } else {
        lines.forEach(function (line) {
          var row = document.createElement("div");
          row.className = "summary-row";
          row.innerHTML =
            "<span>" + line.name + " × " + line.qty + "</span>" +
            "<span>$" + (line.qty * line.price).toFixed(2) + "</span>";
          cartLines.appendChild(row);
        });
      }
    }

    var deliveryFee = fulfilment && fulfilment.value === "delivery" ? 15 : 0;
    if (sumDelivery) sumDelivery.textContent = deliveryFee ? "$" + deliveryFee.toFixed(2) : "Free";

    var total = subtotal + deliveryFee;
    if (cartTotal) cartTotal.textContent = "$" + total.toFixed(2);
    if (continueBtn) continueBtn.disabled = subtotal <= 0;

    return total;
  }

  steppers.forEach(function (stepper) {
    var input = stepper.querySelector("input[type=number]");
    stepper.querySelector(".qty-plus").addEventListener("click", function () {
      input.value = (parseInt(input.value, 10) || 0) + 1;
      renderCart();
    });
    stepper.querySelector(".qty-minus").addEventListener("click", function () {
      input.value = Math.max(0, (parseInt(input.value, 10) || 0) - 1);
      renderCart();
    });
  });

  if (fulfilment) fulfilment.addEventListener("change", renderCart);

  renderCart();
})();
