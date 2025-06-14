import customtkinter as ctk
from tkinter import Tk
from PIL import Image, ImageTk

app = ctk.CTk()
app.geometry("1080x600")
app.configure(fg_color="white")
ctk.set_default_color_theme("green")

# Dummy data
products = []
picked_items = []
cart_position = (70, 115)

def render_sidebar(products, picked_items, cart_position):
    def on_enter(event, button):
        button.configure(text_color="white", fg_color="dark green")
    def on_leave(event, button):
        button.configure(text_color="green", fg_color="white")

    frame_width = 200
    frame = ctk.CTkFrame(app, width=frame_width, height=580, fg_color="white",
                         border_color="green", border_width=2.5)
    frame.place(x=1080 - frame_width, y=10)  # Align right

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
        "Account": "photos/2.jpeg",
        "LogOut": "photos/logout.png"
    }
    loaded_icons = {
        key: ImageTk.PhotoImage(Image.open(path).resize((30, 30))) for key, path in icons.items()
    }
    loaded_icons["Wishlist"] = ImageTk.PhotoImage(Image.open(icons["Wishlist"]).resize((40, 40)))

    # Button height + spacing
    button_count = 8
    total_height = 600
    button_height = 50
    spacing = (total_height - (button_height * button_count)) // (button_count + 1)

    button_configs = [
        {"text": "Dashboard", "image": loaded_icons["Dashboard"], "command": lambda: print("Dashboard")},
        {"text": "Categories", "image": loaded_icons["Categories"], "command": lambda: print("Categories")},
        {"text": "Wishlist", "image": loaded_icons["Wishlist"], "command": lambda: print("Wishlist")},
        {"text": "Location", "image": loaded_icons["Location"], "command": lambda: print("Location")},
        {"text": "Order", "image": loaded_icons["Order"], "command": lambda: print("Order")},
        {"text": "Checkout", "image": loaded_icons["Checkout"], "command": lambda: print("Checkout")},
        {"text": "Account", "image": loaded_icons["Account"], "command": lambda: print("Account")},
        {"text": "LogOut", "image": loaded_icons["LogOut"], "command": lambda: print("Logout")}
    ]

    for i, config in enumerate(button_configs):
        y_position = 60 + spacing + i * (button_height + spacing)
        btn = ctk.CTkButton(frame, text=config["text"], image=config["image"],
                            compound="left", fg_color="white", bg_color="white",
                            text_color="green", hover_color="#006400",
                            font=("Arial", 20), width=180, height=button_height,
                            corner_radius=20, command=config["command"])
        btn.place(x=10, y=y_position)
        btn.bind("<Enter>", lambda e, b=btn: on_enter(e, b))
        btn.bind("<Leave>", lambda e, b=btn: on_leave(e, b))

# استدعاء القائمة الجانبية
render_sidebar(products, picked_items, cart_position)

app.mainloop()
