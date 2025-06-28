# 🔐 MiniRSA_Breaker

**All students and educators welcome. Build understanding through math, logic, and real cryptographic theory.**

**Category:**   Cryptography / Educational Visualization  
**Tech Stack:** Python, PyQt6  
**Author:**     [Justin Guida](https://github.com/jguida941)  
**Resume:**     [View My Live Resume on Indeed →](https://profile.indeed.com/p/justing-yqigd8r)

 **⭐ If you find this project useful, please consider starring it!**


Whether you're a **teacher**, a **CS student**, or just **someone fascinated by how passwords work**,  
**this tool was built for you**

> ⚠️ *This **won't teach you how** to break secure RSA encryption.*  
> But... with the **right math and curiosity**, thats **a different story**, lets keep it at that. 

---


# ✨ Features

**RSA Key Generation**  
Generate custom or random small prime keys instantly.

**Modular Exponentiation Engine**  
Performs `c = m^e mod n` and `m = c^d mod n` using Python’s `pow()` function — real, fast RSA behavior.

**Character Mapping System**  
Maps characters **A–Z** to integers **01–26**, with optional symbol support for extended messages.

**Encryption & Decryption Panels**  
Visualize the full message transformation — from plaintext to ciphertext and back — in real time.

**Step-by-Step Math Breakdown**  
Each stage of RSA math is clearly explained and animated for learning purposes.

**Error Handling + Input Validation**  
Smart checks catch invalid primes, characters, and unsupported input types — with helpful messages.

**100% Offline Application**  
Runs entirely on your device — no web server, no uploads, just fast, secure local computation.

**Debug Mode & Educational Hints**  
Toggle debug mode to show raw values, intermediate results, and contextual explanations at every step.

# 📸 Screenshots

## Main Interface RSA Setup  
**Define primes, generate public/private keys, and view entropy ratings in real time.**

<img width="1195" alt="Screenshot 2025-06-27 at 10 18 09 PM" src="https://github.com/user-attachments/assets/b5174655-6163-4e40-856f-27b8a8a2759c" />

---

## Encryption Panel  
## Watch your message get encrypted character by character using modular exponentiation.

<img width="1197" alt="Screenshot 2025-06-27 at 10 18 49 PM" src="https://github.com/user-attachments/assets/5da211a7-97e6-44e0-899d-0e331e3bacbf" />

---

## Decryption Panel  
## Reverse the cipher text and view RSA logic in reverse using your private key.

<img width="1194" alt="Screenshot 2025-06-27 at 10 19 22 PM" src="https://github.com/user-attachments/assets/40b65622-5c40-4cc8-9fd7-bbe587868c8b" />

---

## 🚀  How to Run

Follow these steps to launch **MiniRSA_Breaker** locally:

### 1. Clone the Repository
```bash
git clone https://github.com/jguida941/MiniRSA_Breaker.git
cd MiniRSA_Breaker
```

### 2. Create a virtual environment (recommended)
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Launch the app
```bash
python rsa.py
```

App runs fully offline — no network needed.

---

## 📄 License: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)

© 2025 Justin Guida  
This project is licensed under the **Creative Commons Attribution-NonCommercial 4.0 International License**.

---

###  You May:
-  **Share** — Copy, distribute, and share the code  
- **Adapt** — Remix, transform, or build upon it for personal or academic purposes  

###  You May Not:
- Use this work for commercial purposes  
- Sell, rebrand, or repackage this project for profit  

###  You Must:
- Credit the original author clearly:
  - **Name:** Justin Guida  
  - **Year:** 2025  
  - **GitHub:** [https://github.com/jguida941](https://github.com/jguida941)

---

##  Educational Terms

Educators and students are encouraged to:
- Use this tool in lessons, demos, or assignments  
- Modify and explore it freely for academic learning  
- Ensure visible credit appears in repurposed or adapted materials  

---

##  Attribution Link
[https://creativecommons.org/licenses/by-nc/4.0/](https://creativecommons.org/licenses/by-nc/4.0/)
