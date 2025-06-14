import tkinter as tk
import winsound
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
from AStar.GIS import find_nearest_walkable, sort_points_by_path_distance, calculate_total_path ,draw_path_with_arrows

BASE_URL = "https://shehab123.pythonanywhere.com"

products=[]
picked_items=[]
cart_position = (70,115) ######################## <--------------------------location

user_access_token = None
user_refresh_token = None
cart_data=None
page_size = 5
app = ctk.CTk()
app.title("Cart Program")
app.geometry("1080x600")
app.configure(fg_color="white")
ctk.set_default_color_theme("green")

img_path=["photos/download18.jpeg",
     "photos/download19.jpeg",
     "photos/download20.jpeg",
     "photos/product_design.jpeg"]
img_index = 0
img_label = ctk.CTkLabel(app, text="")
img_label.pack(expand=False)

def clear_screen():
    for widget in app.winfo_children():
        try:
            widget.place_forget()
            widget.pack_forget()
        except AttributeError:
            continue  # تخطى الويدجت اللي مش بيدعم place/pack


def render_sidebar(products, picked_items, cart_position):
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

    loaded_icons = {
        key: ImageTk.PhotoImage(Image.open(path).resize((35, 35))) for key, path in icons.items()
    }
    loaded_icons["Wishlist"] = ImageTk.PhotoImage(Image.open(icons["Wishlist"]).resize((36, 36)))

    # أزرار رئيسية (7 فقط + Logout هنبقي نثبّته تحت)
    main_buttons = [
        {"text": "Dashboard", "image": loaded_icons["Dashboard"], "command": lambda: show_loading_screen()},
        {"text": "Categories", "image": loaded_icons["Categories"], "command": lambda: categories()},
        {"text": "Wishlist", "image": loaded_icons["Wishlist"], "command": lambda: wishlist()},
        {"text": "Location", "image": loaded_icons["Location"], "command": lambda: show_map_with_path(products, picked_items, cart_position)},
        {"text": "Order", "image": loaded_icons["Order"], "command": lambda: orders_page(cart_data=[])},
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

    # زر Logout في الأسفل
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
    global products, picked_items, cart_position
    clear_screen()
    render_sidebar(products, picked_items, cart_position)

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
            show_search_results(results)  # ← بدل عرضها في نفس الصفحة، ننتقل لصفحة نتائج
        except Exception as e:
            print("Search Error:", e)

    search_icon = ImageTk.PhotoImage(Image.open("photos/search.png").resize((27, 27)))
    search_entry = ctk.CTkEntry(app, placeholder_text="Search Product..", width=700, height=40, border_width=2,
                                fg_color="white", text_color="black", border_color="green")
    search_entry.place(x=590, y=10, anchor="n")

    search_button = ctk.CTkButton(app, image=search_icon, text="", width=100, height=30,
                                  fg_color="white", hover_color="#e0ffe0", command=perform_search)
    search_button.place(x=835, y=13)

from functools import partial
def show_search_results(results):
    global picked_items ,cart_position ,products
    clear_screen()
    render_sidebar(products=products, picked_items=picked_items, cart_position=cart_position)
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

        def load_image(url, label):
            try:
                response = requests.get(url)
                img = Image.open(io.BytesIO(response.content)).resize((100, 100))
                photo = ImageTk.PhotoImage(img)
                label.configure(image=photo, text="")
                label.image = photo
            except Exception as e:
                label.configure(text="Image Error")

        # ✅ استخدم partial لتمرير كل label مستقل
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
    global products, picked_items, cart_position
    clear_screen()
    render_sidebar(products, picked_items, cart_position)

    profile = api.get_profile()
    if not profile or not isinstance(profile, dict):
        messagebox.showerror("Error", "فشل جلب بيانات الملف الشخصي أو البيانات غير صحيحة")
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
        ctk.CTkLabel(row, text=f"{label}:", font=("Arial", 18, "bold"), text_color="black", width=140, anchor="w").pack(side="left")
        ctk.CTkLabel(row, text=str(value), font=("Arial", 18), text_color="green", anchor="w").pack(side="left")



def update_image():
    global img_index
    window_width = app.winfo_width()
    window_height = app.winfo_height()
    img = Image.open(img_path[img_index])
    img = img.resize((window_width, window_height))
    img_tk = ImageTk.PhotoImage(img)
    img_label.configure(image=img_tk)
    img_label.image = img_tk
    img_index = (img_index + 1) % len(img_path)
    app.after(2000, update_image)

def next_page():
    clear_screen()
    frame2 = ctk.CTkFrame(app, width=1080, height=90, fg_color="green", border_color="#006400",bg_color="green")
    frame2.place(x=0, y=0)
    image = r"photos/cart.jpeg"
    img = Image.open(image)
    img = img.resize((350, 440), Image.LANCZOS)
    photo = ImageTk.PhotoImage(img)
    l77 = ctk.CTkLabel(app, image=photo, text="")
    l77.place(x=25, y=100)
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
    b2=ctk.CTkButton(app,text="Login",bg_color="white",command=login_1,width=220, height=40,fg_color="green",
                       text_color="white",font=("Arial",20))
    b2.place(x=460,y=550)
    b4 = ctk.CTkButton(app, text="Scan",width=220, height=40,bg_color="white",fg_color="green",command=scan,
                       text_color="white", font=("Arial",20))
    b4.place(x=60, y=550)

    b3 = ctk.CTkButton(app, text="Sign Up",bg_color="white",fg_color="green",command=sign_up,
                       text_color="white"
                        ,width=220, height=40,font=("Arial",20))
    b3.place(x=840, y=550)



def show_map_with_path(products, picked_items, cart_pos,
                       bw_map_path="AStar/IMG/b&w.png", color_map_path="photos/map.png",
                       base_image_url=api.BASE_URL):
    clear_screen()
    app.geometry("1080x600")

    # إعداد الواجهة
    map_frame = tk.Frame(app, bg="green", width=680, height=580)
    map_frame.place(x=10, y=10)
    info_frame = tk.Frame(app, bg="white", width=380, height=580, highlightbackground="black", highlightthickness=2)
    info_frame.place(x=700, y=10)
    canvas = tk.Canvas(map_frame, width=680, height=560, bg="white")
    canvas.pack(padx=0, pady=10)

    resized_w, resized_h = 680, 560
    original_w, original_h = 550, 550
    scale_x = resized_w / original_w
    scale_y = resized_h / original_h

    # تحميل الخرائط
    bw_map = cv2.imread(bw_map_path, cv2.IMREAD_GRAYSCALE)
    color_map = cv2.imread(color_map_path)
    if bw_map is None or color_map is None:
        print("❌ BW Map or Color Map not found")
        return

    # رسم المسار فقط لو في منتجات عندها إحداثيات
    if isinstance(products, list) and any("x" in p and "y" in p for p in products):
        try:
            product_points = [(int(p["x"]), int(p["y"])) for p in products if "x" in p and "y" in p]
            cart_point = (int(cart_pos[0]), int(cart_pos[1]))
            exit_point = (40, 365)

            start = find_nearest_walkable(bw_map, cart_point)
            walkable_targets = [find_nearest_walkable(bw_map, pt) for pt in product_points]
            sorted_points = sort_points_by_path_distance(bw_map, start, walkable_targets)
            full_path = calculate_total_path(bw_map, [start] + sorted_points + [exit_point])

            if full_path:
                scaled_path = [(int(x * scale_x), int(y * scale_y)) for x, y in full_path]
                resized_color_map = cv2.resize(color_map.copy(), (resized_w, resized_h))

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

                color_map_rgb = cv2.cvtColor(resized_color_map, cv2.COLOR_BGR2RGB)
                img_pil = Image.fromarray(color_map_rgb)
                img_tk = ImageTk.PhotoImage(img_pil)
                canvas.create_image(0, 0, anchor="nw", image=img_tk)
                canvas.image = img_tk

                cart_img = Image.open("photos/cart.png").resize((30, 30), Image.LANCZOS)
                cart_photo = ImageTk.PhotoImage(cart_img)
                cart_x, cart_y = int(start[0] * scale_x), int(start[1] * scale_y)
                canvas.create_image(cart_x, cart_y, anchor="center", image=cart_photo)
                canvas.cart_photo = cart_photo
        except Exception as e:
            print("⚠️ رسم الخريطة فشل:", e)

    # دالة إنشاء الكارد
    def create_product_card(parent, item, border_color):
        frame = ctk.CTkFrame(parent, width=340, height=90, fg_color="white", border_color=border_color, border_width=2)
        frame.pack(pady=5, padx=5)

        image_path = base_image_url + item.get("image", "")
        try:
            img = Image.open(requests.get(image_path, stream=True, timeout=3).raw).resize((70, 70))
        except:
            img = Image.new("RGB", (70, 70), color="grey")
        img_tk = ImageTk.PhotoImage(img)

        img_label = tk.Label(frame, image=img_tk, bg="white")
        img_label.image = img_tk
        img_label.place(x=10, y=10)

        name = item.get("name", "Unknown")
        short_name = name[:28] + "..." if len(name) > 28 else name
        price = item.get("total_price", 0)

        tk.Label(frame, text=short_name, font=("Arial", 10, "bold"), bg="white", anchor="w").place(x=90, y=20)
        tk.Label(frame, text=f"{price} EGP", font=("Arial", 10), bg="white", fg=border_color).place(x=90, y=50)

    # ✅ EasyCartVirtualItems
    title1 = tk.Label(info_frame, text="EasyCartVirtualItems", font=("Arial", 14, "bold"), bg="white", fg="green")
    title1.place(x=10, y=5)
    virtual_frame = ctk.CTkScrollableFrame(info_frame, width=360, height=250, fg_color="white")
    virtual_frame.place(x=10, y=35)
    for item in products:
        create_product_card(virtual_frame, item, border_color="green")

    separator = tk.Frame(info_frame, bg="gray", height=2, width=360)
    separator.place(x=10, y=295)

    # ✅ EasyCartItems
    title2 = tk.Label(info_frame, text="EasyCartItems", font=("Arial", 14, "bold"), bg="white", fg="blue")
    title2.place(x=10, y=310)
    picked_frame = ctk.CTkScrollableFrame(info_frame, width=360, height=240, fg_color="white")
    picked_frame.place(x=10, y=340)
    for item in picked_items:
        create_product_card(picked_frame, item, border_color="blue")

    back_btn = ctk.CTkButton(app, text="Back", fg_color="green", bg_color="green", command=show_loading_screen,
                             text_color="white", width=220, corner_radius=20, border_color="white", border_width=5,
                             height=50, hover_color="#006400", font=("Arial", 20))
    back_btn.place(y=540, x=420)


def show_loading_screen():
    clear_screen()
    loading_frame = ctk.CTkFrame(app, width=1060, height=580, fg_color="white")
    loading_frame.place(x=10, y=10)
    loading_label = ctk.CTkLabel(loading_frame, text="Loading Dashboard...", font=("Arial", 30, "bold"), text_color="green")
    loading_label.place(relx=0.5, rely=0.5, anchor="center")
    def load_data_in_thread():
        try:
            product = api.get_all_products()
        except Exception as e:
            print("Error while loading:", e)
            product = []
        def render_dashboard():
            loading_frame.destroy()
            dashboard(product)
        app.after(0, render_dashboard)
    threading.Thread(target=load_data_in_thread, daemon=True).start()

def login_1():
    clear_screen()
    bottom_frame = ctk.CTkFrame(app, width=540, height=590, fg_color="transparent", border_width=2.5)
    bottom_frame.place(x=30, y=10)
    top_frame = ctk.CTkFrame(app, width=540, height=589, fg_color="green", border_width=2.5, bg_color="green",border_color="green")
    top_frame.place(x=550, y=10)
    ctk.CTkLabel(top_frame, text="🛒Easy Cart", font=("Times New Roman", 20, "bold"), text_color="white").place(x=20,y=15)
    ctk.CTkLabel(top_frame, text="Welcome Our Host!", font=("Arial", 30, "bold"), text_color="white",bg_color="green").place(x=140, y=80)
    ctk.CTkLabel(top_frame, text="Create your Account", font=("Times New Roman", 40, "bold"), text_color="white",bg_color="green").place(x=100, y=150)
    ctk.CTkLabel(bottom_frame, text="Sign In", font=("Arial", 30, "bold"), text_color="green").place(x=180, y=80)
    entries = {}
    y_pos = 130
    # Username Field
    ctk.CTkLabel(bottom_frame, text="Username", font=("Arial", 16), text_color="green").place(x=50, y=y_pos)
    username_entry = ctk.CTkEntry(bottom_frame, width=400, height=40, placeholder_text="Enter Username",text_color="black", fg_color="white")
    username_entry.place(x=50, y=y_pos + 30)
    entries["entry_username"] = username_entry
    y_pos += 80

    # Password Field + Show/Hide Button
    ctk.CTkLabel(bottom_frame, text="Password", font=("Arial", 16), text_color="green").place(x=50, y=y_pos)
    password_entry = ctk.CTkEntry(bottom_frame, width=400, height=40, placeholder_text="Enter Password",text_color="black", fg_color="white", show="*")
    password_entry.place(x=50, y=y_pos + 30)
    def toggle_password():
        if password_entry.cget("show") == "":
            password_entry.configure(show="*")
            eye_button.configure(text="Show")
        else:
            password_entry.configure(show="")
            eye_button.configure(text="Hide")

    eye_button = ctk.CTkButton(bottom_frame, text="Show", width=50, command=toggle_password, bg_color="white",text_color="green", fg_color="white", hover_color="white")
    eye_button.place(x=390, y=y_pos + 38)
    entries["password_entry"] = password_entry
    y_pos += 80

    result_label = ctk.CTkLabel(bottom_frame, text="", font=("Arial", 16), text_color="green")
    result_label.place(x=150, y=420)
    forgot_password_label = ctk.CTkLabel(bottom_frame, text="Forgot Password?",fg_color="transparent", text_color="green",bg_color="white", font=("Arial", 15, "bold"))
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
                    CTkMessagebox(title="Success", message=f"Welcome {username}، Your identity has been successfully verified✅", icon="check")
                    show_loading_screen()
                else:
                    messagebox.showerror("Error", f"Failed to login: {response.text}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        threading.Thread(target=do_login).start()


    login_button = ctk.CTkButton(bottom_frame, text="Login", command=login, fg_color="green", bg_color="white",
                       text_color="black", width=220, corner_radius=20,
                       height=50, hover_color="dark green", font=("Arial", 20))
    login_button.place(x=150, y=360)
    qr_login_button = ctk.CTkButton(bottom_frame, text="Login by QR",
                                    fg_color="white", text_color="green", border_width=2, border_color="green",
                                    width=220, corner_radius=20, height=50, hover_color="green",
                                    font=("Arial", 18, "bold"))
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


def scan():
    global products,picked_items,cart_position
    def start_camera():
        return cv2.VideoCapture(0)
    def stop_camera(cap):
        if cap and cap.isOpened():
            cap.release()
        cv2.destroyAllWindows()
    clear_screen()
    cap = start_camera()
    frame = ctk.CTkFrame(app, width=640, height=300, fg_color="white", corner_radius=10)
    frame.pack(pady=10, padx=20)
    title = ctk.CTkLabel(frame, text="Scan QR to Login", font=("Arial", 24, "bold"), text_color="green")
    title.pack(pady=(10, 10))
    video_label = ctk.CTkLabel(frame, text="")
    video_label.pack()
    def close_cam():
        stop_camera(cap)
        next_page()
    back_btn = ctk.CTkButton(frame, text="Back", command=close_cam, width=200, fg_color="green")
    back_btn.pack(pady=10)
    def update_frame():
        global products, picked_items , cart_position
        ret, img = cap.read()
        if ret:
            decoded = pyzbar.decode(img)
            for obj in decoded:
                QR = obj.data.decode("utf-8")
                stop_camera(cap)
                try:
                    products, picked_items = api.cart_cheek_in(QR)
                    if products:
                        show_map_with_path(products, picked_items, cart_position)
                    else:
                        messagebox.showerror("No Items", "No products found in cart.")
                except Exception as e:
                    messagebox.showerror("Error", str(e))
            frame_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(frame_rgb)
            imgtk = ImageTk.PhotoImage(image=img_pil)
            video_label.imgtk = imgtk
            video_label.configure(image=imgtk)
        video_label.after(10, update_frame)
    update_frame()

def orders_page(cart_data):
    clear_screen()
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

    sc = ctk.CTkScrollableFrame(app, width=1060, height=400,bg_color="white",fg_color="white")
    sc.place(x=10, y=70)

    btn = ctk.CTkButton(app, text="Location", width=220, height=45, fg_color="#388e3c", hover_color="#4caf50",
                        command=lambda: show_map_with_path(products, picked_items, cart_position))
    btn.place(x=610, y=570, anchor="center")
    btn = ctk.CTkButton(app, text="Back", width=220, height=45, fg_color="#388e3c", hover_color="#4caf50",
                        command= show_loading_screen)
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
        print(f"Updated total: {total}")
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
        ctk.CTkLabel(sc, text=product["name"], font=("Arial", 14), text_color="#222222").grid(row=i + 1, column=0, padx=10, pady=5)
        ctk.CTkLabel(sc, text=f"{product['price']:.2f}LE", font=("Arial", 14), text_color="#222222").grid(row=i + 1, column=1, padx=10, pady=5)

        quantity_var = tk.IntVar(value=product["quantity"])
        quantity_vars.append(quantity_var)

        frame_qty = ctk.CTkFrame(sc, fg_color="#e6f2e6")
        frame_qty.grid(row=i + 1, column=2, padx=10, pady=5)

        btn_minus = ctk.CTkButton(frame_qty, text="-", width=30, command=lambda idx=i: decrease_quantity(idx))
        btn_minus.pack(side="left")

        lbl_qty = ctk.CTkLabel(frame_qty, textvariable=quantity_var, width=30, anchor="center", text_color="#222222", fg_color="#e6f2e6")
        lbl_qty.pack(side="left", padx=5)

        btn_plus = ctk.CTkButton(frame_qty, text="+", width=30, command=lambda idx=i: increase_quantity(idx))
        btn_plus.pack(side="left")

        subtotal = product["quantity"] * product["price"]
        lbl_subtotal = ctk.CTkLabel(sc, text=f"{subtotal:.2f}LE", font=("Arial", 14), text_color="#222222")
        lbl_subtotal.grid(row=i + 1, column=3, padx=10, pady=5)
        subtotal_labels.append(lbl_subtotal)

        ctk.CTkLabel(sc, text=f"{product['weight']}g", font=("Arial", 14), text_color="#222222").grid(row=i + 1, column=4, padx=10, pady=5)

    update_total()

# class VerifyPage(ctk.CTkFrame):
#     def __init__(self, parent, api_url):
#         super().__init__(parent)
#         self.api_url = api_url
#         self.place(relwidth=1, relheight=1)  # مهم جداً لإظهار الصفحة
#         ctk.CTkLabel(self, text="Email Verification", font=("Arial", 20)).place(x=400, y=100)
#         self.code_entry = ctk.CTkEntry(self, width=200, height=80)
#         self.code_entry.place(x=500, y=200)
#         ctk.CTkButton(self, text="Done", command=self.perform_verify).place(x=500, y=260)
#     def perform_verify(self):
#         code = self.code_entry.get().strip()
#         if not code:
#             CTkMessagebox(title="خطأ", message="الرجاء إدخال كود التحقق", icon="warning")
#             return
#
#         try:
#             response = requests.post(self.api_url, json={"verificationCode": int(code)})
#             if response.status_code == 200:
#                 data = response.json()
#                 if data.get("access"):
#                     user_access_token=data.get("access")
#                     user_refresh_token = data.get("refresh")
#                     # print(session_data)
#                     CTkMessagebox(title="Success", message="Verification Done", icon="check")
#                     show_loading_screen()
#                 else:
#                     CTkMessagebox(title="Failed", message="Wrong Code Try Again!", icon="cancel")
#             else:
#                 CTkMessagebox(title="خطأ", message=f"خطأ من السيرفر: {response.status_code}", icon="cancel")
#         except ValueError:
#             CTkMessagebox(title="خطأ", message="كود التحقق يجب أن يكون رقمًا", icon="warning")
#         except requests.exceptions.RequestException as e:
#             CTkMessagebox(title="خطأ", message=f"فشل الاتصال: {str(e)}", icon="cancel")

# def sign_up():
#     clear_screen()
#     bottom_frame = ctk.CTkFrame(app, width=540, height=590, fg_color="transparent", border_width=2.5)
#     bottom_frame.place(x=550, y=10)
#     entries = {}
#     fields = [
#         ("Username", "username"),
#         ("First Name", "first_name"),
#         ("Last Name", "last_name"),
#         ("Email", "email"),
#         ("Password", "password", True)
#     ]
#     y_pos = 70
#     for label_text, key, *is_password in fields:
#         ctk.CTkLabel(bottom_frame, text=label_text, font=("Arial", 16), text_color="green").place(x=50, y=y_pos)
#         entry = ctk.CTkEntry(
#             bottom_frame, text_color="black",
#             width=400,
#             height=40,
#             placeholder_text=f"Enter {label_text}",
#             fg_color="white",
#             show="*" if is_password and is_password[0] else ""
#         )
#         entry.place(x=50, y=y_pos + 30)
#         entries[key] = entry
#         y_pos += 90
#
#     def perform_signup():
#         data = {k: e.get().strip() for k, e in entries.items()}
#
#         if not all(data.values()):
#             CTkMessagebox(title="Error", message="Please fill in all fields.", icon="warning")
#             return
#
#         try:
#             res = api.register_user(
#                 data["username"],
#                 data["first_name"],
#                 data["last_name"],
#                 data["email"],
#                 data["password"]
#             )
#             CTkMessagebox(title="Success", message=res.get("message", "Registered Successfully"), icon="check")
#
#             VerifyPage(app, api_url=f"{BASE_URL}/user/verify/")
#
#
#         except Exception as e:
#             CTkMessagebox(title="Signup Failed", message=str(e), icon="cancel")
#
#     ctk.CTkButton(bottom_frame, text="Create Account", command=perform_signup,
#                   fg_color="green", hover_color="dark green", text_color="white",
#                   width=220, height=45, font=("Arial", 18)).place(x=160, y=520)
#     top_frame = ctk.CTkFrame(app, width=545, height=589, fg_color="green", border_width=2.5, bg_color="green",
#                              border_color="green")
#     top_frame.place(x=30, y=10)
#
#     l1 = ctk.CTkLabel(top_frame, text="🛒Easy Cart", font=("Times New Roman", 20, "bold"), text_color="white")
#     l1.place(x=10, y=15)
#     l2=ctk.CTkLabel(top_frame, text="Hey There!", font=("Arial", 30, "bold"), text_color="white")
#     l2.place(x=150, y=80)
#     l3=ctk.CTkLabel(top_frame, text="Welcome Back!", font=("Arial", 40, "bold"), text_color="white", bg_color="green")
#     l3.place(x=80, y=150)
#     l4=ctk.CTkLabel(top_frame, text="Sign in to your account", font=("Arial", 25), text_color="white", bg_color="green")
#     l4.place(x=110, y=220)
#     l5=ctk.CTkLabel(bottom_frame, text="Sign Up", font=("Arial", 30, "bold"), text_color="green")
#     l5.place(x=220, y=30)
#     l6=ctk.CTkButton(top_frame, text="Sign In", command=login_1, fg_color="green", bg_color="green",
#                   text_color="white", width=220, corner_radius=20, border_color="white", border_width=5,
#                   height=50, hover_color="#006400", font=("Arial", 20))
#     l6.place(y=340, x=100)
#
#     l7=ctk.CTkButton(top_frame, text="Back", command=next_page, fg_color="green", bg_color="green",
#                   text_color="white", width=220, corner_radius=20, border_color="white", border_width=5,
#                   height=50, hover_color="#006400", font=("Arial", 20))
#     l7.place(y=430, x=100)

class VerifyPage(ctk.CTkFrame):
    def __init__(self, parent, api_url):
        super().__init__(parent)
        self.api_url = api_url
        self.place(relwidth=1, relheight=1)
        self.configure(fg_color="white")

        # === عنوان رئيسي ===
        ctk.CTkLabel(self, text="🔐 Email Verification", font=("Arial", 30, "bold"),
                     text_color="green").place(relx=0.5, y=100, anchor="center")

        # === مربع إدخال الكود ===
        ctk.CTkLabel(self, text="Enter your verification code:", font=("Arial", 18),
                     text_color="black").place(relx=0.5, y=180, anchor="center")

        self.code_entry = ctk.CTkEntry(self, width=300, height=50, font=("Arial", 18),
                                       fg_color="white", text_color="black", border_color="green", border_width=2)
        self.code_entry.place(relx=0.5, y=230, anchor="center")

        # === زر الإرسال ===
        ctk.CTkButton(self, text="✅ Verify", command=self.perform_verify,
                      font=("Arial", 18, "bold"),
                      width=200, height=45,
                      fg_color="green", hover_color="dark green", text_color="white").place(relx=0.5, y=300, anchor="center")

        # === زر العودة (اختياري) ===
        ctk.CTkButton(self, text="← Back", command=next_page,
                      font=("Arial", 16),
                      fg_color="white", hover_color="#d0ffd0", text_color="green", width=120).place(x=20, y=20)

    def perform_verify(self):
        code = self.code_entry.get().strip()
        if not code:
            CTkMessagebox(title="خطأ", message="الرجاء إدخال كود التحقق", icon="warning")
            return

        try:
            response = requests.post(self.api_url, json={"verificationCode": int(code)})
            if response.status_code == 200:
                data = response.json()
                if data.get("access"):
                    global user_access_token, user_refresh_token
                    user_access_token = data.get("access")
                    user_refresh_token = data.get("refresh")
                    api.session.headers.update({"Authorization": f"Bearer {user_access_token}"})
                    api.refresh_token=user_refresh_token
                    CTkMessagebox(title="Success", message="✅ Verification Done", icon="check")
                    show_loading_screen()
                else:
                    CTkMessagebox(title="Failed", message="❌ Wrong Code, Try Again", icon="cancel")
            else:
                CTkMessagebox(title="Error", message=f"Server Error: {response.status_code}", icon="cancel")
        except ValueError:
            CTkMessagebox(title="خطأ", message="❗ كود التحقق يجب أن يكون رقمًا", icon="warning")
        except requests.exceptions.RequestException as e:
            CTkMessagebox(title="Connection Error", message=f"❌ {str(e)}", icon="cancel")


def sign_up():
    clear_screen()
    # === Top Frame (Left - Welcome) ===
    top_frame = ctk.CTkFrame(app, width=500, height=580, fg_color="green")
    top_frame.place(x=30, y=10)

    ctk.CTkLabel(top_frame, text="🛒 Easy Cart", font=("Times New Roman", 26, "bold"), text_color="white").place(x=20, y=20)
    ctk.CTkLabel(top_frame, text="Welcome!", font=("Arial", 30, "bold"), text_color="white").place(x=150, y=100)
    ctk.CTkLabel(top_frame, text="Create your account easily", font=("Arial", 20), text_color="white").place(x=90, y=160)

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

    frame = ctk.CTkFrame(parent, width=200, height=350, fg_color="white", border_color="green", border_width=2,bg_color="transparent")
    frame.grid(row=row, column=col, padx=20, pady=15)
    # زر القلب (wishlist)
    wishlist_state = ctk.StringVar(value="♡")  # شكل القلب الافتراضي


    wishlist_btn = ctk.CTkButton(
        frame,
        textvariable=wishlist_state,
        width=30,
        height=30,
        font=("Arial", 30,"bold"),
        fg_color="transparent",bg_color="white",
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

    # عنصر الصورة (مكان فارغ ليتم تحديثه لاحقًا)
    image_label = ctk.CTkLabel(frame, text="Loading...", width=150, height=150)
    image_label.place(x=15, y=5)

    # عرض الاسم
    label = ctk.CTkLabel(frame, text=title, font=("Arial", 16, "bold"), text_color="green",
                         fg_color="white", wraplength=160, justify="center")
    label.place(x=10, y=170)

    # عرض الوزن
    weight_label = ctk.CTkLabel(frame, text=f"Weight : {weight} Kg", font=("Arial", 14), text_color="green")
    weight_label.place(x=10, y=weight_y)

    if discount > 0:
        discounted_price = price * (1 - discount / 100)
        # السعر المخفض
        discounted_label = ctk.CTkLabel(frame, text=f"Discounted Price {discounted_price:.2f}EGP",
                                        font=("Arial", 12, "bold"), text_color="black")
        discounted_label.place(x=5, y=220)

        # السعر الأصلي مشطوب
        price_label = ctk.CTkLabel(frame, text=f"Price {price:.2f} LE", font=("Arial", 14, "overstrike", "bold"),
                                   text_color="red")
        price_label.place(x=10, y=price_y)
    else:
        # السعر العادي
        price_label = ctk.CTkLabel(frame, text=f"Price {price:.2f} LE", font=("Arial", 14, "bold"),
                                   text_color="black")
        price_label.place(x=10, y=price_y)

    # تقييم المنتج
    def get_stars(rate):
        full_stars = int(rate)  # عدد النجوم المكتملة
        half_star = (rate - full_stars) >= 0.5  # هل هناك نصف نجمة؟
        empty_stars = 5 - full_stars - (1 if half_star else 0)

        stars = "★" * full_stars
        if half_star:
            stars += "☆"  # بديل لنصف نجمة
        stars += "☆" * empty_stars

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

    # تحديث حالة الأزرار
    def update_button():
        qty = quantity.get()
        if qty == 0:
            # إظهار زر Add to Cart فقط
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
    add_cart_btn = ctk.CTkButton(frame, text="Add to Cart", width=140, command=add_to_cart,fg_color="green",hover_color="dark green")
    add_cart_btn.place(x=25, y=300)
    plus_btn = ctk.CTkButton(frame, text="+", width=30, command=increase_qty,fg_color="green",hover_color="dark green")
    minus_btn = ctk.CTkButton(frame, text="-", width=30, command=decrease_qty,fg_color="green",hover_color="dark green")
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
            photo_img = ImageTk.PhotoImage(img)
            image_label.configure(image=photo_img, text="")  # إزالة النص "Loading..."
            image_label.image = photo_img
        except Exception as e:
            print(f"Error loading product image: {e}")

    if image_bytes or image_url:
        threading.Thread(target=load_and_update_image, daemon=True).start()

from customtkinter import CTkImage
from PIL import Image

def dashboard(dashproducts=None):
    global picked_items ,cart_position ,products
    clear_screen()
    render_sidebar(products=products, picked_items=picked_items, cart_position=cart_position)
    # Search bar
    render_searchbar()
    ctk.CTkLabel(app, text="Popular Products", font=("Times New Roman", 30, "bold"), bg_color="white",
                 fg_color="white", text_color="black").place(x=220, y=80)

    sc = ctk.CTkScrollableFrame(app, width=750, height=475, bg_color="white", fg_color="white",
                                scrollbar_fg_color="white", scrollbar_button_hover_color="dark green",
                                scrollbar_button_color="#388e3c")
    sc.place(x=200, y=120)

    # 🧠 تحميل المنتجات إن لم تكن موجودة مسبقًا
    if dashproducts is None:
        try:
            dashproducts = api.get_all_products()
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
            print("❌ Logout error:", e)
    b_yes = ctk.CTkButton(app, text="Yes",
                          command=confirm_logout,  # ← مربوطة بدالة تسجل الخروج
                          bg_color="white", fg_color="green",
                          text_color="white", width=220,
                          height=45, hover_color="#006400", font=("Arial", 20))
    b_yes.place(x=250, y=250)
    b_no = ctk.CTkButton(app, text="No",
                         command=show_loading_screen,  # ← رجوع للداشبورد بشكل صحيح
                         bg_color="white", fg_color="green",
                         text_color="white", width=220,
                         height=45, font=("Arial", 20))
    b_no.place(x=600, y=250)

def nfc():
    clear_screen()
    frame = ctk.CTkFrame(app, width=1060, height=580, fg_color="white", border_color="green", border_width=1)
    frame.place(x=10, y=10)
    frame.image_refs = []
    header = ctk.CTkFrame(frame, width=1060, height=80, fg_color="green")
    header.place(x=0, y=0)
    title = ctk.CTkLabel(header, text="⬅ Go back to Payment ", font=("Times New Roman", 35, "bold"),
                         text_color="white", fg_color="transparent", cursor="hand2")
    title.place(x=200, y=15, anchor="n")
    title.bind("<Button-1>",lambda event: checkout())

    label_status = ctk.CTkLabel(frame, text="", font=("Arial", 14))
    label_status.place(x=50, y=350)

    img_path = "photos/nfc.png"
    try:
        img = Image.open(img_path).resize((250, 250), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        nfc_label = ctk.CTkLabel(frame, text="", image=photo)
        nfc_label.image = photo
        nfc_label.place(x=800, y=150)
    except FileNotFoundError:
        label_status.configure(text="Image not found: " + img_path, text_color="red")

    ctk.CTkLabel(frame, text="Tap your card or phone on the NFC reader", font=("Arial", 30, "bold"),
                 text_color="black").place(x=50, y=150)
    def display_invoice(data):
        invoice = data.get("invoice", {})

        invoice_window = ctk.CTkToplevel()
        invoice_window.title("Invoice")
        invoice_window.geometry("600x500")
        invoice_window.configure(fg_color="white")

        ctk.CTkLabel(invoice_window, text="🧾 Invoice Details", font=("Arial", 24, "bold"),
                     text_color="green").pack(pady=10)

        ctk.CTkLabel(invoice_window, text=f"Total Amount: {invoice.get('totalAmount', 'N/A')} EGP",
                     font=("Arial", 16)).pack()
        ctk.CTkLabel(invoice_window, text=f"Total Weight: {invoice.get('totalWeight', 'N/A')} g",
                     font=("Arial", 16)).pack()
        ctk.CTkLabel(invoice_window, text=f"Total Quantity: {invoice.get('totalQuantity', 'N/A')} items",
                     font=("Arial", 16)).pack()
        ctk.CTkLabel(invoice_window, text=f"Payment Method: {invoice.get('paymentMethod', 'N/A')}",
                     font=("Arial", 16)).pack()
        ctk.CTkLabel(invoice_window, text=f"Date: {invoice.get('createdAt', 'N/A')}", font=("Arial", 16)).pack(pady=10)

        ctk.CTkLabel(invoice_window, text="Items:", font=("Arial", 18, "bold")).pack(pady=5)

        items_frame = ctk.CTkScrollableFrame(invoice_window, width=500, height=250, fg_color="#f5f5f5")
        items_frame.pack(pady=5)

        items = invoice.get("items", {})
        for key, item in items.items():
            product = item.get("product", {})
            product_name = product.get("ProductName", "Unknown")
            quantity = item.get("quantity", 0)
            price = item.get("total_price", 0)
            weight = item.get("total_weight", 0)

            item_text = f"🛒 {product_name} | Qty: {quantity} | Price: {price} EGP | Weight: {weight}g"
            ctk.CTkLabel(items_frame, text=item_text, font=("Arial", 14), anchor="w", justify="left").pack(fill="x", pady=2)
    def send_nfc_transaction():
        label_status.configure(text="Processing NFC transaction...", text_color="orange")

        nfc_transaction_id = "nfc-123456789"

        try:
            response = requests.post("http://127.0.0.1:8000/cart/EasyCartchechout/", json={
                "nfc_transaction_id": nfc_transaction_id,
                "payment_method": "Card NFC"
            })

            if response.status_code == 200:
                data = response.json()
                label_status.configure(
                    text="✅ " + data.get("detail", "Success"),
                    text_color="green", font=("Arial", 18, "bold")
                )
                display_invoice(data)
            else:
                label_status.configure(
                    text="❌ Error: " + response.json().get("detail", "Unknown error"),
                    text_color="red"
                )
        except Exception as e:
            label_status.configure(text="❌ Connection error: " + str(e), text_color="red")

    ctk.CTkButton(frame, text="Start Scanning", command=send_nfc_transaction,
                  fg_color="green", height=50).place(x=50, y=250)

def checkout():
    clear_screen()
    frame8 = ctk.CTkFrame(app, width=1060, height=580, fg_color="white", border_color="green", border_width=1)
    frame8.place(x=10, y=10)
    frame8.image_refs = []
    title = ctk.CTkLabel(app, text="⬅Back", font=("Times New Roman", 25, "bold"),
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
        photo = ImageTk.PhotoImage(img)
        btn = ctk.CTkButton(frame8, text="", fg_color="transparent", bg_color="white",
                            image=photo, compound="left", border_width=2,
                            border_color="white", text_color="black", width=150, height=100,
                            hover_color="#3CB371", font=("Arial", 20), command=cmd)
        btn.image = photo
        btn.place(relx=x_rel, y=190, anchor="center")
        frame8.image_refs.append(photo)

    create_button("photos/credit1.png", 0.6, credit)
    create_button("photos/NFC 1.png", 0.4, nfc)

def categories():
    global products, picked_items, cart_position
    clear_screen()
    render_sidebar(products, picked_items, cart_position)
    render_searchbar()
    l1 = ctk.CTkLabel(app, text="Categories", font=("Times New Roman", 30, "bold"), text_color="black", fg_color="white")
    l1.place(x=280, y=70, anchor="n")
    l1.is_main_title = True
    def load_image_from_url_cat(image_url, size=(100, 100), callback=None):
        def load_image():
            try:
                response = requests.get(f"{api.BASE_URL}{image_url}")
                img = Image.open(io.BytesIO(response.content)).resize(size, Image.LANCZOS)
                photo_image = ImageTk.PhotoImage(img)
                if callback:
                    callback(photo_image)
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
    global products, picked_items, cart_position
    clear_screen()
    render_sidebar(products, picked_items, cart_position)
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
            image = Image.open(io.BytesIO(response.content)).resize((100, 100))
            photo = ImageTk.PhotoImage(image)
            label.configure(image=photo, text="")
            label.image = photo
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

        # صورة مؤقتة بنص "Loading..."
        image_label = ctk.CTkLabel(frame, text="Loading...", width=100, height=100, fg_color="white", text_color="gray")
        image_label.place(x=50, y=10)

        # تحميل الصورة في thread
        threading.Thread(target=load_image, args=(image_url, image_label), daemon=True).start()

        # زر الـ wishlist
        wishlist_state = ctk.StringVar(value="♡")
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
            stars = "★" * full_stars
            if half_star:
                stars += "☆"
            stars += "☆" * empty_stars
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
                                 command=lambda p=product: open_product(p,category_name),
                                 fg_color="green", hover_color="dark green")

        add_cart.place(x=5, y=10)

def open_product(product ,category_name):
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
    image_frame.place(x=20,y=100)

    img_label = tk.Label(image_frame, text="Loading image...", bg="white")
    img_label.pack()

    def load_img():
        try:
            image_url = product.get("ProductImage", "")
            if image_url:
                response = requests.get(f"{api.BASE_URL}{image_url}")
                response.raise_for_status()
                img = Image.open(io.BytesIO(response.content)).resize((250, 250))
                photo = ImageTk.PhotoImage(img)
                img_label.configure(image=photo, text="")
                img_label.image = photo
            else:
                img_label.configure(text="No image available")
        except Exception as e:
            img_label.configure(text=f"Image error: {e}")

    threading.Thread(target=load_img, daemon=True).start()

    # ====== Product Info on the Right ======
    info_frame = tk.Frame(main_frame, bg="white")
    info_frame.place(x=350,y=50)

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

    ctk.CTkButton(btn_frame, text="Add to Cart", command=add_to_cart, width=150, fg_color="green").pack(side="left",pady=10,
                                                                                                        padx=10)
    ctk.CTkButton(btn_frame, text="♥", command=toggle_wishlist, width=60, fg_color="red").pack(side="left", padx=10,pady=5)

# def location():
#     clear_screen()
#     map_frame = tk.Frame(app, bg="green", width=700, height=580)
#     map_frame.place(x=10, y=10)
#     order_frame = tk.Frame(app, bg="lightgrey", width=460, height=580)
#     order_frame.place(x=720, y=10)
#     canvas = tk.Canvas(map_frame, width=680, height=560, bg="white")
#     canvas.pack(padx=10, pady=10)
#     original_img = Image.open("photos/map.png")
#     original_width, original_height = original_img.size
#     max_width, max_height = 680, 560
#     ratio = min(max_width / original_width, max_height / original_height)
#     img_size = [int(original_width * ratio), int(original_height * ratio)]
#     resized_img = original_img.resize(img_size, Image.LANCZOS)
#     photo = ImageTk.PhotoImage(resized_img)
#     canvas.create_image(0, 0, anchor="nw", image=photo)
#     canvas.photo = photo
#     room_width_m = 5.0
#     room_height_m = 5.0
#     pixel_per_meter_x = img_size[0] / room_width_m
#     pixel_per_meter_y = img_size[1] / room_height_m
#     cart_img = Image.open("photos/cart.png").resize((30, 30), Image.LANCZOS)
#     cart_photo = ImageTk.PhotoImage(cart_img)
#     tx_icon = canvas.create_image(0, 0, anchor="center", image=cart_photo)
#     canvas.cart_photo = cart_photo
#     def move_cart(x_meters, y_meters):
#         x_px = x_meters * pixel_per_meter_x
#         y_px = img_size[1] - (y_meters * pixel_per_meter_y)
#         canvas.coords(tx_icon, x_px, y_px)
#     order_title = tk.Label(order_frame, text="Order Items", font=("Arial", 18), bg="green")
#     order_title.pack(pady=10)
#     order_listbox = tk.Listbox(order_frame, font=("Arial", 14), width=40, height=25)
#     order_listbox.pack(padx=10, pady=10)
#     cart_items = []
#     def update_order_list():
#         order_listbox.delete(0, tk.END)
#         for item in cart_items:
#             order_listbox.insert(tk.END, item)
#     def simulate_new_item_entry():
#         import random
#         x = round(random.uniform(0, 5), 2)
#         y = round(random.uniform(0, 5), 2)
#         new_item = f"Item {len(cart_items)+1} at ({x},{y})"
#         cart_items.append(new_item)
#         move_cart(x, y)
#         update_order_list()
#         app.after(5000, simulate_new_item_entry)
#     simulate_new_item_entry()
#     b22 = ctk.CTkButton(app, text="Back", fg_color="green", bg_color="green", command=show_loading_screen,
#                         text_color="white", width=220, corner_radius=20, border_color="white", border_width=5,
#                         height=50, hover_color="#006400", font=("Arial", 20))
#     b22.place(y=500, x=160)


def wishlist():
    clear_screen()
    HEADERS = {"Authorization": f"Token {user_access_token}"}
    BASE_URL = "https://shehab123.pythonanywhere.com"
    wishlist_qrs = set()
    products = []
    global picked_items ,cart_position
    clear_screen()
    render_sidebar(products={}, picked_items=picked_items, cart_position=cart_position)
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
            res = requests.get(f"{BASE_URL}/product/wishlist/getmywish/", headers=HEADERS)
            if res.status_code == 200:
                wishlist_qrs = {item['QRNumber'] for item in res.json()}
            else:
                print("Failed to load wishlist", res.status_code)
        except Exception as e:
            print("Error:", e)

    def load_products():
        nonlocal products
        try:
            res = requests.get(f"{BASE_URL}/product/getall/", headers=HEADERS)
            if res.status_code == 200:
                products = res.json()
                display_products()
            else:
                print("Failed to load products", res.status_code)
        except Exception as e:
            print("Error:", e)

    def add_to_wishlist(qr):
        try:
            res = requests.post(f"{BASE_URL}/product/wishlist/add/{{QRNumber}}//", headers=HEADERS)
            return res.status_code == 200
        except:
            return False

    def remove_from_wishlist(qr):
        try:
            res = requests.delete(f"{BASE_URL}/product/wishlist/remove/{{QRNumber}}//", headers=HEADERS)
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
            ctk.CTkButton(frame, text=btn_text, width=150, command=lambda p=product: toggle_wishlist(p)).pack(side="right", padx=10)

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
            ctk.CTkButton(frame, text="Remove from Wishlist", width=150, command=lambda p=product: toggle_wishlist(p)).pack(side="right", padx=10)

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