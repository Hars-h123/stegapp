# 🔐 StegApp — Secure Image Steganography System

StegApp is a secure web application that encrypts messages using password-based AES encryption and hides them inside images using Lossless LSB (Least Significant Bit) steganography.

The system allows secure communication across devices without altering the visual appearance of the image.

---

## 🚀 Features

- 🔑 Password-based AES encryption (Fernet + SHA256 key derivation)
- 🖼️ Lossless LSB image steganography
- 📦 Secure image download system
- 🔓 Hidden message decryption system
- 📱 Cross-device compatibility (Laptop ↔ Mobile)
- 🎨 Modern responsive UI
- 🌙 Theme toggle support
- ⚡ Real-time processing overlays

---

## 🛠 Tech Stack

Backend:

- Python
- Flask
- Cryptography (Fernet AES)
- Pillow (Image Processing)

Frontend:

- HTML
- Tailwind CSS
- Vanilla JavaScript

Version Control:

- Git
- GitHub

---

## 🧠 How It Works

### Step 1 – Encryption

The user enters:

- Secret message
- Password
- Carrier image

The system:

- Generates a SHA256-based key from the password
- Encrypts the message using AES (Fernet)
- Converts encrypted bytes into binary
- Embeds bits inside image pixels using LSB

---

### Step 2 – Steganography

The encrypted message is embedded into:

- The least significant bit of RGB channels
- A delimiter marks end-of-message

The output image looks visually identical to the original.

---

### Step 3 – Decryption

When decoding:

- The binary data is extracted from pixels
- Delimiter stops extraction
- AES decryption is applied using password
- Original message is restored

---

## ⚠ Important Notes

- PNG format is recommended (lossless)
- JPEG compression may corrupt hidden data
- Password must match exactly
- Uploads folder must exist when running locally

---

## 📦 Installation

Clone repository:

git clone https://github.com/yourusername/stegapp.git

cd stegapp

Create virtual environment:

python -m venv venv

Activate environment:

Mac:

source venv/bin/activate

Windows:

venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

Create uploads folder:

mkdir uploads

Run server:

python app.py

---

## 🌍 Cross Device Usage

To test across devices:

Run Flask on local IP:

python app.py

Then access using:

http://YOUR_LOCAL_IP:5000

Ensure both devices are on same network.

---

## 📌 Future Improvements

- Image capacity indicator
- File integrity validation
- Drag & drop improvements
- Production deployment (Render / Railway)
- React front-end upgrade
- Multi-file encryption support

---

## 👨‍💻 Author

Harsh Damania

Built for cryptography learning and practical steganography demonstration.