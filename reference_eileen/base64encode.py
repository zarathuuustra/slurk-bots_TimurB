import base64

def encode_image_to_base64(image_path):
    """ Encodes images to 64 bits
    """
    try:
        with open(image_path, 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read())
            return encoded_string.decode('utf-8')  # Convert bytes to a UTF-8 string
    except FileNotFoundError:
        return None