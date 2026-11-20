/**
 * HACKSPHERE - Interactive Application Scripts
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. Mobile Menu Toggle
  const hamburger = document.getElementById("hamburgerBtn");
  const mobileMenu = document.getElementById("mobileMenu");
  if (hamburger && mobileMenu) {
    hamburger.addEventListener("click", () => {
      mobileMenu.classList.toggle("active");
    });
  }

  // 2. Password Visibility Toggle
  const toggleButtons = document.querySelectorAll(".password-toggle-btn");
  toggleButtons.forEach((btn) => {
    btn.addEventListener("click", function () {
      const targetId = this.getAttribute("data-target");
      const input = document.getElementById(targetId);
      if (!input) return;

      const isPassword = input.type === "password";
      input.type = isPassword ? "text" : "password";

      // Toggle Eye Icon SVG
      const icon = this.querySelector("svg");
      if (icon) {
        if (isPassword) {
          // Eye Slash Icon
          icon.innerHTML = `
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
          `;
          this.setAttribute("aria-label", "Hide password");
        } else {
          // Normal Eye Icon
          icon.innerHTML = `
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          `;
          this.setAttribute("aria-label", "Show password");
        }
      }
    });
  });

  // 3. Role Selector on Sign Up Page
  const roleOptions = document.querySelectorAll(".role-option");
  roleOptions.forEach((opt) => {
    opt.addEventListener("click", function () {
      roleOptions.forEach((o) => o.classList.remove("selected"));
      this.classList.add("selected");
      const radio = this.querySelector('input[type="radio"]');
      if (radio) radio.checked = true;
    });
  });

  // 4. Tab Switcher
  const tabBtns = document.querySelectorAll(".tab-btn");
  tabBtns.forEach((btn) => {
    btn.addEventListener("click", function () {
      const parent = this.closest(".tabs-wrapper") || document;
      const targetId = this.getAttribute("data-tab");

      parent.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      parent.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));

      this.classList.add("active");
      const targetContent = parent.querySelector(`#${targetId}`);
      if (targetContent) {
        targetContent.classList.add("active");
      }
    });
  });

  // 5. Alert Auto-Dismiss
  const alertCloseBtns = document.querySelectorAll(".alert-close");
  alertCloseBtns.forEach((btn) => {
    btn.addEventListener("click", function () {
      const alert = this.closest(".alert");
      if (alert) {
        alert.style.opacity = "0";
        alert.style.transform = "translateY(-6px)";
        setTimeout(() => alert.remove(), 200);
      }
    });
  });

  // 6. Demo Account Quick-Fill
  window.fillCredentials = function (email, password) {
    const emailInput = document.getElementById("loginEmail");
    const passwordInput = document.getElementById("loginPassword");
    if (emailInput && passwordInput) {
      emailInput.value = email;
      passwordInput.value = password;
      emailInput.focus();
    }
  };

  // 7. Review Modal Handling (Organizer Manage View)
  window.openReviewModal = function (submissionId, projectName, submitterName, currentStatus, currentFeedback) {
    const modal = document.getElementById("reviewModal");
    const form = document.getElementById("reviewForm");
    const titleEl = document.getElementById("modalProjectName");
    const submitterEl = document.getElementById("modalSubmitterName");
    const feedbackInput = document.getElementById("reviewFeedback");
    const acceptRadio = document.getElementById("decisionAccept");
    const underReviewRadio = document.getElementById("decisionUnderReview");
    const needsChangesRadio = document.getElementById("decisionNeedsChanges");
    const rejectRadio = document.getElementById("decisionReject");

    if (modal && form) {
      form.action = `/api/submissions/${submissionId}/review`;
      if (titleEl) titleEl.textContent = projectName;
      if (submitterEl) submitterEl.textContent = `Certificate Recipient: ${submitterName}`;
      if (feedbackInput) feedbackInput.value = currentFeedback || "";

      if ((currentStatus === "accepted" || currentStatus === "approved") && acceptRadio) {
        acceptRadio.checked = true;
      } else if ((currentStatus === "needs_changes" || currentStatus === "rejected") && (needsChangesRadio || rejectRadio)) {
        if (needsChangesRadio) needsChangesRadio.checked = true;
        else if (rejectRadio) rejectRadio.checked = true;
      } else if (underReviewRadio) {
        underReviewRadio.checked = true;
      } else if (acceptRadio) {
        acceptRadio.checked = true;
      }

      modal.classList.add("active");
    }
  };

  window.closeReviewModal = function () {
    const modal = document.getElementById("reviewModal");
    if (modal) {
      modal.classList.remove("active");
    }
  };

  // Real-time filtering for Submissions in Organizer Manage View
  window.filterSubmissions = function () {
    const q = (document.getElementById("subSearchInput")?.value || "").toLowerCase().trim();
    const st = document.getElementById("subStatusFilter")?.value || "all";
    document.querySelectorAll(".submission-item").forEach(el => {
      const text = el.getAttribute("data-text") || "";
      const status = el.getAttribute("data-status") || "";
      const matchesQ = !q || text.includes(q);
      const matchesSt = st === "all" ||
        (st === "approved" && (status === "approved" || status === "accepted")) ||
        (st === "under_review" && (status === "under_review" || status === "pending")) ||
        (st === "needs_changes" && (status === "needs_changes" || status === "rejected"));
      el.style.display = matchesQ && matchesSt ? "" : "none";
    });
  };

  // Real-time filtering for Participants in Organizer Manage View
  window.filterParticipants = function () {
    const q = (document.getElementById("partSearchInput")?.value || "").toLowerCase().trim();
    const st = document.getElementById("partStatusFilter")?.value || "all";
    document.querySelectorAll(".participant-row").forEach(el => {
      const text = el.getAttribute("data-text") || "";
      const status = el.getAttribute("data-status") || "";
      const matchesQ = !q || text.includes(q);
      const matchesSt = st === "all" ||
        (st === "pending" && status === "pending") ||
        (st === "accepted" && (status === "accepted" || status === "registered")) ||
        (st === "rejected" && status === "rejected");
      el.style.display = matchesQ && matchesSt ? "" : "none";
    });
  };

  // Close modal when clicking on backdrop
  const modalBackdrop = document.getElementById("reviewModal");
  if (modalBackdrop) {
    modalBackdrop.addEventListener("click", function (e) {
      if (e.target === this) {
        closeReviewModal();
      }
    });
  }

  // 8. Copy to Clipboard Utility
  window.copyText = function (text, btnElement) {
    navigator.clipboard.writeText(text).then(() => {
      const originalText = btnElement.innerText;
      btnElement.innerText = "Copied!";
      setTimeout(() => {
        btnElement.innerText = originalText;
      }, 2000);
    });
  };
});
