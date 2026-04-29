"""
StegApp – Flask application
Key fix: file secrets are now stored as raw encrypted bytes inside the steg
image, not as base64-encoded strings. This eliminates the ~33% size overhead
and the slow Python string operations that caused long encode times.

Binary wire format embedded in the steg image:
  - Text secret: encrypt_message(text, pw)  → Fernet token (bytes)
  - File secret : [1-byte type=0x02][2-byte name_len][name_bytes][encrypt_bytes(file_data, pw)]

The type byte lets decode() distinguish text (Fernet starts with 'gAAAAA')
from a binary file payload, without any string parsing overhead.
"""

from flask import Flask, render_template, request, send_file, jsonify
import os
import struct
import uuid
import io
from werkzeug.utils import secure_filename

from utils.crypto_utils import encrypt_message, decrypt_message, encrypt_bytes, decrypt_bytes
import steg_engine as steg

app = Flask(__name__)

# =============================
# Folder setup
# =============================
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}

ALLOWED_SECRET_EXTENSIONS = {
    "jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff",
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "txt", "csv", "rtf", "odt", "ods", "odp",
    "mp3", "wav", "aac", "flac", "ogg",
    "mp4", "avi", "mov", "mkv", "webm",
    "zip", "rar", "7z", "tar", "gz",
    "json", "xml", "html", "css", "js", "py",
}

# Short link storage (in-memory; fine for demo)
link_map = {}

# Marker byte: distinguishes a binary file payload from a plain Fernet text token.
# Fernet tokens always start with 'gAAAAA' (ASCII 0x67), so 0x02 is unambiguous.
_FILE_MAGIC = b'\x02'


# =============================
# Helpers
# =============================
def allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def allowed_secret(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_SECRET_EXTENSIONS


def _pack_file_payload(original_filename: str, encrypted_data: bytes) -> bytes:
    """
    Pack a binary file payload:
      [0x02][2-byte name_len LE][name UTF-8][encrypted_data]
    """
    name_bytes = original_filename.encode("utf-8")[:65535]
    return _FILE_MAGIC + struct.pack("<H", len(name_bytes)) + name_bytes + encrypted_data


def _unpack_file_payload(raw: bytes) -> tuple:
    """
    Unpack a binary file payload.
    Returns (original_filename: str, encrypted_data: bytes).
    """
    if not raw.startswith(_FILE_MAGIC):
        raise ValueError("Not a binary file payload.")
    name_len = struct.unpack("<H", raw[1:3])[0]
    name_bytes = raw[3: 3 + name_len]
    encrypted_data = raw[3 + name_len:]
    return name_bytes.decode("utf-8"), encrypted_data


# =============================
# Pages
# =============================
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/encode")
def encode_page():
    return render_template("encode.html")


@app.route("/decode")
def decode_page():
    return render_template("decode.html")


# =============================
# Encode action
# =============================
@app.route("/encode_action", methods=["POST"])
def encode_action():

    image_source = request.form.get("image_source")
    secret_type  = request.form.get("secret_type", "text")   # "text" or "file"
    password     = request.form.get("password")

    if not image_source or not password:
        return jsonify({"error": "Missing required fields"}), 400

    # ── Resolve cover image ────────────────────────────────────────────────────
    if image_source == "sample":
        sample = request.form.get("sample_img")
        if not sample:
            return jsonify({"error": "No sample image selected"}), 400
        image_path = os.path.join("static", "sample_images", sample)
        with open(image_path, "rb") as f:
            cover_bytes = f.read()
    else:
        if "image" not in request.files:
            return jsonify({"error": "No image uploaded"}), 400
        img_file = request.files["image"]
        if img_file.filename == "":
            return jsonify({"error": "Empty filename"}), 400
        if not allowed_image(img_file.filename):
            return jsonify({"error": "Invalid image type (PNG/JPG only)"}), 400
        cover_bytes = img_file.read()

    # ── Build secret payload ───────────────────────────────────────────────────
    if secret_type == "file":
        if "secret_file" not in request.files:
            return jsonify({"error": "No secret file uploaded"}), 400
        secret_file = request.files["secret_file"]
        if secret_file.filename == "":
            return jsonify({"error": "Empty secret filename"}), 400
        if not allowed_secret(secret_file.filename):
            return jsonify({"error": "That file type is not allowed as a secret"}), 400

        original_filename = secure_filename(secret_file.filename)
        raw_secret = secret_file.read()

        # Encrypt raw bytes directly — no base64, no string conversion
        encrypted_data = encrypt_bytes(raw_secret, password)

        # Pack into our binary wire format
        steg_payload = _pack_file_payload(original_filename, encrypted_data)
        steg_filename_hint = original_filename

    else:
        # Plain text — unchanged behaviour
        message = request.form.get("message", "")
        if not message:
            return jsonify({"error": "Message is empty"}), 400
        # encrypt_message returns Fernet bytes (starts with b'gAAAAA...')
        steg_payload = encrypt_message(message, password)
        steg_filename_hint = "message.txt"

    # ── Encode into image ──────────────────────────────────────────────────────
    try:
        steg_bytes = steg.encode(
            cover_image_bytes=cover_bytes,
            secret_bytes=steg_payload if isinstance(steg_payload, bytes) else steg_payload,
            filename=steg_filename_hint,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # ── Save output ────────────────────────────────────────────────────────────
    file_id         = uuid.uuid4().hex
    short_id        = file_id[:6]
    output_filename = f"{file_id}.png"
    output_path     = os.path.join(UPLOAD_FOLDER, output_filename)

    with open(output_path, "wb") as f:
        f.write(steg_bytes)

    link_map[short_id] = output_filename
    share_url = request.host_url + "s/" + short_id

    return jsonify({"share_url": share_url})


# =============================
# Decode action
# =============================
@app.route("/decode_action", methods=["POST"])
def decode_action():

    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    password = request.form.get("password")
    if not password:
        return jsonify({"error": "Password required"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    steg_bytes = file.read()

    try:
        _, raw_payload = steg.decode(steg_bytes)
    except Exception:
        return jsonify({"error": "Wrong password or corrupted / non-steg image."}), 400

    # ── Determine payload type ────────────────────────────────────────────────
    if raw_payload.startswith(_FILE_MAGIC):
        # Binary file payload (new format)
        try:
            original_name, encrypted_data = _unpack_file_payload(raw_payload)
            raw_bytes = decrypt_bytes(encrypted_data, password)
        except Exception:
            return jsonify({"error": "Wrong password or corrupted file payload."}), 400

        dl_id       = uuid.uuid4().hex
        dl_filename = f"{dl_id}_{secure_filename(original_name)}"
        dl_path     = os.path.join(UPLOAD_FOLDER, dl_filename)
        with open(dl_path, "wb") as f:
            f.write(raw_bytes)

        return jsonify({
            "type":     "file",
            "filename": original_name,
            "dl_path":  dl_filename,
        })

    elif raw_payload.startswith(b"FILE:"):
        # Legacy base64 format (backwards compat for images encoded with old app)
        import base64
        try:
            decrypted = decrypt_message(raw_payload, password)
        except Exception:
            return jsonify({"error": "Wrong password or corrupted / non-steg image."}), 400

        parts = decrypted.split(":", 2)
        if len(parts) != 3:
            return jsonify({"error": "Corrupted file payload."}), 400

        original_name = parts[1]
        raw_bytes     = base64.b64decode(parts[2])

        dl_id       = uuid.uuid4().hex
        dl_filename = f"{dl_id}_{secure_filename(original_name)}"
        dl_path     = os.path.join(UPLOAD_FOLDER, dl_filename)
        with open(dl_path, "wb") as f:
            f.write(raw_bytes)

        return jsonify({
            "type":     "file",
            "filename": original_name,
            "dl_path":  dl_filename,
        })

    else:
        # Plain text (Fernet token)
        try:
            decrypted = decrypt_message(raw_payload, password)
        except Exception:
            return jsonify({"error": "Wrong password or corrupted / non-steg image."}), 400

        return jsonify({
            "type":    "text",
            "message": decrypted,
        })


# =============================
# Download decoded file
# =============================
@app.route("/download_decoded/<filename>")
def download_decoded(filename):
    safe = secure_filename(filename)
    path = os.path.join(UPLOAD_FOLDER, safe)
    if not os.path.exists(path):
        return "File not found", 404
    original_name = "_".join(safe.split("_")[1:]) or safe
    return send_file(path, as_attachment=True, download_name=original_name)


# =============================
# Short share link
# =============================
@app.route("/s/<short_id>")
def short_redirect(short_id):
    filename = link_map.get(short_id)
    if not filename:
        return "Invalid or expired link", 404
    return render_template("share.html", filename=filename)


# =============================
# Download encoded steg image
# =============================
@app.route("/download/<filename>")
def download_file(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(path):
        return "File not found", 404
    return send_file(
        path,
        mimetype="image/png",
        as_attachment=True,
        download_name=filename,
    )


# =============================
# Run server
# =============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)