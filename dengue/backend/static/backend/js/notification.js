class DjangoNotificationSystem {
  constructor() {
    this.MESSAGE_TYPES = {
      success: { icon: "✅", color: "#28a745", title: "Success" },
      error: { icon: "❌", color: "#dc3545", title: "Error" },
      warning: { icon: "⚠️", color: "#ffc107", title: "Warning" },
      info: { icon: "ℹ️", color: "#17a2b8", title: "Information" },
    };

    this.init();
  }

  init() {
    document.addEventListener("DOMContentLoaded", () => {
      this.setupStyles();
      this.detectDjangoMessages();
      this.checkURLForMessages();
    });
  }

  setupStyles() {
    if (!document.getElementById("notification-styles")) {
      const style = document.createElement("style");
      style.id = "notification-styles";
      style.textContent = `
                .django-notification {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: white;
                    padding: 15px 20px;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    max-width: 400px;
                    z-index: 10000;
                    animation: slideInRight 0.3s ease-out;
                    font-family: Arial, sans-serif;
                    border-left: 4px solid #17a2b8;
                }
                
                .django-notification.success {
                    border-left-color: #28a745;
                }
                
                .django-notification.error {
                    border-left-color: #dc3545;
                }
                
                .django-notification.warning {
                    border-left-color: #ffc107;
                }
                
                .django-notification.info {
                    border-left-color: #17a2b8;
                }
                
                @keyframes slideInRight {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
                
                .notification-close {
                    background: none;
                    border: none;
                    color: #666;
                    font-size: 16px;
                    cursor: pointer;
                    margin-left: 10px;
                    float: right;
                }

                .django-messages {
                    display: none !important;
                }
            `;
      document.head.appendChild(style);
    }
  }

  detectDjangoMessages() {
    console.log("Django Notification System: Checking for messages...");

    this.checkDjangoMessagesContainer();

    this.checkAlertElements();

    this.checkCommonContainers();
  }

  checkDjangoMessagesContainer() {
    const containers = [
      ".django-messages",
      '[class*="messages"]',
      "#django-messages",
    ];

    containers.forEach((selector) => {
      const container = document.querySelector(selector);
      if (container) {
        const messages = container.querySelectorAll(
          '.alert, [class*="alert-"], .message, [class*="message-"]',
        );
        messages.forEach((messageElement) => {
          this.processMessageElement(messageElement);
        });
      }
    });
  }

  checkAlertElements() {
    const alertSelectors = [
      ".alert",
      '[class*="alert-"]',
      ".message",
      '[class*="message-"]',
    ];

    alertSelectors.forEach((selector) => {
      const elements = document.querySelectorAll(selector);
      elements.forEach((element) => {
        if (this.shouldSkipElement(element)) return;

        this.processMessageElement(element);
      });
    });
  }

  checkCommonContainers() {
    const commonContainers = [
      ".messages",
      ".alert-container",
      ".message-container",
    ];

    commonContainers.forEach((selector) => {
      const containers = document.querySelectorAll(selector);
      containers.forEach((container) => {
        const messages = container.querySelectorAll("div, p, span");
        messages.forEach((element) => {
          if (
            this.looksLikeMessage(element) &&
            !this.shouldSkipElement(element)
          ) {
            this.processMessageElement(element);
          }
        });
      });
    });
  }

  shouldSkipElement(element) {
    if (
      element.tagName === "BUTTON" ||
      element.closest(".tab-container") ||
      element.closest("nav") ||
      element.closest(".main-menu") ||
      element.classList.contains("tab-btn") ||
      element.classList.contains("nav-btn") ||
      element.classList.contains("template-btn") ||
      element.classList.contains("submit-btn") ||
      element.classList.contains("calendar-nav") ||
      element.classList.contains("file-input-label")
    ) {
      return true;
    }

    const text = element.textContent.trim();
    const uiTextPatterns = [
      /^manual$/i,
      /^upload$/i,
      /^download$/i,
      /^home$/i,
      /^report$/i,
      /^message$/i,
      /^weather$/i,
      /^week$/i,
      /^year$/i,
      /^cases$/i,
      /^barangay$/i,
      /^choose csv file$/i,
      /^drop your csv file here$/i,
      /^submit report$/i,
      /^upload file$/i,
      /^prev$/i,
      /^next$/i,
      /^sun$/i,
      /^mon$/i,
      /^tue$/i,
      /^wed$/i,
      /^thu$/i,
      /^fri$/i,
      /^sat$/i,
    ];

    for (const pattern of uiTextPatterns) {
      if (pattern.test(text.toLowerCase())) {
        return true;
      }
    }

    return false;
  }

  looksLikeMessage(element) {
    const text = element.textContent.trim();
    if (!text || text.length < 5) return false;

    const messagePatterns = [
      /successfully/i,
      /error/i,
      /warning/i,
      /upload/i,
      /created/i,
      /updated/i,
      /deleted/i,
      /import/i,
      /export/i,
      /failed/i,
      /invalid/i,
      /required/i,
      /please/i,
      /thank you/i,
      /logged in/i,
      /logged out/i,
      /saved/i,
      /submitted/i,
      /imported/i,
      /exported/i,
    ];

    return messagePatterns.some((pattern) => pattern.test(text.toLowerCase()));
  }

  processMessageElement(element) {
    const messageText = element.textContent.trim();
    if (!messageText) return;

    const messageType = this.detectMessageType(element, messageText);

    this.showNotification(messageText, messageType);

    element.style.display = "none";

    console.log("Django Notification: Showing message:", {
      text: messageText,
      type: messageType,
    });
  }

  detectMessageType(element, messageText) {
    const text = messageText.toLowerCase();
    const classes = element.className.toLowerCase();

    if (classes.includes("success") || text.includes("success")) {
      return "success";
    } else if (
      classes.includes("error") ||
      classes.includes("danger") ||
      text.includes("error") ||
      text.includes("invalid")
    ) {
      return "error";
    } else if (classes.includes("warning") || text.includes("warning")) {
      return "warning";
    } else if (classes.includes("info")) {
      return "info";
    }

    if (text.includes("failed") || text.includes("error")) return "error";
    if (text.includes("success")) return "success";
    if (text.includes("warning")) return "warning";

    return "info";
  }

  showNotification(message, type = "info") {
    const config = this.MESSAGE_TYPES[type] || this.MESSAGE_TYPES.info;

    const notification = document.createElement("div");
    notification.className = `django-notification ${type}`;
    notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 18px;">${config.icon}</span>
                <div style="flex: 1;">
                    <div style="font-weight: bold; color: ${config.color}; margin-bottom: 4px;">
                        ${config.title}
                    </div>
                    <div style="color: #333; font-size: 14px; line-height: 1.4;">
                        ${message}
                    </div>
                </div>
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">
                    ×
                </button>
            </div>
        `;

    document.body.appendChild(notification);

    setTimeout(() => {
      if (notification.parentElement) {
        notification.remove();
      }
    }, 5000);
  }

  checkURLForMessages() {
    const urlParams = new URLSearchParams(window.location.search);

    if (urlParams.has("message")) {
      const message = urlParams.get("message");
      const type = urlParams.get("type") || "info";
      this.showNotification(message, type);
    }

    if (urlParams.get("success")) {
      this.showNotification(urlParams.get("success"), "success");
    }
    if (urlParams.get("error")) {
      this.showNotification(urlParams.get("error"), "error");
    }
    if (urlParams.get("warning")) {
      this.showNotification(urlParams.get("warning"), "warning");
    }
    if (urlParams.get("info")) {
      this.showNotification(urlParams.get("info"), "info");
    }
  }

  showManualNotification(message, type = "info") {
    this.showNotification(message, type);
  }

  success(message) {
    this.showNotification(message, "success");
  }

  error(message) {
    this.showNotification(message, "error");
  }

  warning(message) {
    this.showNotification(message, "warning");
  }

  info(message) {
    this.showNotification(message, "info");
  }
}

window.DjangoNotifications = new DjangoNotificationSystem();
