import tkinter as tk
import platform
from CTkMessagebox import CTkMessagebox
import customtkinter as ctk
import json
import functools
import math
import socket
from customtkinter import CTkImage
from tkinter import Tk, messagebox
import threading
from PIL import Image, ImageTk
import os
import io
from io import BytesIO
from root import api
from pyzbar import pyzbar
import cv2
import requests
from AStar.GIS import find_nearest_walkable, sort_points_by_path_distance, calculate_total_path, draw_path_with_arrows
from pycamera2 import Picamera2
import time
from app.ai_core import EasyCartAICore
import sqlite3
from NFC.Read import read_card_text


camera_running = False
picam2_instance = None

BASE_URL = "https://shehab123.pythonanywhere.com"

page_size = 5
app = ctk.CTk()
app.title("Cart Program")
app.geometry("1080x600")
app.configure(fg_color="white")
ctk.set_default_color_theme("green")

img_path = ["photos/download18.jpeg",
            "photos/download19.jpeg",
            "photos/download20.jpeg",
            "photos/product_design.jpeg"]
img_index = 0
img_label = ctk.CTkLabel(app, text="")
img_label.pack(expand=False)

def ensure_camera_closed():
    global camera_running, picam2_instance
    if camera_running and picam2_instance is not None:
        try:
            picam2_instance.stop()
            picam2_instance.close()
            picam2_instance = None
            camera_running = False
        except Exception as e:
            print(f"Error stopping camera in next_page: {e}")


def clear_screen():
    ensure_camera_closed()
    for widget in app.winfo_children():
        try:
            widget.place_forget()
            widget.pack_forget()
        except AttributeError:
            continue
def clear_screen2():
    # ensure_camera_closed()
    for widget in app.winfo_children():
        try:
            widget.place_forget()
            widget.pack_forget()
        except AttributeError:
            continue


class AppState:
    def __init__(self):
        self.products = []
        self.picked_items = []
        self.cart_position = (70, 115)
        self.user_access_token = None
        self.user_refresh_token = None
        self.cart_data = None
    def save_state(self):
        pass

app_state = AppState()

def render_sidebar():
    def on_enter(event, button):
        button.configure(text_color="white", fg_color="dark green")

    def on_leave(event, button):
        button.configure(text_color="green", fg_color="white")

    frame_width = 200
    frame = ctk.CTkFrame(app, width=frame_width, height=600, fg_color="white",
                         border_color="green", border_width=1)
    frame.place(x=0, y=0)

    # Logo
    ctk.CTkLabel(frame, text="Easy", font=("Times New Roman", 30, "bold"), text_color="green").place(x=50, y=10)
    ctk.CTkLabel(frame, text="Cart", font=("Times New Roman", 30, "bold"), text_color="black").place(x=110, y=10)

    icons = {
        "Dashboard": "photos/dash.png",
        "Categories": "photos/1.png",
        "Wishlist": "photos/fav.png",
        "Order": "photos/cart.png",
        "Location": "photos/loc.png",
        "Checkout": "photos/payment.png",
        "Account": "photos/2.png",
        "LogOut": "photos/logout.png"
    }

    loaded_icons = {}
    for key, path in icons.items():
        try:
            size = (36, 36) if key == "Wishlist" else (35, 35)
            img = Image.open(path).resize(size, Image.LANCZOS)
            loaded_icons[key] = CTkImage(light_image=img, size=size)
        except Exception as e:
            print(f"[Sidebar] Failed to load icon '{key}': {e}")
    main_buttons = [
        {"text": "Dashboard", "image": loaded_icons["Dashboard"], "command": lambda: show_loading_screen()},
        {"text": "Categories", "image": loaded_icons["Categories"], "command": lambda: categories()},
        {"text": "Wishlist", "image": loaded_icons["Wishlist"], "command": lambda: wishlist()},
        {"text": "Location", "image": loaded_icons["Location"],
         "command": lambda: show_map_with_path()},
        {"text": "Order", "image": loaded_icons["Order"], "command": lambda: orders_page()},
        {"text": "Checkout", "image": loaded_icons["Checkout"], "command": lambda: checkout()},
        {"text": "Account", "image": loaded_icons["Account"], "command": lambda: show_profile_screen()},
    ]
    button_width = 170
    button_height = 45
    top_spacing = 75
    spacing = 10
    for i, config in enumerate(main_buttons):
        y_pos = top_spacing + i * (button_height + spacing)
        btn = ctk.CTkButton(
            frame,
            text=config["text"],
            image=config["image"],
            compound="left",
            anchor="w",
            font=("Arial", 17),
            fg_color="white",
            bg_color="white",
            text_color="green",
            hover_color="#006400",
            width=button_width,
            height=button_height,
            corner_radius=20,
            command=config["command"]
        )
        btn.place(x=10, y=y_pos)
        btn.bind("<Enter>", lambda e, b=btn: on_enter(e, b))
        btn.bind("<Leave>", lambda e, b=btn: on_leave(e, b))

    logout_btn = ctk.CTkButton(
        frame, text="Log Out", image=loaded_icons["LogOut"], compound="left",
        anchor="w",
        font=("Arial", 17), fg_color="white", bg_color="white", text_color="green",
        hover_color="#8B0000", width=button_width, height=button_height, corner_radius=20,
        command=lambda: logout()
    )
    logout_btn.place(x=10, y=520)
    logout_btn.bind("<Enter>", lambda e: logout_btn.configure(text_color="white", fg_color="dark red"))
    logout_btn.bind("<Leave>", lambda e: logout_btn.configure(text_color="green", fg_color="white"))


def render_searchbar():
    clear_screen()
    render_sidebar()

    def perform_search():
        keyword = search_entry.get().strip()
        if not keyword:
            return
        try:
            response = requests.post(
                f"{api.BASE_URL}/product/search/",
                json={"product": keyword},
                headers=api.session.headers
            )
            response.raise_for_status()
            results = response.json()
            show_search_results(results)
        except Exception as e:
            print("Search Error:", e)

    try:
        search_img = Image.open("photos/search.png").resize((27, 27), Image.LANCZOS)
        search_icon = CTkImage(light_image=search_img, size=(27, 27))
    except Exception as e:
        print(f"[Search Icon] Failed to load icon: {e}")
        search_icon = None

    # Search Entry
    search_entry = ctk.CTkEntry(app, placeholder_text="Search Product..", width=700, height=40, border_width=2,
                                fg_color="white", text_color="black", border_color="green")
    search_entry.place(x=590, y=10, anchor="n")

    # Search Button
    search_button = ctk.CTkButton(app, image=search_icon, text="", width=100, height=30,
                                  fg_color="white", hover_color="#e0ffe0", command=perform_search)
    search_button.place(x=835, y=13)


from functools import partial


def show_search_results(results):
    clear_screen()
    render_sidebar()
    # Search bar
    render_searchbar()

    ctk.CTkLabel(app, text="Search Results", font=("Times New Roman", 30, "bold"),
                 text_color="black", bg_color="white").place(x=220, y=80)

    sc = ctk.CTkScrollableFrame(app, width=750, height=475, bg_color="white", fg_color="white")
    sc.place(x=200, y=120)

    for i, product in enumerate(results):
        frame = ctk.CTkFrame(sc, width=200, height=350, fg_color="white", border_color="green", border_width=2)
        frame.grid(row=i // 3, column=i % 3, padx=15, pady=15)

        title = product.get('ProductName', 'Unknown')
        price = float(product.get('ProductPrice', 0))
        image_url = product.get('ProductImage', '')

        image_label = ctk.CTkLabel(frame, text="Loading...", width=100, height=100,
                                   fg_color="white", text_color="gray")
        image_label.place(x=50, y=10)

        def load_image(url, label, size=(100, 100)):
            try:
                response = requests.get(url)
                response.raise_for_status()
                img = Image.open(io.BytesIO(response.content)).resize(size, Image.LANCZOS)
                ctk_img = CTkImage(light_image=img, size=size)
                label.configure(image=ctk_img, text="")
                label.image = ctk_img  # Keep reference alive
            except Exception as e:
                print(f"[Image Load] Failed to load: {e}")
                label.configure(text="Image Error")

        threading.Thread(
            target=partial(load_image, image_url, image_label),
            daemon=True
        ).start()

        ctk.CTkLabel(frame, text=title, font=("Arial", 14, "bold"),
                     text_color="green", wraplength=160, justify="center").place(x=10, y=130)
        ctk.CTkLabel(frame, text=f"Price: {price:.2f} EGP", font=("Arial", 14),
                     text_color="black").place(x=10, y=230)
        ctk.CTkButton(frame, text="Add to Cart", width=140, fg_color="green").place(x=25, y=280)


def show_profile_screen():
    clear_screen()
    render_sidebar()

    profile = api.get_profile()
    if not profile or not isinstance(profile, dict):
        messagebox.showerror("Error", "Can`t load your data")
        return

    # ====== Main Frame ======
    main_frame = ctk.CTkFrame(app, width=820, height=500, fg_color="white", border_color="green", border_width=2)
    main_frame.place(x=220, y=50)

    # ====== Profile Image ======
    image_frame = ctk.CTkFrame(main_frame, width=250, height=250, fg_color="white")
    image_frame.place(x=530, y=40)

    try:
        image_url = profile.get('clientImage', "")
        full_image_url = f"{api.BASE_URL}{image_url}" if image_url.startswith("/") else image_url
        response = requests.get(full_image_url)
        response.raise_for_status()
        img_data = response.content
        image = Image.open(BytesIO(img_data)).resize((200, 200))
        profile_img = ctk.CTkImage(light_image=image, dark_image=image, size=(200, 200))
        ctk.CTkLabel(image_frame, image=profile_img, text="").pack()
    except Exception as e:
        ctk.CTkLabel(image_frame, text="No image", text_color="red").pack()

    # ====== Profile Info ======
    info_frame = ctk.CTkFrame(main_frame, width=500, height=400, fg_color="white")
    info_frame.place(x=20, y=20)

    ctk.CTkLabel(info_frame, text="My Profile", font=("Arial", 26, "bold"), text_color="green").pack(pady=(0, 20))

    fields = [
        ("Username", profile.get('clientUserName', 'N/A')),
        ("First Name", profile.get('clientFirstName', 'N/A')),
        ("Last Name", profile.get('clientLastName', 'N/A')),
        ("Email", profile.get('clientEmail', 'N/A')),
        ("Phone Number", profile.get('clientPhone', 'N/A')),
        ("Gender", profile.get('clientGender', 'N/A').capitalize()),
        ("Birthday", profile.get('clientBirthdate', 'N/A')),
        ("Money", f"{profile.get('clientMoney', 0)} EGP"),
        ("Points", f"{profile.get('clientPoints', 0)}"),
    ]

    for label, value in fields:
        row = ctk.CTkFrame(info_frame, fg_color="white")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text=f"{label}:", font=("Arial", 18, "bold"), text_color="black", width=140, anchor="w").pack(
            side="left")
        ctk.CTkLabel(row, text=str(value), font=("Arial", 18), text_color="green", anchor="w").pack(side="left")


def update_image():
    global img_index
    window_width = app.winfo_width()
    window_height = app.winfo_height()
    try:
        img = Image.open(img_path[img_index]).resize((window_width, window_height), Image.LANCZOS)
        ctk_img = CTkImage(light_image=img, size=(window_width, window_height))
        img_label.configure(image=ctk_img)
        img_label.image = ctk_img
    except Exception as e:
        print(f"[Background Image] Failed to load: {e}")
    img_index = (img_index + 1) % len(img_path)
    app.after(2000, update_image)


def next_page():
    clear_screen()

    if hasattr(app, 'ai_core'):
        app.ai_core.stop_detection()

    frame2 = ctk.CTkFrame(app, width=1080, height=90, fg_color="green", border_color="#006400", bg_color="green")
    frame2.place(x=0, y=0)
    try:
        img = Image.open("photos/cart.jpeg").resize((350, 440), Image.LANCZOS)
        ctk_photo = CTkImage(light_image=img, size=(350, 440))
        l77 = ctk.CTkLabel(app, image=ctk_photo, text="")
        l77.image = ctk_photo  # important
        l77.place(x=25, y=100)
    except Exception as e:
        print(f"[Cart Image] Failed to load: {e}")

    l15 = ctk.CTkLabel(app,
                       text=" Shop Smart,",
                       text_color="green", font=("times new roman", 50, "bold"))
    l15.place(x=380, y=150)
    l15 = ctk.CTkLabel(app,
                       text="     Shop Easy- ",
                       text_color="green", font=("times new roman", 50, "bold"))
    l15.place(x=450, y=250)
    l15 = ctk.CTkLabel(app,
                       text="Welcome to Easy Cart!",
                       text_color="green", font=("times new roman", 50, "bold"))
    l15.place(x=550, y=350)
    b2 = ctk.CTkButton(app, text="Login", bg_color="white", command=login_1, width=220, height=40, fg_color="green",
                       text_color="white", font=("Arial", 20))
    b2.place(x=460, y=550)
    b4 = ctk.CTkButton(app, text="Scan", width=220, height=40, bg_color="white", fg_color="green", command=scan,
                       text_color="white", font=("Arial", 20))
    b4.place(x=60, y=550)

    b3 = ctk.CTkButton(app, text="Sign Up", bg_color="white", fg_color="green", command=sign_up,
                       text_color="white"
                       , width=220, height=40, font=("Arial", 20))
    b3.place(x=840, y=550)



#############################################################################################################################################################

def redraw_map_path(canvas, bw_map, color_map, products, cart_pos,
                    resized_w=680, resized_h=560, original_w=550, original_h=550):
    try:
        scale_x = resized_w / original_w
        scale_y = resized_h / original_h

        cart_point = (int(cart_pos[0]), int(cart_pos[1]))
        start = find_nearest_walkable(bw_map, cart_point)
        resized_color_map = cv2.resize(color_map.copy(), (resized_w, resized_h))

        product_points = [(int(p["x"]), int(p["y"])) for p in products if "x" in p and "y" in p]
        exit_point = (40, 365)

        if not product_points:
            print("[Path] No product points. Drawing direct path to exit.")
            full_path = calculate_total_path(bw_map, [start, exit_point])
            sorted_points = []
        else:
            walkable_targets = [find_nearest_walkable(bw_map, pt) for pt in product_points]
            sorted_points = sort_points_by_path_distance(bw_map, start, walkable_targets)
            full_path = calculate_total_path(bw_map, [start] + sorted_points + [exit_point])

        if full_path:
            scaled_path = [(int(x * scale_x), int(y * scale_y)) for x, y in full_path]
            resized_color_map = draw_path_with_arrows(
                color_map=resized_color_map,
                path=scaled_path,
                line_color=(0, 191, 98),
                arrow_color=(236, 190, 60),
                line_thickness=3,
                arrow_thickness=2,
                arrow_spacing=150
            )

            for pt in sorted_points:
                rx, ry = int(pt[0] * scale_x), int(pt[1] * scale_y)
                cv2.circle(resized_color_map, (rx, ry), 7, (255, 0, 0), -1)

            ex, ey = int(exit_point[0] * scale_x), int(exit_point[1] * scale_y)
            cv2.circle(resized_color_map, (ex, ey), 10, (0, 0, 255), -1)

        # Convert to Tk image
        color_map_rgb = cv2.cvtColor(resized_color_map, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(color_map_rgb)
        img_tk = ImageTk.PhotoImage(img_pil)

        # Clear canvas then draw base map
        canvas.delete("all")
        canvas.create_image(0, 0, anchor="nw", image=img_tk)
        canvas.image = img_tk

        # Draw cart on top
        cart_img = Image.open("photos/cart.png").resize((30, 30), Image.LANCZOS)
        cart_tk = ImageTk.PhotoImage(cart_img)
        cart_x, cart_y = int(start[0] * scale_x), int(start[1] * scale_y)
        canvas.create_image(cart_x, cart_y, anchor="center", image=cart_tk)
        canvas.cart_photo = cart_tk

    except Exception as e:
        print(f"[redraw_map_path] Failed: {e}")

def create_product_card(parent, item, border_color, extra_text=""):
    frame = ctk.CTkFrame(parent, width=340, height=90, fg_color="white", border_color=border_color, border_width=2)
    frame.pack(pady=5, padx=5)
    print(item)

    image_path = api.BASE_URL + item.get("image", "")
    try:
        img = Image.open(requests.get(image_path, stream=True, timeout=3).raw).resize((70, 70), Image.LANCZOS)
    except:
        img = Image.new("RGB", (70, 70), color="grey")

    ctk_img = CTkImage(light_image=img, size=(70, 70))
    img_label = ctk.CTkLabel(frame, image=ctk_img, text="", fg_color="white")
    img_label.image = ctk_img
    img_label.place(x=10, y=10)

    name = item.get("name", "Unknown")
    short_name = name[:25] + "..." if len(name) > 25 else name
    price = item.get("total_price", 0)

    tk.Label(frame, text=short_name + extra_text, font=("Arial", 10, "bold"), bg="white", anchor="w").place(x=90, y=20)
    tk.Label(frame, text=f"{price} EGP", font=("Arial", 10), bg="white", fg=border_color).place(x=90, y=50)



def show_map_with_path(bw_map_path="AStar/IMG/b&w.png", color_map_path="photos/map.png"):
    clear_screen()
    app.geometry("1080x600")

    updated = api.get_cart_items()
    if updated:
        app_state.products, app_state.picked_items = updated
        app_state.save_state()

    products = app_state.products
    picked_items = app_state.picked_items
    cart_pos = app_state.cart_position

    map_frame = tk.Frame(app, bg="green", width=680, height=580)
    map_frame.place(x=10, y=10)
    canvas = tk.Canvas(map_frame, width=680, height=560, bg="white")
    canvas.pack()

    info_frame = tk.Frame(app, bg="white", width=380, height=580, highlightbackground="black", highlightthickness=2)
    info_frame.place(x=700, y=10)

    # AI Status
    ai_status = tk.Label(info_frame, text="AI: OFF", font=("Arial", 10, "bold"), bg="white", fg="gray")
    ai_status.place(x=260, y=10)

    ai_detect = tk.Label(info_frame, text="Detection: OFF", font=("Arial", 10, "bold"), bg="white", fg="gray")
    ai_detect.place(x=280, y=10)

    checkout_btn = ctk.CTkButton(app, text="Checkout", command=checkout, fg_color="#007B00", text_color="white")
    checkout_btn.place(x=870, y=545)

    back_btn = ctk.CTkButton(app, text="? Back", command=show_loading_screen, fg_color="white", text_color="green")
    back_btn.place(x=10, y=5)

    def create_scrollable_area(parent, width, height):
        outer_frame = tk.Frame(parent, width=width, height=height)
        outer_frame.pack_propagate(False)

        canvas = tk.Canvas(outer_frame, width=width - 15, height=height, bg="white", highlightthickness=0)
        scrollbar = tk.Scrollbar(outer_frame, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="white")

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        return outer_frame, scroll_frame

    tk.Label(info_frame, text="EasyCartVirtualItems", font=("Arial", 14, "bold"), bg="white", fg="green").place(x=10, y=5)
    virtual_container, virtual_frame = create_scrollable_area(info_frame, 360, 250)
    virtual_container.place(x=10, y=35)

    tk.Frame(info_frame, bg="gray", height=2, width=360).place(x=10, y=295)
    tk.Label(info_frame, text="EasyCartItems", font=("Arial", 14, "bold"), bg="white", fg="blue").place(x=10, y=310)
    picked_container, picked_frame = create_scrollable_area(info_frame, 360, 240)
    picked_container.place(x=10, y=340)

    bw_map = cv2.imread(bw_map_path, cv2.IMREAD_GRAYSCALE)
    color_map = cv2.imread(color_map_path)
    if bw_map is None or color_map is None:
        print("Map or Color Map not found")
        return

    # === Render Products
    def render_products():
        for widget in virtual_frame.winfo_children():
            widget.destroy()
        for widget in picked_frame.winfo_children():
            widget.destroy()

        updated = api.get_cart_items()
        if updated:
            app_state.products, app_state.picked_items = updated

        products = app_state.products
        picked_items = app_state.picked_items

        if products:
            for item in products:
                name = item.get("name")
                star = " *" if hasattr(app, 'ai_core') and any(
                    p.get("ProductName") == name for p in app.ai_core.waiting_products
                ) and item not in picked_items else ""
                create_product_card(virtual_frame, item, border_color="green", extra_text=star)
        else:
            tk.Label(virtual_frame, text="No virtual products", font=("Arial", 12), bg="white", fg="gray").pack(pady=10)

        if picked_items:
            for item in picked_items:
                # print(f"[UI] {item}")
                create_product_card(picked_frame, item, border_color="blue")
        else:
            tk.Label(picked_frame, text="No products", font=("Arial", 12), bg="white", fg="gray").pack(pady=10)

    render_products()

    def update_items_only():
        try:
            updated = api.get_cart_items()
            if updated:
                app_state.products, app_state.picked_items = updated
                app_state.save_state()
                render_products()
                redraw_map_path(canvas, bw_map, color_map, app_state.products, cart_pos)
        except Exception as e:
            print("[UI Update] Failed:", e)

    def on_product_confirmed(product):
        if product in app_state.products:
            app_state.products.remove(product)
        if product not in app_state.picked_items:
            app_state.picked_items.append(product)
        try:
            api.session.post(f"{api.BASE_URL}/cart/EasyCartItems/",
                             json={"QRNumber": product["QRNumber"], "quantity": 1},
                             headers=api.session.headers)
            update_items_only()
        except Exception as e:
            print("[MAP] Add Sync Failed:", e)

    def on_product_removed(product):
        if product in app_state.picked_items:
            app_state.picked_items.remove(product)
        if product not in app_state.products:
            app_state.products.append(product)
        app_state.save_state()
        try:
            api.session.delete(f"{api.BASE_URL}/cart/EasyCartItems/",
                               json={"QRNumber": product["QRNumber"], "quantity": 1},
                               headers=api.session.headers)
            update_items_only()
        except Exception as e:
            print("[MAP] Remove Sync Failed:", e)

    # AI Core setup
    if not hasattr(app, 'ai_core'):
        app.ai_core = EasyCartAICore(on_product_confirmed, on_product_removed)
    else:
        app.ai_core.resume_detection()
        app.ai_core.on_product_confirmed = on_product_confirmed
        app.ai_core.on_product_removed = on_product_removed

    redraw_map_path(canvas, bw_map, color_map, products, cart_pos)

    # Update AI status label
    def update_ai_label():
        if hasattr(app, 'ai_core') and app.ai_core.ai_active:
            ai_status.config(text="AI", fg="green")
        else:
            ai_status.config(text="AI", fg="red")
        info_frame.after(1000, update_ai_label)
    update_ai_label()

    def update_detection_label():
        if app.ai_core.ai_active and app.ai_core.detection_active:
            ai_detect.config(text="Detection", fg="green")
        else:
            ai_detect.config(text="Detection", fg="red")
        info_frame.after(1000, update_detection_label)

    update_detection_label()




###################################################################################################################################################################################

def show_loading_screen():
    clear_screen()

    if hasattr(app, 'ai_core'):
        app.ai_core.stop_detection()

    loading_frame = ctk.CTkFrame(app, width=1060, height=580, fg_color="white")
    loading_frame.place(x=10, y=10)
    loading_label = ctk.CTkLabel(loading_frame, text="Loading Dashboard...", font=("Arial", 30, "bold"),
                                 text_color="green")
    loading_label.place(relx=0.5, rely=0.5, anchor="center")

    def load_data_in_thread():
        try:
            products = api.get_all_products()
            app_state.products = products  # Update state
            app_state.save_state()
        except Exception as e:
            print("Error while loading:", e)
            products = []

        def render_dashboard():
            loading_frame.destroy()
            dashboard(products)

        app.after(0, render_dashboard)

    threading.Thread(target=load_data_in_thread, daemon=True).start()


def login_1():
    clear_screen()
    bottom_frame = ctk.CTkFrame(app, width=540, height=590, fg_color="transparent", border_width=2.5)
    bottom_frame.place(x=30, y=10)
    top_frame = ctk.CTkFrame(app, width=540, height=589, fg_color="green", border_width=2.5, bg_color="green",
                             border_color="green")
    top_frame.place(x=550, y=10)
    ctk.CTkLabel(top_frame, text="🛒Easy Cart", font=("Times New Roman", 20, "bold"), text_color="white").place(
        x=20, y=15)
    ctk.CTkLabel(top_frame, text="Welcome Our Host!", font=("Arial", 30, "bold"), text_color="white",
                 bg_color="green").place(x=140, y=80)
    ctk.CTkLabel(top_frame, text="Create your Account", font=("Times New Roman", 40, "bold"), text_color="white",
                 bg_color="green").place(x=100, y=150)
    ctk.CTkLabel(bottom_frame, text="Sign In", font=("Arial", 30, "bold"), text_color="green").place(x=180, y=80)
    entries = {}
    y_pos = 130
    # Username Field
    ctk.CTkLabel(bottom_frame, text="Username", font=("Arial", 16), text_color="green").place(x=50, y=y_pos)
    username_entry = ctk.CTkEntry(bottom_frame, width=400, height=40, placeholder_text="Enter Username",
                                  text_color="black", fg_color="white")
    username_entry.place(x=50, y=y_pos + 30)
    entries["entry_username"] = username_entry
    y_pos += 80

    # Password Field + Show/Hide Button
    ctk.CTkLabel(bottom_frame, text="Password", font=("Arial", 16), text_color="green").place(x=50, y=y_pos)
    password_entry = ctk.CTkEntry(bottom_frame, width=400, height=40, placeholder_text="Enter Password",
                                  text_color="black", fg_color="white", show="*")
    password_entry.place(x=50, y=y_pos + 30)

    def toggle_password():
        if password_entry.cget("show") == "":
            password_entry.configure(show="*")
            eye_button.configure(text="Show")
        else:
            password_entry.configure(show="")
            eye_button.configure(text="Hide")

    eye_button = ctk.CTkButton(bottom_frame, text="Show", width=50, command=toggle_password, bg_color="white",
                               text_color="green", fg_color="white", hover_color="white")
    eye_button.place(x=390, y=y_pos + 38)
    entries["password_entry"] = password_entry
    y_pos += 80

    result_label = ctk.CTkLabel(bottom_frame, text="", font=("Arial", 16), text_color="green")
    result_label.place(x=150, y=420)
    forgot_password_label = ctk.CTkLabel(bottom_frame, text="Forgot Password?", fg_color="transparent",
                                         text_color="green", bg_color="white", font=("Arial", 15, "bold"))
    forgot_password_label.place(y=300, x=350)

    def login():
        username = username_entry.get()
        password = password_entry.get()
        if not username or not password:
            CTkMessagebox(title="Input Error", message="Please fill in the username and password.", icon="warning")
            return

        def do_login():
            try:
                response = api.login_user(username, password)
                if response["access"]:
                    # ???? ??????? ??? GUI Main Thread
                    app.after(0, lambda: (
                        CTkMessagebox(title="Success", message=f"Welcome {username}?", icon="check"),
                        show_loading_screen()
                    ))
                else:
                    app.after(0, lambda: messagebox.showerror("Error", f"Failed to login: {response.text}"))
            except Exception as e:
                app.after(0, lambda: messagebox.showerror("Error", str(e)))

        threading.Thread(target=do_login).start()

    login_button = ctk.CTkButton(bottom_frame, text="Login", command=login, fg_color="green", bg_color="white",
                                 text_color="black", width=220, corner_radius=20,
                                 height=50, hover_color="dark green", font=("Arial", 20))
    login_button.place(x=150, y=360)
    qr_login_button = ctk.CTkButton(bottom_frame, text="Login by QR",
                                    fg_color="white", text_color="green", border_width=2, border_color="green",
                                    width=220, corner_radius=20, height=50, hover_color="green",
                                    font=("Arial", 18, "bold"),command= lambda :scan())
    qr_login_button.place(x=150, y=420)

    ctk.CTkLabel(top_frame, text="Don't have an account yet?", text_color="white", bg_color="green",
                 font=("Arial", 20)).place(x=160, y=220)

    b21 = ctk.CTkButton(top_frame, text="Sign Up", fg_color="green", bg_color="green",
                        text_color="white", width=220, corner_radius=20, border_color="white", border_width=5,
                        height=50, hover_color="#006400", font=("Arial", 20))
    b21.place(y=280, x=160)

    b22 = ctk.CTkButton(top_frame, text="Back", fg_color="green", bg_color="green", command=next_page,
                        text_color="white", width=220, corner_radius=20, border_color="white", border_width=5,
                        height=50, hover_color="#006400", font=("Arial", 20))
    b22.place(y=350, x=160)


def scan(camera_index=0):
    global camera_running, picam2_instance
    clear_screen2()
    camera_running = True

    frame = ctk.CTkFrame(app, width=640, height=300, fg_color="white", corner_radius=10)
    frame.pack(pady=10, padx=20)

    title = ctk.CTkLabel(frame, text="Scan QR to Login", font=("Arial", 24, "bold"), text_color="green")
    title.pack(pady=(10, 10))

    video_label = ctk.CTkLabel(frame, text="")
    video_label.pack()

    def stop_camera():
        global camera_running, picam2_instance
        camera_running = False
        try:
            if picam2_instance is not None:
                picam2_instance.stop()
                picam2_instance.close()
                picam2_instance = None
        except Exception as e:
            print(f"Error stopping camera: {e}")

    back_btn = ctk.CTkButton(frame, text="Back", width=200, fg_color="green",
                             command=lambda: [stop_camera(), next_page()])
    back_btn.pack(pady=10)

    try:
        # ????? ?? ?????? ???? ??????
        stop_camera()
        camera_running = True

        # ????? ?????? ?????
        picam2_instance = Picamera2(camera_num=camera_index)
        config = picam2_instance.create_preview_configuration(main={"format": 'RGB888', "size": (640, 480)})
        picam2_instance.configure(config)
        picam2_instance.start()
    except Exception as e:
        messagebox.showerror("Camera Error", f"Failed to initialize camera: {str(e)}")
        return

    def update_frame():
        if not camera_running:
            return

        try:
            frame_array = picam2_instance.capture_array()

            decoded = pyzbar.decode(frame_array)
            if decoded:
                QR = decoded[0].data.decode("utf-8")
                stop_camera()
                try:
                    app_state.products, app_state.picked_items = api.cart_cheek_in(QR)
                    if app_state.products:
                        show_map_with_path()
                    else:
                        messagebox.showerror("No Items", "No products found in cart.")
                except Exception as e:
                    messagebox.showerror("Error", str(e))
                return

            img = Image.fromarray(frame_array)
            ctk_img = CTkImage(light_image=img, size=img.size)
            video_label.configure(image=ctk_img)
            video_label.image = ctk_img
        except Exception as e:
            print(f"Frame error: {e}")
            stop_camera()
            return

        if camera_running:
            video_label.after(30, update_frame)
    print(camera_running)
    update_frame()


# def scan(camera_index=0):
#     global app_state
#     clear_screen()
#
#     frame = ctk.CTkFrame(app, width=640, height=300, fg_color="white", corner_radius=10)
#     frame.pack(pady=10, padx=20)
#
#     title = ctk.CTkLabel(frame, text="Scan QR to Login", font=("Arial", 24, "bold"), text_color="green")
#     title.pack(pady=(10, 10))
#
#     video_label = ctk.CTkLabel(frame, text="")
#     video_label.pack()
#
#     def stop_camera_and_next():
#         nonlocal running
#         running = False
#         time.sleep(0.3)
#         try:
#             picam2.stop()
#             picam2.close()
#         except:
#             pass
#         next_page()
#
#     back_btn = ctk.CTkButton(frame, text="Back", width=200, fg_color="green", command=stop_camera_and_next)
#     back_btn.pack(pady=10)
#
#     picam2 = Picamera2(camera_num=camera_index)
#     config = picam2.create_preview_configuration(main={"format": 'RGB888', "size": (640, 480)})
#     picam2.configure(config)
#     picam2.start()
#
#     running = True
#
#     def update_frame():
#         nonlocal running
#         if not running:
#             return
#
#         try:
#             frame_array = picam2.capture_array()
#         except:
#             return
#
#         decoded = pyzbar.decode(frame_array)
#         if decoded:
#             QR = decoded[0].data.decode("utf-8")
#             try:
#                 picam2.stop()
#                 picam2.close()
#                 running = False
#                 print("after back")
#                 app_state.products, app_state.picked_items = api.cart_cheek_in(QR)
#                 print(app_state.products)
#                 print(app_state.picked_items)
#                 if app_state.products:
#                     show_map_with_path()
#                 else:
#                     messagebox.showerror("No Items", "No products found in cart.")
#             except Exception as e:
#                 messagebox.showerror("Error", str(e))
#             return
#
#         try:
#             img = Image.fromarray(frame_array)
#             ctk_img = CTkImage(light_image=img, size=img.size)
#             video_label.configure(image=ctk_img)
#             video_label.image = ctk_img
#         except Exception as e:
#             print(f"Frame display error: {e}")
#
#         video_label.after(30, update_frame)
#
#     update_frame()

def orders_page():
    clear_screen()
    cart_data=app_state.products
    orders = []
    if cart_data and "EasyCartItems" in cart_data:
        easy_cart = cart_data["EasyCartItems"][0]
        items = easy_cart.get("items", {})
        for product_id, item_info in items.items():
            product = item_info.get("product", {})
            orders.append({
                "id": product_id,
                "name": product.get("ProductName", "Unknown"),
                "price": product.get("ProductPrice", 0.0),
                "quantity": item_info.get("quantity", 1),
                "weight": product.get("ProductWeight", 0.0),
                "discount": product.get("ProductDiscount", 0)
            })

    title = ctk.CTkLabel(app, text="Orders", font=("Arial", 40, "bold"), text_color="#005F43")
    title.place(x=530, y=20, anchor="n")

    sc = ctk.CTkScrollableFrame(app, width=1060, height=400, bg_color="white", fg_color="white")
    sc.place(x=10, y=70)

    btn = ctk.CTkButton(app, text="Location", width=220, height=45, fg_color="#388e3c", hover_color="#4caf50",
                        command=lambda: show_map_with_path())
    btn.place(x=610, y=570, anchor="center")
    btn = ctk.CTkButton(app, text="Back", width=220, height=45, fg_color="#388e3c", hover_color="#4caf50",
                        command=show_loading_screen)
    btn.place(x=330, y=570, anchor="center")

    headers = ["Product", "Price", "Quantity", "Subtotal", "Weight"]
    for col, header in enumerate(headers):
        lbl = ctk.CTkLabel(sc, text=header, font=("Arial", 20, "bold"), text_color="#007A4D")
        lbl.grid(row=0, column=col, padx=70, pady=15)

    quantity_vars = []
    subtotal_labels = []

    total_var = tk.DoubleVar(value=0.0)
    total_label = ctk.CTkLabel(app, text=f"Total: 0.00LE", font=("Arial", 20, "bold"), text_color="#005F43")
    total_label.place(x=900, y=560)

    def update_total():
        total = 0
        for i, var in enumerate(quantity_vars):
            qty = var.get()
            price = orders[i]["price"]
            total += qty * price
        total_var.set(total)
        total_label.configure(text=f"Total: {total:.2f}LE")

    def update_subtotal(index):
        qty = quantity_vars[index].get()
        price = orders[index]["price"]
        subtotal = qty * price
        subtotal_labels[index].configure(text=f"{subtotal:.2f}LE")
        update_total()

    def increase_quantity(index):
        quantity_vars[index].set(quantity_vars[index].get() + 1)
        update_subtotal(index)

    def decrease_quantity(index):
        current_qty = quantity_vars[index].get()
        if current_qty > 1:
            quantity_vars[index].set(current_qty - 1)
            update_subtotal(index)

    for i, product in enumerate(orders):
        ctk.CTkLabel(sc, text=product["name"], font=("Arial", 14), text_color="#222222").grid(row=i + 1, column=0,
                                                                                              padx=10, pady=5)
        ctk.CTkLabel(sc, text=f"{product['price']:.2f}LE", font=("Arial", 14), text_color="#222222").grid(row=i + 1,
                                                                                                          column=1,
                                                                                                          padx=10,
                                                                                                          pady=5)

        quantity_var = tk.IntVar(value=product["quantity"])
        quantity_vars.append(quantity_var)

        frame_qty = ctk.CTkFrame(sc, fg_color="#e6f2e6")
        frame_qty.grid(row=i + 1, column=2, padx=10, pady=5)

        btn_minus = ctk.CTkButton(frame_qty, text="-", width=30, command=lambda idx=i: decrease_quantity(idx))
        btn_minus.pack(side="left")

        lbl_qty = ctk.CTkLabel(frame_qty, textvariable=quantity_var, width=30, anchor="center", text_color="#222222",
                               fg_color="#e6f2e6")
        lbl_qty.pack(side="left", padx=5)

        btn_plus = ctk.CTkButton(frame_qty, text="+", width=30, command=lambda idx=i: increase_quantity(idx))
        btn_plus.pack(side="left")

        subtotal = product["quantity"] * product["price"]
        lbl_subtotal = ctk.CTkLabel(sc, text=f"{subtotal:.2f}LE", font=("Arial", 14), text_color="#222222")
        lbl_subtotal.grid(row=i + 1, column=3, padx=10, pady=5)
        subtotal_labels.append(lbl_subtotal)

        ctk.CTkLabel(sc, text=f"{product['weight']}g", font=("Arial", 14), text_color="#222222").grid(row=i + 1,
                                                                                                      column=4, padx=10,
                                                                                                      pady=5)

    update_total()


class VerifyPage(ctk.CTkFrame):
    def __init__(self, parent, api_url):
        super().__init__(parent)
        self.api_url = api_url
        self.place(relwidth=1, relheight=1)
        self.configure(fg_color="white")

        ctk.CTkLabel(self, text="🔐 Email Verification", font=("Arial", 30, "bold"),
                     text_color="green").place(relx=0.5, y=100, anchor="center")

        ctk.CTkLabel(self, text="Enter your verification code:", font=("Arial", 18),
                     text_color="black").place(relx=0.5, y=180, anchor="center")

        self.code_entry = ctk.CTkEntry(self, width=300, height=50, font=("Arial", 18),
                                       fg_color="white", text_color="black", border_color="green", border_width=2)
        self.code_entry.place(relx=0.5, y=230, anchor="center")

        ctk.CTkButton(self, text="✅ Verify", command=self.perform_verify,
                      font=("Arial", 18, "bold"),
                      width=200, height=45,
                      fg_color="green", hover_color="dark green", text_color="white").place(relx=0.5, y=300,
                                                                                            anchor="center")

        ctk.CTkButton(self, text="Back", command=next_page,
                      font=("Arial", 16),
                      fg_color="white", hover_color="#d0ffd0", text_color="green", width=120).place(x=20, y=20)

    def perform_verify(self):
        code = self.code_entry.get().strip()
        if not code:
            CTkMessagebox(title="Error", message="Pleas Enter Code", icon="warning")
            return

        try:
            response = requests.post(self.api_url, json={"verificationCode": int(code)})
            if response.status_code == 200:
                data = response.json()
                if data.get("access"):
                    global app_state
                    app_state.user_access_token = data.get("access")
                    app_state.user_refresh_token = data.get("refresh")
                    api.session.headers.update({"Authorization": f"Bearer { app_state.user_access_token}"})
                    api.refresh_token = app_state.user_refresh_token
                    CTkMessagebox(title="Success", message="✅ Verification Done", icon="check")
                    show_loading_screen()
                else:
                    CTkMessagebox(title="Failed", message="❌ Wrong Code, Try Again", icon="cancel")
            else:
                CTkMessagebox(title="Error", message=f"Server Error: {response.status_code}", icon="cancel")
        except ValueError:
            CTkMessagebox(title="خطأ",
                          message="❗ كود التحقق يجب أن يكون رقمًا",
                          icon="warning")
        except requests.exceptions.RequestException as e:
            CTkMessagebox(title="Connection Error", message=f"❌ {str(e)}", icon="cancel")


def sign_up():
    clear_screen()
    # === Top Frame (Left - Welcome) ===
    top_frame = ctk.CTkFrame(app, width=500, height=580, fg_color="green")
    top_frame.place(x=30, y=10)

    ctk.CTkLabel(top_frame, text="🛒 Easy Cart", font=("Times New Roman", 26, "bold"), text_color="white").place(
        x=20, y=20)
    ctk.CTkLabel(top_frame, text="Welcome!", font=("Arial", 30, "bold"), text_color="white").place(x=150, y=100)
    ctk.CTkLabel(top_frame, text="Create your account easily", font=("Arial", 20), text_color="white").place(x=90,
                                                                                                             y=160)

    ctk.CTkButton(top_frame, text="Back", command=next_page,
                  fg_color="white", text_color="green",
                  hover_color="#d0ffd0", font=("Arial", 18, "bold"),
                  width=200, height=45, corner_radius=20).place(x=150, y=350)

    ctk.CTkButton(top_frame, text="Sign In", command=login_1,
                  fg_color="white", text_color="green",
                  hover_color="#d0ffd0", font=("Arial", 18, "bold"),
                  width=200, height=45, corner_radius=20).place(x=150, y=410)

    # === Bottom Frame (Right - Form) ===
    bottom_frame = ctk.CTkFrame(app, width=520, height=580, fg_color="white", border_color="green", border_width=2)
    bottom_frame.place(x=530, y=10)

    ctk.CTkLabel(bottom_frame, text="Sign Up", font=("Arial", 30, "bold"), text_color="green").place(x=190, y=30)

    entries = {}
    fields = [
        ("Username", "username"),
        ("First Name", "first_name"),
        ("Last Name", "last_name"),
        ("Email", "email"),
        ("Password", "password", True)
    ]

    y_pos = 90
    for label_text, key, *is_password in fields:
        ctk.CTkLabel(bottom_frame, text=label_text, font=("Arial", 16), text_color="green").place(x=50, y=y_pos)
        entry = ctk.CTkEntry(
            bottom_frame, text_color="black", width=400, height=40,
            placeholder_text=f"Enter {label_text}", fg_color="white",
            show="*" if is_password and is_password[0] else ""
        )
        entry.place(x=50, y=y_pos + 30)
        entries[key] = entry
        y_pos += 80

    def perform_signup():
        data = {k: e.get().strip() for k, e in entries.items()}
        if not all(data.values()):
            CTkMessagebox(title="Error", message="Please fill in all fields.", icon="warning")
            return
        try:
            res = api.register_user(
                data["username"],
                data["first_name"],
                data["last_name"],
                data["email"],
                data["password"]
            )
            CTkMessagebox(title="Success", message=res.get("message", "Registered Successfully"), icon="check")
            VerifyPage(app, api_url=f"{BASE_URL}/user/verify/")
        except Exception as e:
            CTkMessagebox(title="Signup Failed", message=str(e), icon="cancel")

    ctk.CTkButton(bottom_frame, text="Create Account", command=perform_signup,
                  fg_color="green", hover_color="dark green", text_color="white",
                  width=220, height=50, font=("Arial", 20), corner_radius=20).place(x=150, y=500)


def create_product(parent, row, col, title, rate, price, product_id, weight, discount,
                   image_url=None, image_bytes=None):
    frame = ctk.CTkFrame(parent, width=200, height=350, fg_color="white", border_color="green", border_width=2,
                         bg_color="transparent")
    frame.grid(row=row, column=col, padx=20, pady=15)
    wishlist_state = ctk.StringVar(value="+")

    wishlist_btn = ctk.CTkButton(
        frame,
        textvariable=wishlist_state,
        width=30,
        height=30,
        font=("Arial", 30, "bold"),
        fg_color="transparent", bg_color="white",
        hover_color="#f2f2f2",
        text_color="green",
        corner_radius=10
    )
    wishlist_btn.place(x=155, y=10)
    if discount > 0:
        price_y = 190
        weight_y = 240
        rating_y = 265
    else:
        price_y = 200
        weight_y = 230
        rating_y = 260

    image_label = ctk.CTkLabel(frame, text="Loading...", width=150, height=150)
    image_label.place(x=15, y=5)

    label = ctk.CTkLabel(frame, text=title, font=("Arial", 16, "bold"), text_color="green",
                         fg_color="white", wraplength=160, justify="center")
    label.place(x=10, y=170)

    weight_label = ctk.CTkLabel(frame, text=f"Weight : {weight} Kg", font=("Arial", 14), text_color="green")
    weight_label.place(x=10, y=weight_y)

    if discount > 0:
        discounted_price = price * (1 - discount / 100)
        discounted_label = ctk.CTkLabel(frame, text=f"Discounted Price {discounted_price:.2f}EGP",
                                        font=("Arial", 12, "bold"), text_color="black")
        discounted_label.place(x=5, y=220)

        price_label = ctk.CTkLabel(frame, text=f"Price {price:.2f} LE", font=("Arial", 14, "overstrike", "bold"),
                                   text_color="red")
        price_label.place(x=10, y=price_y)
    else:
        price_label = ctk.CTkLabel(frame, text=f"Price {price:.2f} LE", font=("Arial", 14, "bold"),
                                   text_color="black")
        price_label.place(x=10, y=price_y)

    def get_stars(rate):
        full_stars = int(rate)
        half_star = (rate - full_stars) >= 0.5
        empty_stars = 5 - full_stars - (1 if half_star else 0)

        stars = "[*]" * full_stars
        if half_star:
            stars += "[/]"
        stars += "[ ]" * empty_stars

        return stars

    rating_stars = get_stars(rate)
    rating_label = ctk.CTkLabel(frame, text=f"Rate: {rating_stars}", font=("Arial", 16), text_color="green")
    rating_label.place(x=10, y=rating_y)
    quantity = ctk.IntVar(value=0)

    def increase_qty():
        quantity.set(quantity.get() + 1)
        update_button()

    def decrease_qty():
        current = quantity.get()
        if current > 0:
            quantity.set(current - 1)
        update_button()

    def update_button():
        qty = quantity.get()
        if qty == 0:
            add_cart_btn.configure(text="Add to Cart", width=140, command=add_to_cart)
            add_cart_btn.place(x=25, y=300)
            plus_btn.place_forget()
            minus_btn.place_forget()
            qty_label.place_forget()
        else:
            add_cart_btn.place_forget()
            plus_btn.place(x=120, y=300)
            minus_btn.place(x=40, y=300)
            qty_label.configure(text=str(qty))
            qty_label.place(x=88, y=300)

    def add_to_cart():
        quantity.set(1)
        update_button()

    add_cart_btn = ctk.CTkButton(frame, text="Add to Cart", width=140, command=add_to_cart, fg_color="green",
                                 hover_color="dark green")
    add_cart_btn.place(x=25, y=300)
    plus_btn = ctk.CTkButton(frame, text="+", width=30, command=increase_qty, fg_color="green",
                             hover_color="dark green")
    minus_btn = ctk.CTkButton(frame, text="-", width=30, command=decrease_qty, fg_color="green",
                              hover_color="dark green")
    qty_label = ctk.CTkLabel(frame, text="0", font=("Arial", 14, "bold"), text_color="black")
    qty_label.place_forget()

    def load_and_update_image():
        try:
            if image_bytes:
                img = Image.open(io.BytesIO(image_bytes))
            elif image_url:
                response = requests.get(f"{api.BASE_URL}{image_url}")
                response.raise_for_status()
                img = Image.open(io.BytesIO(response.content))
            else:
                return
            img = img.resize((150, 150), Image.LANCZOS)
            photo_img = CTkImage(light_image=img, size=(150, 150))
            image_label.configure(image=photo_img, text="")  # Remove "Loading..."
            image_label.image = photo_img  # Keep a reference
        except Exception as e:
            print(f"Error loading product image: {e}")

    if image_bytes or image_url:
        threading.Thread(target=load_and_update_image, daemon=True).start()


from customtkinter import CTkImage
from PIL import Image

def dashboard(dashproducts=None):
    global app_state
    clear_screen()

    render_sidebar()
    render_searchbar()
    ctk.CTkLabel(app, text="Popular Products", font=("Times New Roman", 30, "bold"), bg_color="white",
                 fg_color="white", text_color="black").place(x=220, y=80)

    sc = ctk.CTkScrollableFrame(app, width=750, height=475, bg_color="white", fg_color="white",
                                scrollbar_fg_color="white", scrollbar_button_hover_color="dark green",
                                scrollbar_button_color="#388e3c")
    sc.place(x=200, y=120)

    if dashproducts is None:
        try:
            dashproducts = api.get_all_products()
            app_state.products = dashproducts  # Update state
            app_state.save_state()
        except Exception as e:
            print("Error loading products:", e)
            return

    try:
        products_per_row = 3
        row = 0
        col = 0

        for product in dashproducts:
            create_product(
                parent=sc,
                row=row,
                col=col,
                title=product['ProductName'],
                price=product['ProductPrice'],
                product_id=product['ProductCategory'],
                image_url=product['ProductImage'],
                weight=product['ProductWeight'],
                discount=product['ProductDiscount'],
                rate=product['ProductTotalRate']
            )
            col += 1
            if col >= products_per_row:
                col = 0
                row += 1
    except Exception as e:
        print("Error displaying products:", e)


def logout():
    clear_screen()
    bottom_frame = ctk.CTkFrame(app, width=1060, height=580, fg_color="transparent", border_width=2.5)
    bottom_frame.place(x=10, y=10)
    title = ctk.CTkLabel(app, text="Are you sure you want to logout?",
                         font=("Arial", 40, "bold"),
                         text_color="#005F43", bg_color="white")
    title.place(x=540, y=80, anchor="n")

    def confirm_logout():
        try:
            api.logout_user()
            next_page()
        except Exception as e:
            print("Logout error:", e)

    b_yes = ctk.CTkButton(app, text="Yes",
                          command=confirm_logout,
                          bg_color="white", fg_color="green",
                          text_color="white", width=220,
                          height=45, hover_color="#006400", font=("Arial", 20))
    b_yes.place(x=250, y=250)
    b_no = ctk.CTkButton(app, text="No",
                         command=show_loading_screen,
                         bg_color="white", fg_color="green",
                         text_color="white", width=220,
                         height=45, font=("Arial", 20))
    b_no.place(x=600, y=250)


def nfc():
    clear_screen()
    frame = ctk.CTkFrame(app, width=1060, height=580, fg_color="white", border_color="green", border_width=1)
    frame.place(x=10, y=10)

    header = ctk.CTkFrame(frame, width=1060, height=80, fg_color="green")
    header.place(x=0, y=0)

    title = ctk.CTkLabel(header, text="<- Go back to Payment", font=("Arial", 26, "bold"),
                         text_color="white", cursor="hand2")
    title.place(x=30, y=15)
    def stop_nfc():
        checkout()
    title.bind("<Button-1>", lambda e: stop_nfc())

    status_label = ctk.CTkLabel(frame, text="", font=("Arial", 14))
    status_label.place(x=50, y=350)

    try:
        img = Image.open("photos/nfc.png").resize((250, 250))
        photo = CTkImage(light_image=img, size=(250, 250))
        nfc_label = ctk.CTkLabel(frame, text="", image=photo)
        nfc_label.image = photo
        nfc_label.place(x=800, y=150)
    except FileNotFoundError:
        status_label.configure(text="Image not found", text_color="red")

    ctk.CTkLabel(frame, text="Tap your card or phone on the NFC reader", font=("Arial", 24, "bold"),
                 text_color="black").place(x=50, y=150)

    def send_nfc_transaction():
        status_label.configure(text="Waiting for NFC Card...", text_color="orange")

        def task():
            card_data = read_card_text()
            if not card_data:
                status_label.configure(text="Card not detected", text_color="red")
                return

            try:
                response = requests.post(f"{api.BASE_URL}/cart/EasyCartchechout/",
                                         json={"paymentMethod": "Card NFC"},
                                         headers=api.session.headers)
                if response.status_code == 200:
                    data = response.json()
                    status_label.configure(text="Transaction Successful", text_color="green")
                    display_invoice(data)
                else:
                    status_label.configure(text="Payment Failed", text_color="red")
            except Exception as e:
                status_label.configure(text=f"Connection Error: {e}", text_color="red")

        threading.Thread(target=task, daemon=True).start()

    ctk.CTkButton(frame, text="Start Scanning", command=send_nfc_transaction,
                  fg_color="green", height=50).place(x=50, y=250)

def display_invoice(data):
    clear_screen()
    invoice = data.get("invoice", {})
    items = invoice.get("items", {})

    frame = ctk.CTkFrame(app, width=1060, height=580, fg_color="white")
    frame.place(x=10, y=10)

    # Header
    ctk.CTkLabel(frame, text="? Invoice Summary", font=("Arial", 26, "bold"),
                 text_color="green").place(x=30, y=10)

    # Summary Info
    summary = [
        f"Total Amount: {invoice.get('totalAmount')} EGP",
        f"Total Weight: {invoice.get('totalWeight')} g",
        f"Total Quantity: {invoice.get('totalQuantity')} items",
        f"Payment Method: {invoice.get('paymentMethod')}",
        f"Date: {invoice.get('createdAt')}"
    ]
    for i, text in enumerate(summary):
        ctk.CTkLabel(frame, text=text, font=("Arial", 14), text_color="black").place(x=30, y=60 + i * 30)

    # Product Cards
    products_frame = ctk.CTkScrollableFrame(frame, width=980, height=340, fg_color="white",
                                            scrollbar_fg_color="white",
                                            scrollbar_button_color="green",
                                            scrollbar_button_hover_color="dark green")
    products_frame.place(x=30, y=230)

    def create_invoice_product_card(parent, row, col, product, item):
        card = ctk.CTkFrame(parent, width=300, height=200, fg_color="white",
                            border_color="green", border_width=2)
        card.grid(row=row, column=col, padx=15, pady=10)

        img_label = ctk.CTkLabel(card, text="Loading...", width=100, height=100)
        img_label.place(x=10, y=10)

        # Image lazy loading
        def load_image():
            try:
                img_url = product.get("ProductImage", "")
                response = requests.get(f"{api.BASE_URL}{img_url}")
                response.raise_for_status()
                img = Image.open(io.BytesIO(response.content)).resize((100, 100), Image.LANCZOS)
                ctk_img = CTkImage(light_image=img, size=(100, 100))
                img_label.configure(image=ctk_img, text="")
                img_label.image = ctk_img
            except Exception as e:
                print("[Invoice Image] Failed to load:", e)

        threading.Thread(target=load_image, daemon=True).start()

        name = product.get("ProductName", "Unknown")
        qty = item.get("quantity", 0)
        price = item.get("total_price", 0)
        weight = item.get("total_weight", 0)

        ctk.CTkLabel(card, text=name, font=("Arial", 13, "bold"),
                     text_color="green", wraplength=180).place(x=120, y=15)
        ctk.CTkLabel(card, text=f"Qty: {qty} | {price} EGP", font=("Arial", 12)).place(x=120, y=65)
        ctk.CTkLabel(card, text=f"Weight: {weight}g", font=("Arial", 12)).place(x=120, y=95)

    # Render products in grid
    row, col = 0, 0
    for item_data in items.values():
        product = item_data.get("product", {})
        create_invoice_product_card(products_frame, row, col, product, item_data)
        col += 1
        if col >= 3:
            row += 1
            col = 0

    # Done Button
    def go_home():
        show_loading_screen()

    ctk.CTkButton(frame, text="Done", fg_color="green", hover_color="dark green",
                  font=("Arial", 16, "bold"), command=lambda :next_page(), width=180, height=40).place(x=430, y=540)



def checkout():
    clear_screen()
    frame8 = ctk.CTkFrame(app, width=1060, height=580, fg_color="white", border_color="green", border_width=1)
    frame8.place(x=10, y=10)
    frame8.image_refs = []
    title = ctk.CTkLabel(app, text="<-Back", font=("Times New Roman", 25, "bold"),
                         text_color="Green", fg_color="transparent", cursor="hand2")
    title.place(x=70, y=30, anchor="n")
    title.bind("<Button-1>", lambda event: show_loading_screen())

    def credit():
        print("Credit button clicked")

    def create_button(img_path, x_rel, cmd):
        try:
            img = Image.open(img_path).resize((200, 200), Image.LANCZOS)
        except FileNotFoundError:
            print(f"Image {img_path} not found.")
            return
        img = img.resize((150, 100), Image.LANCZOS)
        photo = CTkImage(light_image=img, size=(150, 100))

        btn = ctk.CTkButton(
            frame8,
            text="",
            fg_color="transparent",
            bg_color="white",
            image=photo,
            compound="left",
            border_width=2,
            border_color="white",
            text_color="black",
            width=150,
            height=100,
            hover_color="#3CB371",
            font=("Arial", 20),
            command=cmd
        )
        btn.image = photo
        btn.place(relx=x_rel, y=190, anchor="center")
        frame8.image_refs.append(photo)

    create_button("photos/credit1.png", 0.6, credit)
    create_button("photos/NFC 1.png", 0.4, nfc)


def categories():
    clear_screen()
    render_sidebar()
    render_searchbar()
    l1 = ctk.CTkLabel(app, text="Categories", font=("Times New Roman", 30, "bold"), text_color="black",
                      fg_color="white")
    l1.place(x=280, y=70, anchor="n")
    l1.is_main_title = True

    def load_image_from_url_cat(image_url, size=(100, 100), callback=None):
        def load_image():
            try:
                response = requests.get(f"{api.BASE_URL}{image_url}")
                response.raise_for_status()
                img = Image.open(io.BytesIO(response.content)).resize(size, Image.LANCZOS)
                ctk_image = CTkImage(light_image=img, size=size)
                if callback:
                    callback(ctk_image)
            except Exception as e:
                print(f"Error loading image: {e}")
                if callback:
                    callback(None)

        threading.Thread(target=load_image, daemon=True).start()

    def display_categories():
        categories = api.get_categories()
        base_x, base_y = 260, 120
        x_spacing, y_spacing = 180, 160
        buttons_per_row = 4
        for index, category in enumerate(categories):
            category_name = category['CategoryName']
            category_image_url = category['CategoryImage']
            placeholder = ctk.CTkImage(Image.new('RGBA', (80, 80), (255, 255, 255, 0)))
            btn = ctk.CTkButton(
                app,
                text=category_name,
                font=("bold", 14),
                text_color="black",
                fg_color="white",
                width=100,
                height=120,
                border_width=2,
                border_color="green",
                corner_radius=20,
                image=placeholder,
                compound="top",
                hover_color="green",
                command=lambda c=category_name: open_category_details(c)
            )
            col = index % buttons_per_row
            row = index // buttons_per_row
            x = base_x + (col * x_spacing)
            y = base_y + (row * y_spacing)
            btn.place(x=x, y=y)

            def update_btn_image(img, button=btn):
                if img:
                    button.configure(image=img)

            load_image_from_url_cat(category_image_url, size=(80, 80), callback=update_btn_image)

    display_categories()


def open_category_details(category_name):
    clear_screen()
    render_sidebar()
    # Search bar
    render_searchbar()

    title_label = ctk.CTkLabel(app, text=f"Categories > {category_name}",
                               font=("Times New Roman", 26, "bold"),
                               text_color="black", fg_color="white")
    title_label.place(x=360, y=70, anchor="n")
    title_label.is_category_title = True
    title_label.bind("<Button-1>", lambda e: categories())

    sc = ctk.CTkScrollableFrame(app, width=700, height=450, fg_color="white", bg_color="white")
    sc.place(x=200, y=120)
    products = api.get_products_by_category_by_name(category_name)
    if "error" in products:
        print(f"API Error: {products['error']}")
        return

    def load_image(image_url, label):
        try:
            response = requests.get(f"{api.BASE_URL}{image_url}")
            response.raise_for_status()
            image = Image.open(io.BytesIO(response.content)).resize((100, 100), Image.LANCZOS)
            ctk_img = CTkImage(light_image=image, size=(100, 100))
            label.configure(image=ctk_img, text="")
            label.image = ctk_img  # Keep a reference
        except Exception as e:
            print(f"Image load error: {e}")
            label.configure(text="Image Error", text_color="red")

    for i, product in enumerate(products):
        frame = ctk.CTkFrame(sc, width=200, height=350, fg_color="white", border_color="green", border_width=2)
        frame.grid(row=i // 3, column=i % 3, padx=15, pady=15)

        title = product.get('ProductName', 'Unknown')
        weight = product.get('ProductWeight', 0)
        price = float(product.get('ProductPrice', 0))
        discount = float(product.get('ProductDiscount', 0))
        rate = float(product.get('ProductRate', 0))
        image_url = product.get('ProductImage', '')
        image_label = ctk.CTkLabel(frame, text="Loading...", width=100, height=100, fg_color="white", text_color="gray")
        image_label.place(x=50, y=10)
        threading.Thread(target=load_image, args=(image_url, image_label), daemon=True).start()

        wishlist_state = ctk.StringVar(value=" +")
        wishlist_btn = ctk.CTkButton(
            frame, textvariable=wishlist_state, width=30, height=30,
            font=("Arial", 30, "bold"), fg_color="transparent", bg_color="white",
            hover_color="#f2f2f2", text_color="green", corner_radius=10
        )
        wishlist_btn.place(x=160, y=10)

        if discount > 0:
            price_y = 190
            weight_y = 240
            rating_y = 265
        else:
            price_y = 200
            weight_y = 230
            rating_y = 260

        label = ctk.CTkLabel(frame, text=title, font=("Arial", 16, "bold"), text_color="green",
                             fg_color="white", wraplength=160, justify="center")
        label.place(x=10, y=170)

        weight_label = ctk.CTkLabel(frame, text=f"Weight : {weight} Kg", font=("Arial", 14), text_color="green")
        weight_label.place(x=10, y=weight_y)

        if discount > 0:
            discounted_price = price * (1 - discount / 100)
            discounted_label = ctk.CTkLabel(frame, text=f"Discounted Price: {discounted_price:.2f} EGP",
                                            font=("Arial", 12, "bold"), text_color="black")
            discounted_label.place(x=5, y=220)
            price_label = ctk.CTkLabel(frame, text=f"Price: {price:.2f} EGP", font=("Arial", 14, "overstrike", "bold"),
                                       text_color="red")
            price_label.place(x=10, y=price_y)
        else:
            price_label = ctk.CTkLabel(frame, text=f"Price: {price:.2f} EGP", font=("Arial", 14, "bold"),
                                       text_color="black")
            price_label.place(x=10, y=price_y)

        def get_stars(rate):
            full_stars = int(rate)
            half_star = (rate - full_stars) >= 0.5
            empty_stars = 5 - full_stars - (1 if half_star else 0)
            stars = "[*]" * full_stars
            if half_star:
                stars += "[/]"
            stars += "[ ]" * empty_stars
            return stars

        rating_stars = get_stars(rate)
        rating_label = ctk.CTkLabel(frame, text=f"Rate: {rating_stars}", font=("Arial", 16), text_color="green")
        rating_label.place(x=10, y=rating_y)

        quantity = ctk.IntVar(value=0)

        def increase_qty():
            quantity.set(quantity.get() + 1)
            update_button()

        def decrease_qty():
            current = quantity.get()
            if current > 0:
                quantity.set(current - 1)
            update_button()

        def update_button():
            qty = quantity.get()
            if qty == 0:
                add_cart_btn.configure(text="Add to Cart", width=140, command=add_to_cart)
                add_cart_btn.place(x=25, y=300)
                plus_btn.place_forget()
                minus_btn.place_forget()
                qty_label.place_forget()
            else:
                add_cart_btn.place_forget()
                plus_btn.place(x=120, y=300)
                minus_btn.place(x=40, y=300)
                qty_label.configure(text=str(qty))
                qty_label.place(x=88, y=300)

        def add_to_cart():
            quantity.set(1)
            update_button()

        add_cart_btn = ctk.CTkButton(frame, text="Add to Cart", width=140, command=add_to_cart, fg_color="green",
                                     hover_color="dark green")
        add_cart_btn.place(x=25, y=300)

        plus_btn = ctk.CTkButton(frame, text="+", width=30, command=increase_qty, fg_color="green",
                                 hover_color="dark green")
        minus_btn = ctk.CTkButton(frame, text="-", width=30, command=decrease_qty, fg_color="green",
                                  hover_color="dark green")
        qty_label = ctk.CTkLabel(frame, text="0", font=("Arial", 14, "bold"), text_color="black")
        qty_label.place_forget()
        add_cart = ctk.CTkButton(frame, text="!", width=30,
                                 command=lambda p=product: open_product(p, category_name),
                                 fg_color="green", hover_color="dark green")

        add_cart.place(x=5, y=10)


def open_product(product, category_name):
    clear_screen()

    # ====== Main Frame for Product Details ======
    main_frame = tk.Frame(app, bg="white")
    main_frame.pack(padx=20, pady=20, fill="both", expand=True)

    # ====== Top: Back Button ======
    back_btn = ctk.CTkButton(app, text="← Back", command=lambda: open_category_details(category_name), width=100,
                             fg_color="green")
    back_btn.place(x=20, y=20)

    # ====== Image on the Left ======
    image_frame = tk.Frame(main_frame, bg="white")
    image_frame.place(x=20, y=100)

    img_label = tk.Label(image_frame, text="Loading image...", bg="white")
    img_label.pack()

    def load_img():
        try:
            image_url = product.get("ProductImage", "")
            if image_url:
                response = requests.get(f"{api.BASE_URL}{image_url}")
                response.raise_for_status()
                img = Image.open(io.BytesIO(response.content)).resize((250, 250))
                ctk_image = CTkImage(light_image=img, size=(250, 250))
                img_label.configure(image=ctk_image, text="")
                img_label.image = ctk_image  # ??? ???? ???? ?????? ??????? ?? ???????
            else:
                img_label.configure(text="No image available")
        except Exception as e:
            img_label.configure(text=f"Image error: {e}")

    threading.Thread(target=load_img, daemon=True).start()

    # ====== Product Info on the Right ======
    info_frame = tk.Frame(main_frame, bg="white")
    info_frame.place(x=350, y=50)

    fields = [
        ("Name", product.get("ProductName", "N/A")),
        ("Price", f"{product.get('ProductPrice', 'N/A')} EGP"),
        ("Category", product.get("ProductCategory", "N/A")),
        ("Brand", product.get("ProductBrand", "N/A")),
        ("Weight", f"{product.get('ProductWeight', 'N/A')} Kg"),
        ("Discount", f"{product.get('ProductDiscount', 0)}%"),
        ("Available", "Yes" if product.get("ProductAvailable", False) else "No"),
        ("Boycott", "Yes" if product.get("ProductBoycott", False) else "No"),
        ("Fasting", "Yes" if product.get("ProductFasting", False) else "No"),
        ("Expiry Date", product.get("ExpiryDate", "N/A")),
        ("Total Rate", product.get("ProductTotalRate", "N/A")),
    ]

    for label, value in fields:
        row = tk.Frame(info_frame, bg="white")
        row.pack(anchor="w", pady=2)
        ctk.CTkLabel(row, text=f"{label}:", text_color="green", font=("Arial", 20, "bold"), width=140, anchor="w").pack(
            side="left")
        ctk.CTkLabel(row, text=str(value), font=("Arial", 20), text_color="green", anchor="w").pack(
            side="left")

    # ====== Description ======
    desc_label = tk.Label(app, text="Description", font=("Arial", 20, "bold"), bg="white")
    desc_label.pack(anchor="w", padx=30, pady=(5, 0))

    desc_text = tk.Label(app, text=product.get("ProductDescription", "No description"), font=("Arial", 15), bg="white",
                         wraplength=640, justify="left")
    desc_text.pack(anchor="w", padx=30)

    # ====== Buttons ======
    btn_frame = tk.Frame(app, bg="white")
    btn_frame.pack(pady=15)

    def add_to_cart():
        try:
            payload = {"productId": product["ProductId"], "quantity": 1}
            headers = {"Authorization": f"Bearer {api.token}"}
            r = requests.post(f"{api.BASE_URL}/cart/add", json=payload, headers=headers)
            if r.status_code == 200:
                tk.messagebox.showinfo("Success", "Added to cart!")
            else:
                tk.messagebox.showerror("Error", f"Cart Error: {r.text}")
        except Exception as e:
            tk.messagebox.showerror("Exception", str(e))

    def toggle_wishlist():
        try:
            headers = {"Authorization": f"Bearer {api.token}"}
            payload = {"productId": product["ProductId"]}
            r = requests.post(f"{api.BASE_URL}/wishlist/toggle", json=payload, headers=headers)
            if r.status_code == 200:
                tk.messagebox.showinfo("Success", "Wishlist updated!")
            else:
                tk.messagebox.showerror("Error", f"Wishlist Error: {r.text}")
        except Exception as e:
            tk.messagebox.showerror("Exception", str(e))

    ctk.CTkButton(btn_frame, text="Add to Cart", command=add_to_cart, width=150, fg_color="green").pack(side="left",
                                                                                                        pady=10,
                                                                                                        padx=10)
    ctk.CTkButton(btn_frame, text="♥", command=toggle_wishlist, width=60, fg_color="red").pack(side="left",
                                                                                                    padx=10, pady=5)


def wishlist():
    clear_screen()
    wishlist_qrs = set()
    products = []
    clear_screen()
    render_sidebar()
    # Search bar
    render_searchbar()
    # ===== Scrollable Frames =====
    products_frame = ctk.CTkScrollableFrame(app, width=750, height=450, fg_color="white")
    products_frame.place(x=200, y=120)

    wishlist_products_frame = ctk.CTkScrollableFrame(app, width=750, height=450, fg_color="white")

    wishlist_page = wishlist_products_frame
    wishlist_btn = ctk.CTkButton(app, text="Go to Wishlist", command=lambda: wishlist)

    # === API Functions ===
    def load_wishlist():
        nonlocal wishlist_qrs
        try:
            res = requests.get(f"{api.BASE_URL}/product/wishlist/getmywish/", headers=api.session.headers)
            if res.status_code == 200:
                wishlist_qrs = {item['QRNumber'] for item in res.json()}
            else:
                print("Failed to load wishlist", res.status_code)
        except Exception as e:
            print("Error:", e)

    def load_products():
        nonlocal products
        try:
            res = requests.get(f"{BASE_URL}/product/getall/", headers=api.session.headers)
            if res.status_code == 200:
                products = res.json()
                display_products()
            else:
                print("Failed to load products", res.status_code)
        except Exception as e:
            print("Error:", e)

    def add_to_wishlist(QRNumber):
        try:
            res = requests.post(f"{BASE_URL}/product/wishlist/add/{QRNumber}/", headers=api.session.headers)
            return res.status_code == 200
        except:
            return False

    def remove_from_wishlist(QRNumber):
        try:
            res = requests.delete(f"{BASE_URL}/product/wishlist/remove/{QRNumber}/", headers=api.session.headers)
            return res.status_code == 204
        except:
            return False

    # === Display Functions ===
    def display_products():
        for widget in products_frame.winfo_children():
            widget.destroy()

        for product in products:
            qr = product.get('QRNumber')
            name = product.get('ProductName', 'Unknown')
            price = product.get('ProductPrice', 0.0)
            btn_text = "Remove from Wishlist" if qr in wishlist_qrs else "Add to Wishlist"
            frame = ctk.CTkFrame(products_frame, fg_color="white")
            frame.pack(pady=5, padx=10, fill="x")
            ctk.CTkLabel(frame, text=name, font=("Arial", 16)).pack(side="left", padx=10)
            ctk.CTkLabel(frame, text=f"${price:.2f}", font=("Arial", 14)).pack(side="left", padx=10)
            ctk.CTkButton(frame, text=btn_text, width=150, command=lambda p=product: toggle_wishlist(p)).pack(
                side="right", padx=10)

    def display_wishlist():
        for widget in wishlist_products_frame.winfo_children():
            widget.destroy()
        wished = [p for p in products if p.get('QRNumber') in wishlist_qrs]
        if not wished:
            ctk.CTkLabel(wishlist_products_frame, text="Wishlist is empty.", font=("Arial", 16)).pack(pady=20)
            return
        for product in wished:
            name = product.get('ProductName', 'Unknown')
            price = product.get('ProductPrice', 0.0)
            frame = ctk.CTkFrame(wishlist_products_frame, fg_color="white")
            frame.pack(pady=5, padx=10, fill="x")
            ctk.CTkLabel(frame, text=name, font=("Arial", 16)).pack(side="left", padx=10)
            ctk.CTkLabel(frame, text=f"${price:.2f}", font=("Arial", 14)).pack(side="left", padx=10)
            ctk.CTkButton(frame, text="Remove from Wishlist", width=150,
                          command=lambda p=product: toggle_wishlist(p)).pack(side="right", padx=10)

    def toggle_wishlist(product):
        qr = product.get('QRNumber')
        if not qr:
            return
        if qr in wishlist_qrs:
            if remove_from_wishlist(qr):
                wishlist_qrs.remove(qr)
        else:
            if add_to_wishlist(qr):
                wishlist_qrs.add(qr)
        display_products()
        display_wishlist()

    wishlist_btn.configure(command=toggle_wishlist)

    def show_wishlist_page():
        products_frame.pack_forget()
        wishlist_btn.pack_forget()
        wishlist_page.place(x=200, y=120)
        display_wishlist()

    def show_products_page():
        wishlist_page.place_forget()
        products_frame.place(x=200, y=120)
        wishlist_btn.pack(pady=5)
        display_products()

    # ===== Initial Load =====
    load_wishlist()
    load_products()


############################################################################################################## End #############################
def enable_copy_paste(entry_widget):
    entry_widget.bind("<Control-c>", lambda e: entry_widget.event_generate("<<Copy>>"))
    entry_widget.bind("<Control-v>", lambda e: entry_widget.event_generate("<<Paste>>"))
    entry_widget.bind("<Control-x>", lambda e: entry_widget.event_generate("<<Cut>>"))


l = ctk.CTkLabel(app, text=" X ", text_color="white", font=("Arial", 30, "bold"),
                 bg_color="transparent", fg_color="black", corner_radius=0)
l.bind("<Button-1>", lambda e: next_page())
l.place(x=1040, y=10, anchor="nw")
update_image()
app.mainloop()

