# -*- coding: utf-8 -*-
import urllib.request

from PIL import Image
from pyzbar.pyzbar import decode


def decode_qr_from_image(image_path):
    try:
        img = Image.open(image_path)
        decoded = decode(img)
        if decoded:
            for obj in decoded:
                url = obj.data.decode('utf-8')
                if url.startswith('http'):
                    return url
        return None
    except Exception as e:
        print(f"QR decode error: {e}")
        return None


def download_pdf_from_url(url, save_path):
    try:
        urllib.request.urlretrieve(url, save_path)
        return True
    except Exception as e:
        print(f"Download error: {e}")
        return False
