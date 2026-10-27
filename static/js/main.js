// KNN - Main JavaScript

document.addEventListener("DOMContentLoaded", () => {
    // Mobile navigation
    const menuToggle = document.getElementById("menuToggle");
    const mainNav = document.getElementById("mainNav");

    if (menuToggle && mainNav) {
        menuToggle.addEventListener("click", () => {
            const isOpen = mainNav.classList.toggle("open");
            menuToggle.setAttribute("aria-expanded", String(isOpen));
        });
    }

    // Copy favorite result
    document.querySelectorAll(".copy-favorite").forEach(button => {
        button.addEventListener("click", async () => {
            try {
                await navigator.clipboard.writeText(
                    button.dataset.copy || ""
                );
                button.textContent = "Copied!";
                setTimeout(() => {
                    button.textContent = "Copy result";
                }, 1800);
            } catch {
                alert("Copy failed. Please select and copy the text manually.");
            }
        });
    });

    // Auto-dismiss flash messages
    document.querySelectorAll(".flash").forEach(message => {
        setTimeout(() => {
            message.style.transition = "opacity 0.4s";
            message.style.opacity = "0";
            setTimeout(() => message.remove(), 450);
        }, 5000);
    });
});