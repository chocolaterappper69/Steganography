# 🔐 Image Steganography Tool — LSB Method

> Hide secret text messages inside images using pixel-level manipulation. Invisible to the human eye.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green?logo=opencv)
![NumPy](https://img.shields.io/badge/NumPy-2.x-orange?logo=numpy)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## 📖 What is Steganography?

Steganography is the practice of **hiding secret information within ordinary, non-secret data** so that the very existence of the hidden message is concealed. Unlike encryption (which scrambles data), steganography makes data *invisible*.

This tool implements the **LSB (Least Significant Bit)** technique on digital images — modifying only the last bit of each pixel channel value to embed secret text, causing a visual change of at most ±1 per channel value — **completely undetectable to the human eye**.

---

## 🧠 How It Works

### The LSB Technique

Every pixel in an RGB image has 3 channel values — Red, Green, Blue — each stored as an 8-bit number (0–255).

```
Example:  156 in binary = 1 0 0 1 1 1 0 [0]  ← LSB (Least Significant Bit)
                                              ↑
                          Change this bit:  156 → 157  (difference of just 1 — invisible!)
```

Each bit of the secret message overwrites the LSB of one channel value. Since only the last bit changes, the colour shift is imperceptible.

### Encoding Process
1. Convert the secret text → binary string (8 bits per character)
2. Append a delimiter `#####` to mark the end of the message
3. Embed each bit into the LSB of consecutive pixel channel values (R→G→B→next pixel→…)
4. Save as **PNG** (lossless compression — mandatory)

### Decoding Process
1. Read the LSB from each pixel channel value sequentially
2. Collect bits until the delimiter `#####` is found
3. Convert the binary string back to characters → recover original text

### Image Capacity
```
Max characters ≈ (width × height × 3) / 8
Example: A 500×500 image can hold ≈ 93,750 characters
```

---

## ✨ Features

| Feature | Description |
|---|---|
| 🖼️ LSB Steganography | Hides data with near-zero perceptual distortion |
| 🔑 XOR Encryption | Optional symmetric cipher applied before hiding |
| 🔤 Caesar Cipher | Optional character-shift cipher |
| 📊 Capacity Checker | Warns if the message is too large for the image |
| 🔍 Distortion Analyzer | Shows pixel-level diff stats after encoding |
| 🖥️ CLI Interface | Full command-line support with flags |
| 🎯 Built-in Demo | Auto-runs with no arguments — generates test image |

---

## 🛠️ Requirements

- Python 3.8 or higher
- `opencv-python`
- `numpy`

### Install Dependencies

```bash
pip install opencv-python numpy
```

---

## 🚀 Usage

### 1. Run the Built-in Demo (no image needed)

```bash
python steganography.py
```

Generates a synthetic 500×500 image, hides a sample message inside it, saves `encoded.png`, reloads it, decodes the message, and verifies it matches the original.

---

### 2. Encode — Hide a Message in Your Image

**Basic (no encryption):**
```bash
python steganography.py --mode encode --image photo.png --message "Your secret message"
```

**With XOR Encryption (key = 99):**
```bash
python steganography.py --mode encode --image photo.png --message "Secret" --xor 99
```

**With Caesar Cipher (shift = 13):**
```bash
python steganography.py --mode encode --image photo.png --message "Secret" --caesar 13
```

**Custom output filename:**
```bash
python steganography.py --mode encode --image photo.png --message "Hello" --output hidden.png
```

---

### 3. Decode — Extract the Hidden Message

**Basic:**
```bash
python steganography.py --mode decode --image encoded.png
```

**With XOR Decryption (use same key as encoding):**
```bash
python steganography.py --mode decode --image encoded.png --xor 99
```

**With Caesar Decryption (use same shift as encoding):**
```bash
python steganography.py --mode decode --image encoded.png --caesar 13
```

---

## 📋 Arguments Reference

| Argument | Required | Default | Description |
|---|---|---|---|
| `--mode` | Yes | — | `encode` or `decode` |
| `--image` | Yes | — | Path to input image (PNG recommended) |
| `--message` | Encode only | — | Secret text to hide |
| `--output` | No | `encoded.png` | Output filename for encoded image |
| `--xor` | No | `0` | XOR cipher key (0–255) |
| `--caesar` | No | `0` | Caesar cipher shift value |

---

## ⚠️ Important Rules

| Rule | Reason |
|---|---|
| Always save output as **PNG** | JPEG compression is lossy — it corrupts hidden bits |
| Use **same key** for decode | XOR/Caesar keys must match exactly between encode and decode |
| Image must be **large enough** | Capacity = `(W × H × 3) / 8` characters |
| Multi-line messages in CLI | Use literal `\n`: `--message "Line1\nLine2"` |

---

## 🔐 Encryption Modes (Optional)

### XOR Cipher
- XOR's each character's ASCII value with a key byte (0–255)
- Symmetric: encrypt and decrypt use the **same function and key**
- Fast, simple, and deterministic

### Caesar Cipher
- Shifts each character's ASCII value by N positions (modulo 256)
- Decryption uses the same shift value (negated internally)

> ⚠️ These are educational ciphers. For production use, consider AES-256 or RSA.

---

## 🧪 Sample Output

```
============================================================
  IMAGE STEGANOGRAPHY DEMO — LSB Method
============================================================

🎨 Creating synthetic test image (500×500)...

📝 SECRET MESSAGE:
----------------------------------------
Hello, World!
This is a secret message hidden using LSB steganography.
Line 3: You can't see me in the image!
Line 4: NumPy + OpenCV = 🔐
----------------------------------------

🔑 XOR encryption applied (key=42)

📊 CAPACITY REPORT
   Image size      : 500×500 px
   Max capacity    : 93745 characters
   Message size    : 104 characters
   Total needed    : 109 characters
   ✅ Message fits! Using 0.1% of image capacity.

🔐 ENCODING
   Binary payload length : 872 bits
   Pixels modified       : 291
   ✅ Encoding complete!

🔍 DISTORTION ANALYSIS
   Max pixel difference  : 1  (should be 1)
   Mean pixel difference : 0.000029  (near-zero)
   Human eye detectable  : NO ✅

🔓 DECODING
   Bits read    : 872
   Chars found  : 104
   ✅ Decoding complete!

✅ VERIFICATION PASSED: Decoded message matches original.
```

---

## 📂 File Structure

```
.
├── steganography.py        ← Main script (all logic in a single file)
├── README_steganography.md ← This file
└── encoded.png             ← Generated after running demo or encode mode
```

---

## 📚 Concepts Demonstrated

- Digital image representation (pixels, RGB channels, 8-bit values)
- Binary encoding of ASCII/Unicode text
- Bitwise operations (`AND`, `OR`) for LSB manipulation
- Lossless vs lossy image formats (PNG vs JPEG)
- Symmetric encryption (XOR cipher, Caesar cipher)
- NumPy array flattening and reshaping
- OpenCV image I/O (`imread`, `imwrite`)
- Python CLI with `argparse`

---

## 👥 Team

Built as part of math mini project 

---

## 📄 License

MIT License — free to use, modify, and distribute with attribution.
