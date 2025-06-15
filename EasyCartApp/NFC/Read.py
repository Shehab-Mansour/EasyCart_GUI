import time
import board
import busio
from digitalio import DigitalInOut
from adafruit_pn532.i2c import PN532_I2C

# Initialize I2C connection
i2c = busio.I2C(board.SCL, board.SDA)
reset_pin = DigitalInOut(board.D24)
req_pin = DigitalInOut(board.D25)

pn532 = PN532_I2C(i2c, reset=reset_pin, req=req_pin, debug=False)
pn532.SAM_configuration()

key_a = b"\xFF\xFF\xFF\xFF\xFF\xFF"

def read_card_text():
#     print("Waiting for NFC card...")
    while True:
        uid = pn532.read_passive_target(timeout=0.5)
        if not uid:
            continue

#         print("Found card with UID:", [hex(i) for i in uid])
        text_blocks = []

        if len(uid) == 4:  # Mifare Classic
            for block_num in [4, 5, 6]:
                try:
                    if pn532.mifare_classic_authenticate_block(uid, block_num, 0x61, key_a):
                        data = pn532.mifare_classic_read_block(block_num)
                        if data:
                            text = "".join(chr(x) for x in data if 32 <= x <= 126).strip()
                            text_blocks.append(text)
                except Exception as e:
                    print(f"Block {block_num} error:", e)

        elif len(uid) == 7:  # NTAG
            for page_num in [4, 5, 6]:
                try:
                    data = pn532.ntag2xx_read_block(page_num)
                    if data:
                        text = "".join(chr(x) for x in data if 32 <= x <= 126).strip()
                        text_blocks.append(text)
                except Exception as e:
                    print(f"Page {page_num} error:", e)
        else:
            print("Unknown card type")
            return None

        result = " ".join(t for t in text_blocks if t)
        print(result)
        return result if result else None

# read_card_text()