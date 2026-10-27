(() => {
  const messagesBox = document.getElementById("messages");
  const statusBox = document.getElementById("status");
  const noticeBox = document.getElementById("notice");
  const messageForm = document.getElementById("messageForm");
  const messageInput = document.getElementById("messageInput");
  const sourceLanguage = document.getElementById("sourceLanguage");
  const sendButton = document.getElementById("sendButton");
  const startForm = document.getElementById("startForm");
  const friendEmail = document.getElementById("friendEmail");
  const chatTitle = document.getElementById("chatTitle");

  const params = new URLSearchParams(window.location.search);
  const conversationId = Number(params.get("conversation"));
  const socket = io();

  let joined = false;
  let loaded = false;
  const shownIds = new Set();

  function setStatus(message) {
    if (statusBox) statusBox.textContent = message;
  }

  function setNotice(message) {
    if (noticeBox) noticeBox.textContent = message;
  }

  function setSendEnabled(enabled) {
    if (sendButton) sendButton.disabled = !enabled;
    if (messageInput) messageInput.disabled = !enabled;
    if (sourceLanguage) sourceLanguage.disabled = !enabled;
  }

  function addMessage(message) {
    if (!messagesBox) return;
    if (message.id && shownIds.has(message.id)) return;
    if (message.id) shownIds.add(message.id);

    const item = document.createElement("div");
    const mine = Number(message.sender_id) === Number(
      document.body.dataset.userId || -1
    );
    item.className = "message" + (mine ? " mine" : "");

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `${message.sender_name || "User"} · ${message.created_at || ""}`;
    item.appendChild(meta);

    const originalLabel = document.createElement("strong");
    originalLabel.textContent = "Original message";
    item.appendChild(originalLabel);

    const original = document.createElement("div");
    original.textContent = message.original_text || "";
    item.appendChild(original);

    const translation = document.createElement("div");
    translation.className = "translation";

    const translationLabel = document.createElement("strong");
    translationLabel.textContent = "Translation";
    translation.appendChild(translationLabel);

    const translated = document.createElement("div");
    if (message.translated_text) {
      translated.textContent = message.translated_text;
    } else {
      translated.textContent = message.translation_status === "failed"
        ? "Translation failed. The original message was saved."
        : "No translation available.";
    }
    translation.appendChild(translated);
    item.appendChild(translation);

    messagesBox.appendChild(item);
    messagesBox.scrollTop = messagesBox.scrollHeight;
  }

  async function loadMessages() {
    if (!window.KNN_CHAT || !window.KNN_CHAT.messagesUrlTemplate) return;
    const url = window.KNN_CHAT.messagesUrlTemplate.replace(
      "999999", String(conversationId)
    );

    try {
      const response = await fetch(url);
      const data = await response.json();

      if (!response.ok) throw new Error(data.error || "Could not load messages.");

      messagesBox.replaceChildren();
      shownIds.clear();
      data.messages.forEach(addMessage);
      loaded = true;
      setStatus("Conversation loaded. Connect and send a message.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  // Start Chat Form Submit Handler (জিমেইল দিয়ে চ্যাট শুরুর জন্য)
  if (startForm) {
    startForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      setNotice("Starting conversation...");

      try {
        const response = await fetch("/api/chat/start", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: friendEmail.value.trim() })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Could not start chat.");

        // সফল হলে রিডাইরেক্ট করবে
        window.location.href = data.redirect;
      } catch (error) {
        setNotice(error.message);
        console.error("Start chat error:", error);
      }
    });
  }

  if (messageForm) {
    messageForm.addEventListener("submit", (event) => {
      event.preventDefault();

      const text = messageInput.value.trim();
      if (!conversationId || !text || !joined) {
        setStatus("Open a conversation and wait for the connection.");
        return;
      }

      socket.emit("send_chat_message", {
        conversation_id: conversationId,
        text,
        source_language: sourceLanguage.value
      });

      messageInput.value = "";
      messageInput.focus();
      setStatus("Sending message and preparing translation...");
    });
  }

  socket.on("connect", () => {
    if (!conversationId) {
      setStatus("Connected. Select a conversation or start one.");
      return;
    }
    socket.emit("join_chat", { conversation_id: conversationId });
  });

  socket.on("joined_chat", (data) => {
    if (Number(data.conversation_id) !== conversationId) return;
    joined = true;
    setSendEnabled(true);
    setStatus("Connected. You can send messages now.");
    if (!loaded) loadMessages();
  });

  socket.on("new_chat_message", (message) => {
    if (Number(message.conversation_id) !== conversationId) return;
    addMessage(message);
    setStatus(message.translation_status === "failed"
      ? "Message delivered, but translation failed."
      : "Message received.");
  });

  socket.on("chat_error", (data) => {
    setStatus(data.error || "A chat error occurred.");
  });

  socket.on("disconnect", () => {
    joined = false;
    setSendEnabled(false);
    setStatus("Disconnected. Reconnecting...");
  });

  if (conversationId) {
    const activeLink = document.querySelector(
      `.friend[href*="conversation=${conversationId}"]`
    );
    if (activeLink && chatTitle) {
      activeLink.classList.add("active");
      chatTitle.textContent = "Chat with " + activeLink.childNodes[0].textContent.trim();
    } else if (chatTitle) {
      chatTitle.textContent = "Private conversation";
    }
    setSendEnabled(false);
    setStatus("Connecting to chat...");
  } else if (chatTitle) {
    chatTitle.textContent = "No conversation selected";
    setSendEnabled(false);
    if (messageInput) messageInput.placeholder = "Start a conversation first";
  }
})();