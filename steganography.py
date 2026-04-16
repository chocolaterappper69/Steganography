"""
╔══════════════════════════════════════════════════════════════════╗
║           IMAGE STEGANOGRAPHY TOOL — LSB Method                 ║
║    Hide secret text inside images using pixel manipulation       ║
║    Tools: Python, OpenCV (cv2), NumPy only                       ║
╚══════════════════════════════════════════════════════════════════╝

HOW IT WORKS (Brief Theory):
─────────────────────────────
Every pixel in an RGB image has 3 channel values (R, G, B),
each ranging from 0–255 (8 bits). The LSB (Least Significant Bit)
is the rightmost bit of each value.

  Example: 156 in binary = 1 0 0 1 1 1 0 [0]  ← LSB
                                              ↑
                            Changing this bit: 156 → 157
                            That's only ±1 difference — invisible to the human eye!

ENCODING PROCESS:
  1. Convert secret text → binary string
  2. Add a delimiter at the end so decoder knows where to stop
  3. Embed each bit into the LSB of consecutive pixel channel values
  4. Save modified image as PNG (lossless — crucial!)

DECODING PROCESS:
  1. Read LSBs from consecutive pixel channel values
  2. Collect bits until delimiter is found
  3. Convert binary back to text

CAPACITY:
  Each pixel can store 3 bits (1 per R/G/B channel)
  Capacity (chars) ≈ (width × height × 3) / 8

OPTIONAL ENCRYPTION:
  XOR cipher: each character's ASCII value is XOR'd with a key byte
  Caesar cipher: each character is shifted by N positions in ASCII
"""

import cv2
import numpy as np
import argparse
import sys
import os

# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────

DELIMITER = "#####"          # Marks end of hidden message
DELIMITER_BINARY = ''.join(format(ord(c), '08b') for c in DELIMITER)


# ══════════════════════════════════════════════════════════════════
#  SECTION 1 — BINARY CONVERSION UTILITIES
# ══════════════════════════════════════════════════════════════════

def text_to_binary(text: str) -> str:
    """
    Convert a string to its binary representation.

    Each character → 8-bit binary string (ASCII code).
    Supports multi-line text via standard newline character.

    Args:
        text (str): The plaintext message (can be multi-line).

    Returns:
        str: A string of '0' and '1' characters.

    Example:
        text_to_binary("Hi") → "0100100001101001"
    """
    binary = ""
    for char in text:
        # ord(char) gives ASCII integer, format pads to 8 bits
        binary += format(ord(char), '08b')
    return binary


def binary_to_text(binary: str) -> str:
    """
    Convert a binary string back to readable text.

    Processes 8 bits at a time → one character.

    Args:
        binary (str): Raw binary string (length must be multiple of 8).

    Returns:
        str: Decoded text string.

    Example:
        binary_to_text("0100100001101001") → "Hi"
    """
    text = ""
    # Walk through binary string in 8-bit chunks
    for i in range(0, len(binary), 8):
        byte = binary[i:i + 8]
        if len(byte) < 8:
            break  # Ignore incomplete trailing byte
        text += chr(int(byte, 2))
    return text


# ══════════════════════════════════════════════════════════════════
#  SECTION 2 — OPTIONAL ENCRYPTION (XOR & CAESAR)
# ══════════════════════════════════════════════════════════════════

def xor_encrypt(text: str, key: int) -> str:
    """
    XOR cipher: each character's ASCII value is XOR'd with the key.

    XOR encryption is its own inverse — same function encrypts & decrypts.
    Key must be 0–255 (one byte).

    Args:
        text (str): Plaintext or ciphertext.
        key  (int): Encryption key (0–255).

    Returns:
        str: Encrypted/decrypted string.
    """
    return ''.join(chr(ord(c) ^ key) for c in text)


def caesar_encrypt(text: str, shift: int) -> str:
    """
    Caesar cipher: shift each character's ASCII value by `shift`.

    Args:
        text  (str): Plaintext message.
        shift (int): Number of positions to shift (positive = encrypt).

    Returns:
        str: Shifted string.
    """
    return ''.join(chr((ord(c) + shift) % 256) for c in text)


def caesar_decrypt(text: str, shift: int) -> str:
    """Reverse of caesar_encrypt."""
    return caesar_encrypt(text, -shift)


# ══════════════════════════════════════════════════════════════════
#  SECTION 3 — CAPACITY CHECK
# ══════════════════════════════════════════════════════════════════

def get_capacity(image: np.ndarray) -> int:
    """
    Calculate how many characters can be hidden in the given image.

    Formula: (total pixels × 3 channels) ÷ 8 bits per character
    We subtract space for the delimiter too.

    Args:
        image (np.ndarray): The cover image (H × W × 3).

    Returns:
        int: Maximum number of characters that can be stored.
    """
    height, width, channels = image.shape
    total_bits = height * width * channels
    usable_bits = total_bits - len(DELIMITER_BINARY)
    return usable_bits // 8


def check_capacity(image: np.ndarray, message: str) -> bool:
    """
    Verify image has enough capacity for the message + delimiter.

    Prints a debug summary of sizes.

    Args:
        image   (np.ndarray): Cover image.
        message (str)       : Secret message (already encrypted if applicable).

    Returns:
        bool: True if it fits, False otherwise.
    """
    capacity   = get_capacity(image)
    msg_len    = len(message)
    delim_len  = len(DELIMITER)
    total_needed = msg_len + delim_len

    print("\n📊 CAPACITY REPORT")
    print(f"   Image size      : {image.shape[1]}×{image.shape[0]} px")
    print(f"   Max capacity    : {capacity} characters")
    print(f"   Message size    : {msg_len} characters")
    print(f"   Delimiter size  : {delim_len} characters")
    print(f"   Total needed    : {total_needed} characters")
    print(f"   Space remaining : {capacity - total_needed} characters")

    if total_needed > capacity:
        print(f"\n❌ ERROR: Message is too large by {total_needed - capacity} characters!")
        return False

    print(f"\n✅ Message fits! Using {(total_needed / capacity * 100):.1f}% of image capacity.")
    return True


# ══════════════════════════════════════════════════════════════════
#  SECTION 4 — CORE ENCODER
# ══════════════════════════════════════════════════════════════════

def encode_image(image: np.ndarray, message: str) -> np.ndarray:
    """
    Hide `message` inside `image` using LSB steganography.

    Algorithm:
      1. Append delimiter to message so decoder knows where to stop.
      2. Convert full payload to binary string.
      3. Iterate through pixel channels (R→G→B→next pixel→...).
      4. Replace the LSB of each channel value with one message bit.
      5. Return modified image (looks identical to original).

    Args:
        image   (np.ndarray): Original cover image (BGR, uint8).
        message (str)       : Secret text to hide.

    Returns:
        np.ndarray: Encoded image with hidden message.

    Raises:
        ValueError: If message is too large for the image.
    """
    # Step 1: Capacity check
    if not check_capacity(image, message):
        raise ValueError("Message is too large for the selected image.")

    # Step 2: Build full binary payload (message + delimiter)
    full_message   = message + DELIMITER
    binary_payload = text_to_binary(full_message)
    payload_len    = len(binary_payload)

    print(f"\n🔐 ENCODING")
    print(f"   Binary payload length : {payload_len} bits")

    # Step 3: Work on a copy so we don't modify the original
    encoded_image = image.copy()

    # Flatten image to a 1D array of channel values for easy indexing
    # Shape: (H, W, 3) → (H*W*3,)
    flat = encoded_image.flatten()

    # Step 4: Embed each bit into the LSB of consecutive channel values
    for i, bit in enumerate(binary_payload):
        # Clear the LSB of flat[i] using AND with 0b11111110 (254)
        # Then set it to our message bit using OR
        flat[i] = (flat[i] & 0b11111110) | int(bit)

    # Step 5: Reshape back to original image dimensions
    encoded_image = flat.reshape(image.shape)

    print(f"   Pixels modified       : {payload_len // 3 + 1}")
    print(f"   ✅ Encoding complete!")

    return encoded_image


# ══════════════════════════════════════════════════════════════════
#  SECTION 5 — CORE DECODER
# ══════════════════════════════════════════════════════════════════

def decode_image(image: np.ndarray) -> str:
    """
    Extract hidden message from a steganographically encoded image.

    Algorithm:
      1. Flatten image to 1D channel array.
      2. Read the LSB from each channel value, building a binary string.
      3. Every 8 bits → convert to one character.
      4. Stop when the delimiter "#####" is found in decoded text.
      5. Return the message before the delimiter.

    Args:
        image (np.ndarray): Encoded image (BGR, uint8).

    Returns:
        str: Extracted hidden message (without delimiter).

    Raises:
        ValueError: If no delimiter found (image may not be encoded).
    """
    print("\n🔓 DECODING")

    flat       = image.flatten()
    binary_str = ""
    decoded    = ""

    for i in range(len(flat)):
        # Extract LSB from this channel value
        binary_str += str(flat[i] & 1)

        # Every 8 bits, decode one character
        if len(binary_str) % 8 == 0:
            byte = binary_str[-8:]           # Last 8 bits
            char = chr(int(byte, 2))
            decoded += char

            # Check if we've hit the delimiter
            if decoded.endswith(DELIMITER):
                message = decoded[:-len(DELIMITER)]   # Strip delimiter
                print(f"   Bits read    : {len(binary_str)}")
                print(f"   Chars found  : {len(message)}")
                print(f"   ✅ Decoding complete!")
                return message

    raise ValueError(
        "No hidden message found. "
        "Make sure you are using the encoded image and it was saved as PNG."
    )


# ══════════════════════════════════════════════════════════════════
#  SECTION 6 — FILE I/O HELPERS
# ══════════════════════════════════════════════════════════════════

def load_image(path: str) -> np.ndarray:
    """
    Load an image from disk using OpenCV.

    Args:
        path (str): File path to the image.

    Returns:
        np.ndarray: Loaded image in BGR format.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError       : If OpenCV cannot read the file.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Image not found: '{path}'")

    image = cv2.imread(path)

    if image is None:
        raise ValueError(
            f"OpenCV could not read '{path}'. "
            "Ensure it is a valid image file (PNG, JPG, BMP, etc.)."
        )

    print(f"📂 Loaded image : '{path}'  [{image.shape[1]}×{image.shape[0]} px, {image.shape[2]} channels]")
    return image


def save_image(image: np.ndarray, output_path: str = "encoded.png") -> None:
    """
    Save image to disk as PNG (lossless — required for steganography).

    IMPORTANT: Always save as PNG. JPEG compression alters pixel values
    and will corrupt the hidden message!

    Args:
        image       (np.ndarray): Image array to save.
        output_path (str)       : Destination file path.
    """
    if not output_path.lower().endswith(".png"):
        output_path = os.path.splitext(output_path)[0] + ".png"
        print(f"⚠️  Output format changed to PNG: '{output_path}'")

    cv2.imwrite(output_path, image)
    print(f"💾 Saved encoded image : '{output_path}'")


# ══════════════════════════════════════════════════════════════════
#  SECTION 7 — VISUAL DIFFERENCE ANALYSIS
# ══════════════════════════════════════════════════════════════════

def compare_images(original: np.ndarray, encoded: np.ndarray) -> None:
    """
    Print statistics comparing original vs encoded image.

    Shows how minimal the changes are — confirming near-zero distortion.

    Args:
        original (np.ndarray): Original cover image.
        encoded  (np.ndarray): Steganographically modified image.
    """
    diff        = np.abs(original.astype(int) - encoded.astype(int))
    max_diff    = diff.max()
    mean_diff   = diff.mean()
    changed_px  = np.count_nonzero(diff)

    print("\n🔍 DISTORTION ANALYSIS")
    print(f"   Max pixel difference  : {max_diff}  (should be 1)")
    print(f"   Mean pixel difference : {mean_diff:.6f}  (near-zero)")
    print(f"   Changed channel values: {changed_px}")
    print(f"   Total channel values  : {original.size}")
    print(f"   % pixels changed      : {changed_px / original.size * 100:.4f}%")
    print(f"   Human eye detectable  : {'NO ✅' if max_diff <= 1 else 'POSSIBLY ⚠️'}")


# ══════════════════════════════════════════════════════════════════
#  SECTION 8 — MAIN DEMO (Run directly)
# ══════════════════════════════════════════════════════════════════

def run_demo():
    """
    Full demonstration: encode a message into a generated test image,
    save it, reload it, decode the message, and verify correctness.
    """
    print("=" * 60)
    print("  IMAGE STEGANOGRAPHY DEMO — LSB Method")
    print("=" * 60)

    # ── Create a synthetic test image (500×500 random pixels) ──
    # In real use: replace with load_image("your_photo.png")
    print("\n🎨 Creating synthetic test image (500×500)...")
    test_image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)

    # ── Secret message (multi-line supported) ──
    secret_message = (
        "Hello, World!\n"
        "This is a secret message hidden using LSB steganography.\n"
        "Line 3: You can't see me in the image!\n"
        "Line 4: NumPy + OpenCV = 🔐"
    )

    print(f"\n📝 SECRET MESSAGE:\n{'-'*40}")
    print(secret_message)
    print('-' * 40)

    # ── Optional: XOR encrypt before hiding ──
    XOR_KEY   = 42          # Change to 0 to disable encryption
    USE_XOR   = True

    if USE_XOR and XOR_KEY != 0:
        payload = xor_encrypt(secret_message, XOR_KEY)
        print(f"\n🔑 XOR encryption applied (key={XOR_KEY})")
    else:
        payload = secret_message

    # ── Encode ──
    encoded_image = encode_image(test_image, payload)

    # ── Save as PNG ──
    output_path = "encoded.png"
    save_image(encoded_image, output_path)

    # ── Compare original vs encoded ──
    compare_images(test_image, encoded_image)

    # ── Reload from disk (simulates real-world usage) ──
    print(f"\n📂 Reloading '{output_path}' from disk...")
    reloaded = cv2.imread(output_path)

    # ── Decode ──
    extracted_payload = decode_image(reloaded)

    # ── Optional: XOR decrypt ──
    if USE_XOR and XOR_KEY != 0:
        extracted_message = xor_encrypt(extracted_payload, XOR_KEY)  # XOR is its own inverse
        print(f"   🔑 XOR decryption applied (key={XOR_KEY})")
    else:
        extracted_message = extracted_payload

    # ── Verify ──
    print(f"\n📝 DECODED MESSAGE:\n{'-'*40}")
    print(extracted_message)
    print('-' * 40)

    match = (extracted_message == secret_message)
    print(f"\n{'✅ VERIFICATION PASSED' if match else '❌ VERIFICATION FAILED'}: "
          f"Decoded message {'matches' if match else 'does NOT match'} original.")
    print("\n" + "=" * 60)


# ══════════════════════════════════════════════════════════════════
#  SECTION 9 — COMMAND LINE INTERFACE
# ══════════════════════════════════════════════════════════════════

def parse_args():
    """Set up command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Image Steganography Tool — Hide text inside images using LSB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  # Run built-in demo (no arguments needed):
  python steganography.py

  # Encode a message into an image:
  python steganography.py --mode encode --image photo.png --message "My secret"

  # Encode with XOR encryption (key=99):
  python steganography.py --mode encode --image photo.png --message "Secret" --xor 99

  # Encode with Caesar cipher (shift=13):
  python steganography.py --mode encode --image photo.png --message "Secret" --caesar 13

  # Decode from an encoded image:
  python steganography.py --mode decode --image encoded.png

  # Decode with XOR decryption:
  python steganography.py --mode decode --image encoded.png --xor 99
        """
    )

    parser.add_argument(
        "--mode", choices=["encode", "decode"], default=None,
        help="Operation mode: 'encode' to hide a message, 'decode' to extract one."
    )
    parser.add_argument(
        "--image", type=str, default=None,
        help="Path to the input image file (PNG recommended)."
    )
    parser.add_argument(
        "--message", type=str, default=None,
        help="Secret message to hide (for encode mode). Supports multi-line via \\n."
    )
    parser.add_argument(
        "--output", type=str, default="encoded.png",
        help="Output path for encoded image (default: encoded.png)."
    )
    parser.add_argument(
        "--xor", type=int, default=0,
        help="XOR cipher key (0–255). Use same key for encode and decode."
    )
    parser.add_argument(
        "--caesar", type=int, default=0,
        help="Caesar cipher shift value. Use same shift for encode and decode."
    )

    return parser.parse_args()


def main():
    args = parse_args()

    # No arguments → run the built-in demo
    if args.mode is None:
        run_demo()
        return

    # ── ENCODE MODE ──
    if args.mode == "encode":
        if not args.image or not args.message:
            print("❌ Encode mode requires --image and --message arguments.")
            sys.exit(1)

        image   = load_image(args.image)
        message = args.message.replace("\\n", "\n")  # Allow \n in CLI args

        # Apply encryption if requested
        if args.xor != 0:
            message = xor_encrypt(message, args.xor)
            print(f"🔑 XOR encryption applied (key={args.xor})")
        elif args.caesar != 0:
            message = caesar_encrypt(message, args.caesar)
            print(f"🔑 Caesar cipher applied (shift={args.caesar})")

        encoded = encode_image(image, message)
        save_image(encoded, args.output)
        compare_images(image, encoded)

    # ── DECODE MODE ──
    elif args.mode == "decode":
        if not args.image:
            print("❌ Decode mode requires --image argument.")
            sys.exit(1)

        image   = load_image(args.image)
        payload = decode_image(image)

        # Apply decryption if requested
        if args.xor != 0:
            payload = xor_encrypt(payload, args.xor)     # XOR is its own inverse
            print(f"🔑 XOR decryption applied (key={args.xor})")
        elif args.caesar != 0:
            payload = caesar_decrypt(payload, args.caesar)
            print(f"🔑 Caesar decryption applied (shift={args.caesar})")

        print(f"\n📝 HIDDEN MESSAGE:\n{'-'*40}")
        print(payload)
        print('-' * 40)


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()
