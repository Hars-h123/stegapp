from PIL import Image


def encode_image(input_path, secret_data, output_path):
    image = Image.open(input_path)
    image = image.convert("RGB")

    encoded = image.copy()
    index = 0

    # Convert secret data to binary
    binary_secret = ''.join(format(byte, '08b') for byte in secret_data)
    binary_secret += '11111110'  # End delimiter

    pixels = list(encoded.getdata())
    new_pixels = []

    for i, pixel in enumerate(pixels):
        r, g, b = pixel

        if index < len(binary_secret):
            r = (r & ~1) | int(binary_secret[index])
            index += 1

        if index < len(binary_secret):
            g = (g & ~1) | int(binary_secret[index])
            index += 1

        if index < len(binary_secret):
            b = (b & ~1) | int(binary_secret[index])
            index += 1

        new_pixels.append((r, g, b))

        # 🚀 STOP early once secret is fully embedded
        if index >= len(binary_secret):
            new_pixels.extend(pixels[i+1:])
            break

    encoded.putdata(new_pixels)
    encoded.save(output_path)
    
def decode_image(image_path):
    from PIL import Image

    image = Image.open(image_path)
    image = image.convert("RGB")

    pixels = list(image.getdata())

    binary_data = ""
    delimiter = "1111111111111110"

    for pixel in pixels:
        r, g, b = pixel

        binary_data += str(r & 1)
        binary_data += str(g & 1)
        binary_data += str(b & 1)

        # STOP as soon as delimiter appears
        if delimiter in binary_data:
            binary_data = binary_data.split(delimiter)[0]
            break

    # Convert to bytes
    all_bytes = [binary_data[i:i+8] for i in range(0, len(binary_data), 8)]

    decoded_bytes = bytearray()

    for byte in all_bytes:
        if len(byte) == 8:
            decoded_bytes.append(int(byte, 2))

    return bytes(decoded_bytes)