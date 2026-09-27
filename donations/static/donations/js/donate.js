// static/js/donate.js
// Handles the preset/custom amount picker on the donate page.
// The actual `amount` <input> is what gets submitted to Django.
(function () {
  "use strict";

  var amountButtons = document.querySelectorAll(".amount-btn");
  var amountInput = document.getElementById("amount");
  var sumAmount = document.getElementById("sumAmount");
  var sumTotal = document.getElementById("sumTotal");

  if (!amountButtons.length || !amountInput) return;

  function setAmount(value) {
    var v = parseFloat(value) || 0;
    amountInput.value = v;
    if (sumAmount) sumAmount.textContent = "$" + v.toFixed(2);
    if (sumTotal) sumTotal.textContent = "$" + v.toFixed(2);
  }

  amountButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      amountButtons.forEach(function (b) { b.setAttribute("aria-pressed", "false"); });
      btn.setAttribute("aria-pressed", "true");

      if (btn.dataset.amount === "other") {
        // Let the user type a custom amount directly into the real input.
        amountInput.readOnly = false;
        amountInput.focus();
      } else {
        amountInput.readOnly = false;
        setAmount(btn.dataset.amount);
      }
    });
  });

  amountInput.addEventListener("input", function () {
    setAmount(amountInput.value);
  });

  // initialise summary with the input's starting value
  setAmount(amountInput.value);
})();
