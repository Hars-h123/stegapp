from PIL import Image


def encode_image(input_path, secret_data, output_path):
    image = Image.open(input_path).convert("RGB")
    pixels = image.load()

    width, height = image.size

    # Convert secret to binary
    binary_secret = ''.join(format(byte, '08b') for byte in secret_data)
    binary_secret += '11111110'  # End delimiter

    data_index = 0
    data_len = len(binary_secret)

    for y in range(height):
        for x in range(width):
            if data_index >= data_len:
                break

            r, g, b = pixels[x, y]

            if data_index < data_len:
                r = (r & ~1) | int(binary_secret[data_index])
                data_index += 1

            if data_index < data_len:
                g = (g & ~1) | int(binary_secret[data_index])
                data_index += 1

            if data_index < data_len:
                b = (b & ~1) | int(binary_secret[data_index])
                data_index += 1

            pixels[x, y] = (r, g, b)

        if data_index >= data_len:
            break

    image.save(output_path)
    image.close()


def decode_image(image_path):
    image = Image.open(image_path).convert("RGB")
    pixels = image.load()

    width, height = image.size

    binary_data = ""
    delimiter = "11111110"

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]

            binary_data += str(r & 1)
            binary_data += str(g & 1)
            binary_data += str(b & 1)

            if delimiter in binary_data:
                binary_data = binary_data.split(delimiter)[0]
                image.close()
                return bytes(
                    int(binary_data[i:i+8], 2)
                    for i in range(0, len(binary_data), 8)
                )

    image.close()
    return b""