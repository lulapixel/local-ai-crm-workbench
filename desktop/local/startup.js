"use strict";
const statusText = document.getElementById("status");
const retry = document.getElementById("retry");
window.prospectosLocal.onStatus(status => { statusText.textContent = status.message; retry.hidden = !status.failed; retry.disabled = false; });
retry.addEventListener("click", () => { retry.disabled = true; retry.hidden = true; statusText.textContent = "Tentando iniciar novamente…"; void window.prospectosLocal.retry(); });
