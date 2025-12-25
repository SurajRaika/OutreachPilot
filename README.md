# AI-Agentic WhatsApp Automation (Self-Hostable)

This is a **self-hostable WhatsApp automation server** built using **FastAPI (Python)** and **Selenium**.

The goal is simple:
Create a practical, internal tool that lets you automate WhatsApp in a **controlled, AI-driven way**, without over-engineering or pretending this is something it’s not.

---

## Home Page

This is the landing page where you manage WhatsApp sessions.

<img width="1418" height="784" alt="image" src="https://github.com/user-attachments/assets/6d75079f-e84c-414a-98b1-2f97b3d42da1" />

Each session represents a **separate WhatsApp Web login**, fully isolated.

---

## Creating a New Session

When you create a new session:
- The server spins up a new Selenium instance
- WhatsApp Web is opened
- The server starts waiting for the QR code

This is intentionally session-based, so multiple accounts can be managed cleanly.

---

## QR Code Extraction (HTTPS only)

Once the QR code is ready, it’s extracted and shown via a simple **HTTPS endpoint**.

<img width="1315" height="567" alt="image" src="https://github.com/user-attachments/assets/46c5645e-38ea-420e-b216-c3b418d6e771" />

<img width="1418" height="784" alt="image" src="https://github.com/user-attachments/assets/aa2f2193-27af-465d-a9ac-f62d45e793bd" />

There’s **no WebSocket usage here**.

That’s a deliberate choice:
- This is an internal tool
- Real-time streaming adds complexity with little benefit
- Simple polling over HTTPS is easier to deploy, debug, and maintain

WebSockets would be overkill for this use case.

---

## Scanning the QR Code

Once the QR code is scanned from your phone, WhatsApp authenticates the session.

<img width="1175" height="597" alt="image" src="https://github.com/user-attachments/assets/13300267-a3eb-4312-a9cb-8a0f71fdebab" />

The server detects the login and marks the session as active.

---

## Active Session Dashboard

After login, you enter the session dashboard.

<img width="1177" height="778" alt="image" src="https://github.com/user-attachments/assets/bb9ad5f9-5f19-4b47-918e-c7be4e6dd802" />

From here, you can enable one of two modes:
- **Outreach Mode**
- **Auto-Reply Mode (AI-powered)**

---

## Outreach Mode

Outreach mode is for sending messages to specific numbers.

You define:
- Phone numbers
- Message content

<img width="988" height="662" alt="image" src="https://github.com/user-attachments/assets/d87d453c-ca90-4880-8722-0f954b7f36ca" />

Important design choice:
This system is **slow by intent**.

WhatsApp automation always carries a risk of getting blocked, so:
- Messages are sent gradually
- No aggressive parallel sending
- Human-like pacing

This is not a bulk-spam tool, and it’s not trying to be one.

---

## Auto-Reply Mode (AI-Agentic)

This is the most powerful part of the system.

Auto-Reply mode uses an **LLM** to automatically respond to incoming messages.

<img width="1074" height="741" alt="image" src="https://github.com/user-attachments/assets/b6f3e8a3-bb1f-42e4-8505-4181f9b88b62" />

You can define:
- Your business context
- The tone and personality
- How responses should be structured
- What the AI should and should not do

Incoming messages are:
1. Read via Selenium
2. Sent to the LLM
3. Replied to in a natural, human-paced way

This turns WhatsApp into an **AI-agentic interface**.

And honestly — it works really, really well.

This is an **AI-agentic WhatsApp automation server**, built for real use — not growth-hacking demos.
