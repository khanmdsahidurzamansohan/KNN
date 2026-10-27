document.addEventListener("DOMContentLoaded", () => {
    const $ = id => document.getElementById(id);

    // 1. TRANSLATION PAGE
    const translateBtn = $("translateBtn");
    if (translateBtn) {
        const input = $("translationInput");
        const status = $("translationStatus");
        const resultBox = $("translationResult");
        const output = $("translationOutput");
        const count = $("charCount");

        input?.addEventListener("input", () => {
            if (count) count.textContent = `${input.value.length} / 5000`;
        });

        translateBtn.addEventListener("click", async () => {
            const text = input?.value.trim();
            if (!text) {
                if (status) {
                    status.textContent = "Please enter text first.";
                    status.className = "status-message error";
                }
                input?.focus();
                return;
            }

            translateBtn.disabled = true;
            translateBtn.textContent = "Translating...";
            if (status) {
                status.textContent = "Connecting to KNN AI...";
                status.className = "status-message";
            }
            if (resultBox) resultBox.hidden = true;

            try {
                const response = await fetch("/api/assistant", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        feature: "translate",
                        text: text,
                        source: $("sourceLang")?.value || "Korean",
                        target: $("targetLang")?.value || "English"
                    })
                });

                const data = await response.json();
                if (!response.ok) throw new Error(data.error || "Translation failed.");

                if (output) output.textContent = data.result;
                if (resultBox) resultBox.hidden = false;
                if (status) {
                    status.textContent = "Translation complete!";
                    status.className = "status-message success";
                }

                window.knnLastSource = text;
                window.knnLastResult = data.result;
            } catch (error) {
                if (status) {
                    status.textContent = error.message || "Could not connect to the server.";
                    status.className = "status-message error";
                }
            } finally {
                translateBtn.disabled = false;
                translateBtn.textContent = "Translate Now →";
            }
        });
        return;
    }

    // 2. LEARNING PAGE
    const learningBtn = $("learningBtn");
    if (learningBtn) {
        const learningInput = $("learningTopic");
        const learningStatus = $("learningStatus");
        const learningResult = $("learningResult");
        const learningOutput = $("learningOutput");
        const chipButtons = document.querySelectorAll(".chip");

        chipButtons.forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                const topicAttr = btn.getAttribute("data-topic");
                if (learningInput) learningInput.value = topicAttr || btn.textContent.trim();
            });
        });

        learningBtn.addEventListener("click", async () => {
            const topic = learningInput ? learningInput.value.trim() : "";
            if (!topic) {
                if (learningStatus) {
                    learningStatus.textContent = "Please enter or select a topic first.";
                    learningStatus.className = "status-message error";
                }
                learningInput?.focus();
                return;
            }

            learningBtn.disabled = true;
            learningBtn.textContent = "Generating Lesson...";
            if (learningStatus) {
                learningStatus.textContent = "Connecting to KNN AI...";
                learningStatus.className = "status-message";
            }
            if (learningResult) learningResult.hidden = true;

            try {
                const response = await fetch("/api/assistant", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ feature: "learning", text: topic })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || "Failed to generate lesson.");

                if (learningOutput && learningResult) {
                    learningOutput.textContent = data.result;
                    learningResult.hidden = false;
                }
                if (learningStatus) {
                    learningStatus.textContent = "Lesson generated successfully!";
                    learningStatus.className = "status-message success";
                }
            } catch (error) {
                if (learningStatus) {
                    learningStatus.textContent = error.message || "Server error.";
                    learningStatus.className = "status-message error";
                }
            } finally {
                learningBtn.disabled = false;
                learningBtn.textContent = "Create my lesson →";
            }
        });
        return;
    }

    // 3. SMART REPLY & UNDERSTAND & SITUATIONS PAGES
    const actionBtn = document.querySelector(".tool-panel button, button.btn-primary");
    if (actionBtn) {
        const path = window.location.pathname;
        let feature = "understand";
        if (path.includes("reply")) feature = "reply";
        else if (path.includes("situations")) feature = "situations";

        const inputField = document.querySelector(".tool-panel textarea, textarea, input[type='text']");
        const selectField = document.querySelector(".tool-panel select, select");

        // Dynamically create or find result display card
        let resultCard = document.querySelector(".result-card");
        if (!resultCard) {
            resultCard = document.createElement("div");
            resultCard.className = "result-card";
            resultCard.hidden = true;
            resultCard.style.marginTop = "20px";
            resultCard.style.padding = "20px";
            resultCard.style.background = "#ffffff";
            resultCard.style.borderRadius = "12px";
            resultCard.style.border = "1px solid #eaeaea";
            resultCard.innerHTML = `<h3 style="margin-bottom:10px; color:#333;">AI Output</h3><div class="result-content" style="white-space: pre-wrap; line-height: 1.6; color:#444;"></div>`;
            
            const panel = document.querySelector(".tool-panel") || actionBtn.parentNode;
            panel.appendChild(resultCard);
        }
        
        const resultOutput = resultCard.querySelector(".result-content") || resultCard;

        actionBtn.addEventListener("click", async (e) => {
            e.preventDefault();
            const textValue = inputField ? inputField.value.trim() : "";
            if (!textValue) {
                alert("Please enter a message or text first.");
                inputField?.focus();
                return;
            }

            const originalBtnText = actionBtn.textContent;
            actionBtn.disabled = true;
            actionBtn.textContent = "Processing with AI...";
            resultCard.hidden = true;

            try {
                const payload = {
                    feature: feature,
                    text: textValue,
                    situation: selectField ? selectField.value : "Daily life"
                };

                const response = await fetch("/api/assistant", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });

                const data = await response.json();
                if (!response.ok) throw new Error(data.error || "AI request failed.");

                if (resultOutput) {
                    resultOutput.textContent = data.result;
                    resultCard.hidden = false;
                }
            } catch (error) {
                console.error("AI Error:", error);
                alert(error.message || "Could not complete the AI request.");
            } finally {
                actionBtn.disabled = false;
                actionBtn.textContent = originalBtnText;
            }
        });
    }
});