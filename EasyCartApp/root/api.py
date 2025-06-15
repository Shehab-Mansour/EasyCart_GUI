
EasyCartID="EasyCart001"
import requests
from urllib.parse import quote
from tkinter.messagebox import showinfo, showerror
from flask import Flask, request, jsonify
token=None
carts = {}
BASE_URL = "https://shehab123.pythonanywhere.com"
_token = None

session = requests.Session()
refresh_token = None

def login_user(username, password):
    global refresh_token
    url = f"{BASE_URL}/user/login/"
    payload = {
        "username": username,
        "password": password
    }
    response = session.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        access_token = data.get("access")
        refresh_token = data.get("refresh")
        if access_token and refresh_token:
            session.headers.update({"Authorization": f"Bearer {access_token}"})
            return data
        else:
            raise Exception("Missing access or refresh token in response.")

    else:
        raise Exception(f"Login failed: {response.status_code} - {response.text}")


def logout_user():
    global refresh_token
    if not refresh_token:
        print("? No refresh token available. User is likely not logged in.")
        return
    url = f"{BASE_URL}/user/logout/"
    payload = {
        "refresh": refresh_token
    }
    try:
        response = session.delete(url, json=payload)
        if response.status_code in [200, 205]:
            print("? Logged out successfully.")
            session.headers.pop("Authorization", None)
            refresh_token = None
        else:
            raise Exception(f"Logout failed: {response.status_code} - {response.text}")
    except Exception as e:
        print("? Error during logout:", str(e))


def get_profile():
    url = "https://shehab123.pythonanywhere.com/user/profile/"
    response = requests.get(url, headers=session.headers)
    if response.status_code == 200:
        return response.json()
    else:
        return None

def refresh_access_token(refresh_token):
    url = f"{BASE_URL}/token/refresh/"
    data = {"refresh": refresh_token}
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return response.json().get("access")
    else:
        print("??? ????? ??????? ??? ????? ?????? ??????.")
        return None

def add_to_wishlist(qr_number):
    url = f"{BASE_URL}/product/wishlist/add/{qr_number}/"
    response = requests.post(url)
    if response.status_code in (200, 201):
        print(f"? ?????? ???? QR {qr_number} ?? ?????? ??? ????????.")
        return True
    else:
        print(f"? ??? ?? ???????:\n{response.status_code} - {response.text}")
        return False


def remove_from_wishlist(QrNumber):
    url = f"{BASE_URL}/product/wishlist/remove/{QrNumber}/"
    response = requests.delete(url)
    if response.status_code == 200 or response.status_code == 204:
        print(f"? ?????? ???? QR {QrNumber} ?? ?????? ?? ????????.")
        return True
    else:
        print(f"? ??? ?? ?????:\n{response.status_code} - {response.text}")
        return False

def set_token(token):
    global _token
    _token = token

def get_token():
    return _token

def get_all_products():
    try:
        product_url = f"{BASE_URL}/product/getall/"
        response = requests.get(product_url)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception("Failed to fetch products")
    except Exception as e:
        print("Error fetching products:", e)
        return []


def open_product_details():
    url = f"{BASE_URL}/product/getall/"
    response = requests.get(url)
    if response.status_code == 200:
        product = response.json()
    else:
        print("Failed to load product details")
#
# def show_product_info(product):
#     print(f"Name: {product['ProductName']}")
#     print(f"Price: {product['ProductPrice']}")
#     print(f"Category: {product['ProductCategory']}")
#     print(f"Description: {product['ProductDescription']}")

def search_products(category=None, product=None):
    try:
        url = f"{BASE_URL}/product/search/"
        payload = {}
        if category:
            payload["category"] = category
        elif product:
            payload["product"] = product
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            print("Error:", response.status_code, response.text)
            return []
    except Exception as e:
        print("Exception:", str(e))
        return []


def send_checkout_request():
    url = f"{BASE_URL}/cart/EasyCartchechout/"
    payload = {
        "user_id": 12,
        "total_price": 80
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # ????? ?? ???? ???? (??? 200-299)
        return response.json()
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        return None

def send_scan_data(cart_qr_number, beginning_weight, location, api_url):
    data = {
        "CartQRNumber": cart_qr_number,
        "beginningWeight": beginning_weight,
        "location": location
    }
    try:
        response = requests.post(api_url, json=data)
        if response.status_code in (200, 201):
            showinfo(title="Success", message="Scan data sent successfully!")
        else:
            showerror(title="Failed", message=f"Server responded with status code {response.status_code}")
    except requests.exceptions.RequestException as e:
        showerror(title="Error", message=f"Connection failed: {str(e)}")


def register_user(username, first_name, last_name, email, password):
    url = f"{BASE_URL}/user/register/"
    data = {
        "clientUserName": username,
        "clientFirstName": first_name,
        "clientLastName": last_name,
        "clientEmail": email,
        "clientPassword": password
    }
    response = requests.post(url, json=data)
    if response.status_code in [200, 201]:
        return response.json()
    else:
        try:
            error_json = response.json()
            error_message = error_json.get("error") or error_json.get("detail") or response.text
        except Exception:
            error_message = response.text
        raise Exception(f"Registration failed: {error_message}")


def verify_user(code):
    url = f"{BASE_URL}/user/verify/"
    payload = {
        "verificationCode": code
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        showerror(title="Verification Error", message=f"Verification failed: {e}")
        return {"error": str(e)}

def get_wishlist(user_token):
    headers = {
        "Authorization": "Bearer YOUR_VALID_USER_TOKEN",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(f"{BASE_URL}/product/wishlist/getmywish/", headers=headers)
        response.raise_for_status()
        wishlist = response.json().get("wishlist", [])
        return wishlist
    except requests.exceptions.HTTPError as err:
        print(f"Error fetching wishlist: {err}")
        return []

def get_categories():
    try:
        response = requests.get(f"{BASE_URL}/product/categories/")
        categories = response.json()
        return categories
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return []
def get_products_by_category_by_name(category_name):
    url = f"{BASE_URL}/product/in/{category_name}/"
    response = requests.get(url)
    response.raise_for_status()  # ???? ????? ?? ??? ??? ?????
    return response.json()
def get_category_details(category_name):
    url = f"{BASE_URL}/product/categories/{category_name}/details/"
    try:
        response = requests.get(url)
        response.raise_for_status()  # ??? ????? ???? ??????? ?? ????? ???
        return response.json()       # ???? ???????? ????? JSON (???? dict)
    except requests.RequestException as e:
        print(f"Error fetching category details: {e}")
        return {"error": str(e)}

def get_product_image(image_path):
    full_url = BASE_URL + image_path
    response = requests.get(full_url)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception("Failed to load image")


def fetch_wishlist():
    try:
        url = f"{BASE_URL}/product/wishlist/getmywish/"  # ???????? ??????? ???????
        response = requests.get(url)
        if response.status_code == 200:
            wishlist_data = response.json()
            return wishlist_data
        else:
            print("Failed to fetch wishlist:", response.status_code)
            return []
    except Exception as e:
        print("Error fetching wishlist:", e)
        return []






####################################  DIS #########################
# def extract_cart_data(json_data):
#     virtual_products = []
#     picked_products = []
#     print("in extract_cart_data")
#     # EasyCartVirtualItems (???? ??? ?? ?????)
#     for cart in json_data.get("EasyCartVirtualItems", []):
#         for item in cart.get("items", {}).values():
#             product = item["product"]
#             name = product.get("ProductName", "Unknown")
#             place_str = product.get("ProductPlace", "[0,0]")
#             try:
#                 x, y = eval(place_str)
#             except:
#                 x, y = 0, 0
#             virtual_products.append({
#                 "name": name,
#                 "x": float(x),
#                 "y": float(y),
#                 "total_price": item.get("total_price", 0),
#                 "image": product.get("ProductImage", "")
#             })
#
#     # EasyCartItems (???? ?????? ?? ??????)
#     for cart in json_data.get("EasyCartItems", []):
#         for item in cart.get("items", {}).values():
#             product = item["product"]
#             name = product.get("ProductName", "Unknown")
#             picked_products.append({
#                 "name": name,
#                 "total_price": item.get("total_price", 0),
#                 "image": product.get("ProductImage", "")
#             })
#     print("out of extract_cart_data")
#     return virtual_products, picked_products
#

def extract_cart_data(json_data):
    virtual_products = []
    picked_products = []

    # First ensure json_data is a dictionary
    if not isinstance(json_data, dict):
        print("Error: json_data is not a dictionary")
        return virtual_products, picked_products

    # Process EasyCartVirtualItems
    virtual_carts = json_data.get("EasyCartVirtualItems", [])
    if not isinstance(virtual_carts, list):
        virtual_carts = []

    for cart in virtual_carts:
        if not isinstance(cart, dict):
            continue

        items = cart.get("items", {})
        if not isinstance(items, dict):
            continue

        for item in items.values():
            if not isinstance(item, dict):
                continue

            product = item.get("product", {})
            if not isinstance(product, dict):
                continue

            name = product.get("ProductName", "Unknown")
            place_str = product.get("ProductPlace", "[0,0]")
            try:
                x, y = eval(place_str)
            except:
                x, y = 0, 0

            virtual_products.append({
                "name": name,
                "x": float(x),
                "y": float(y),
                "total_price": item.get("total_price", 0),
                "image": product.get("ProductImage", "")
            })

    # Process EasyCartItems
    picked_carts = json_data.get("EasyCartItems", [])
    if not isinstance(picked_carts, list):
        picked_carts = []

    for cart in picked_carts:
        if not isinstance(cart, dict):
            continue

        items = cart.get("items", {})
        if not isinstance(items, dict):
            continue

        for item in items.values():
            if not isinstance(item, dict):
                continue

            product = item.get("product", {})
            if not isinstance(product, dict):
                continue

            picked_products.append({
                "name": product.get("ProductName", "Unknown"),
                "total_price": item.get("total_price", 0),
                "image": product.get("ProductImage", "")
            })

    return virtual_products, picked_products


def cart_cheek_in(QR):
    url = f"{BASE_URL}/cart/EsyCartCheckIn/"
    payload = {
        "CartQRNumber": QR,
        "beginningWeight": 1,
        "location": "[70,115]"
    }
    headers = {
        "Authorization": EasyCartID,
    }
    response = session.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        data = response.json()
        access_token = data["access"]
        session.headers.update({"Authorization": f"Bearer {access_token}"})
        print(access_token)
        return get_cart_items()
    else:
        raise Exception(response.json())


def get_cart_items():
    url = f"{BASE_URL}/cart/EasyCartItems/"
    response = requests.get(url, headers=session.headers)
    if response.status_code != 200:
        print("Failed to retrieve cart items")
        products = []
        picked_items=[]
        return products, picked_items

    cart_json = response.json()
    products, picked_items = extract_cart_data(cart_json)

    if not products:
        products=[]
    return products, picked_items


