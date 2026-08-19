/* =========================================================================
   AI HealthAssist — main.js
   ========================================================================= */

document.addEventListener("DOMContentLoaded", () => {

  // -------------------------------------------------------------------------
  // Fetch and display the active AI provider badge
  // -------------------------------------------------------------------------
  const providerBadge = document.getElementById("provider-badge");

  fetch("/api/provider")
    .then(r => r.json())
    .then(data => {
      if (data.provider) {
        const icon = data.provider.toLowerCase().includes("gemini") ? "✨" : "🤖";
        providerBadge.textContent = icon + " AI Provider: " + data.provider;
        providerBadge.classList.add("provider-loaded");
      }
    })
    .catch(() => {
      providerBadge.textContent = "AI Provider: Unknown";
    });

  // -------------------------------------------------------------------------
  // Element references — First-Aid
  // -------------------------------------------------------------------------
  const btnOpenFirstAid   = document.getElementById("btn-open-firstaid");
  const firstAidSection   = document.getElementById("first-aid-section");
  const firstAidForm      = document.getElementById("first-aid-form");
  const firstAidInput     = document.getElementById("firstaid-input");
  const firstAidCharCount = document.getElementById("firstaid-char-count");
  const firstAidInlineErr = document.getElementById("firstaid-inline-error");
  const firstAidSubmitBtn = document.getElementById("firstaid-submit-btn");
  const firstAidLoading   = document.getElementById("firstaid-loading");
  const firstAidError     = document.getElementById("firstaid-error");
  const firstAidResponse  = document.getElementById("firstaid-response");

  // -------------------------------------------------------------------------
  // Element references — Medicine
  // -------------------------------------------------------------------------
  const btnOpenMedicine   = document.getElementById("btn-open-medicine");
  const medicineSection   = document.getElementById("medicine-section");
  const medicineForm      = document.getElementById("medicine-form");
  const medicineInput     = document.getElementById("medicine-input");
  const medicineInlineErr = document.getElementById("medicine-inline-error");
  const medicineSubmitBtn = document.getElementById("medicine-submit-btn");
  const medicineLoading   = document.getElementById("medicine-loading");
  const medicineError     = document.getElementById("medicine-error");
  const medicineResponse  = document.getElementById("medicine-response");

  // -------------------------------------------------------------------------
  // Module reveal
  // -------------------------------------------------------------------------

  function revealSection(section) {
    section.classList.remove("hidden");
    setTimeout(() => {
      section.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 60);
  }

  btnOpenFirstAid.addEventListener("click", () => {
    revealSection(firstAidSection);
    firstAidInput.focus();
  });

  btnOpenMedicine.addEventListener("click", () => {
    revealSection(medicineSection);
    medicineInput.focus();
  });

  // Keyboard activation on cards
  document.getElementById("card-first-aid").addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); btnOpenFirstAid.click(); }
  });
  document.getElementById("card-medicine").addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); btnOpenMedicine.click(); }
  });

  // -------------------------------------------------------------------------
  // Character counter for textarea
  // -------------------------------------------------------------------------
  firstAidInput.addEventListener("input", () => {
    firstAidCharCount.textContent = firstAidInput.value.length;
  });

  // -------------------------------------------------------------------------
  // Generic helpers
  // -------------------------------------------------------------------------

  function setLoading(submitBtn, loadingEl, isLoading) {
    const btnLabel   = submitBtn.querySelector(".btn-label");
    const btnSpinner = submitBtn.querySelector(".btn-spinner");

    if (isLoading) {
      submitBtn.disabled = true;
      btnLabel.textContent = "Please wait\u2026";
      btnSpinner.classList.remove("hidden");
      loadingEl.classList.remove("hidden");
    } else {
      submitBtn.disabled = false;
      btnSpinner.classList.add("hidden");
      loadingEl.classList.add("hidden");
    }
  }

  function showInlineError(el, message) {
    el.textContent = message;
    el.classList.remove("hidden");
  }

  function clearInlineError(el) {
    el.textContent = "";
    el.classList.add("hidden");
  }

  function showBlockError(el, message) {
    el.textContent = message;
    el.classList.remove("hidden");
  }

  function clearResults(responseEl, errorEl, inlineErrEl) {
    responseEl.classList.add("hidden");
    errorEl.classList.add("hidden");
    clearInlineError(inlineErrEl);
    responseEl.querySelectorAll(".section-content").forEach(p => { p.textContent = ""; });
  }

  // -------------------------------------------------------------------------
  // Render helpers
  // -------------------------------------------------------------------------

  const FIRST_AID_SECTIONS = [
    { key: "immediate_steps",   btnLabel: "Get First-Aid Guidance" },
    { key: "things_to_avoid",   btnLabel: null },
    { key: "warning_signs",     btnLabel: null },
    { key: "when_to_seek_help", btnLabel: null },
  ];

  const MEDICINE_SECTIONS = [
    { key: "what_it_is",          btnLabel: "Get Medicine Information" },
    { key: "common_uses",         btnLabel: null },
    { key: "general_precautions", btnLabel: null },
    { key: "important_warnings",  btnLabel: null },
    { key: "when_to_consult",     btnLabel: null },
  ];

  function renderSections(data, sectionDefs, responseEl) {
    sectionDefs.forEach(({ key }) => {
      const contentEl = document.getElementById(key);
      if (contentEl) {
        contentEl.textContent = data[key] || "No information available for this section.";
      }
    });
    responseEl.classList.remove("hidden");
    responseEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function restoreButtonLabel(btn, label) {
    btn.querySelector(".btn-label").textContent = label;
  }

  // -------------------------------------------------------------------------
  // First-Aid form submission
  // -------------------------------------------------------------------------

  firstAidForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const situation = firstAidInput.value.trim();

    clearResults(firstAidResponse, firstAidError, firstAidInlineErr);

    if (!situation) {
      showInlineError(firstAidInlineErr, "Please describe the first-aid situation before submitting.");
      firstAidInput.focus();
      return;
    }

    setLoading(firstAidSubmitBtn, firstAidLoading, true);

    try {
      const res = await fetch("/api/first-aid", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ situation }),
      });

      const data = await res.json();

      if (!res.ok || data.error) {
        showBlockError(firstAidError, data.error || "An unexpected error occurred. Please try again.");
      } else {
        renderSections(data, FIRST_AID_SECTIONS, firstAidResponse);
      }
    } catch (err) {
      showBlockError(firstAidError, "Network error \u2014 please check your connection and try again.");
    } finally {
      setLoading(firstAidSubmitBtn, firstAidLoading, false);
      restoreButtonLabel(firstAidSubmitBtn, "Get First-Aid Guidance");
    }
  });

  // -------------------------------------------------------------------------
  // Medicine form submission
  // -------------------------------------------------------------------------

  medicineForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const medicine = medicineInput.value.trim();

    clearResults(medicineResponse, medicineError, medicineInlineErr);

    if (!medicine) {
      showInlineError(medicineInlineErr, "Please enter a medicine name before submitting.");
      medicineInput.focus();
      return;
    }

    setLoading(medicineSubmitBtn, medicineLoading, true);

    try {
      const res = await fetch("/api/medicine", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ medicine }),
      });

      const data = await res.json();

      if (!res.ok || data.error) {
        showBlockError(medicineError, data.error || "An unexpected error occurred. Please try again.");
      } else {
        renderSections(data, MEDICINE_SECTIONS, medicineResponse);
      }
    } catch (err) {
      showBlockError(medicineError, "Network error \u2014 please check your connection and try again.");
    } finally {
      setLoading(medicineSubmitBtn, medicineLoading, false);
      restoreButtonLabel(medicineSubmitBtn, "Get Medicine Information");
    }
  });

});
