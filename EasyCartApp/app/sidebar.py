import customtkinter as ctk

class Sidebar:
    def __init__(self, root, callbacks: dict):
        self.root = root
        self.callbacks = callbacks

    def render(self):
        frame = ctk.CTkFrame(self.root, width=200, height=600, fg_color="white", border_color="green", border_width=1)
        frame.place(x=0, y=0)

        # Add buttons
        button_config = {
            "Dashboard": self.callbacks.get("dashboard", lambda: None),
            "Categories": self.callbacks.get("categories", lambda: None),
            "Wishlist": self.callbacks.get("wishlist", lambda: None),
            "Location": self.callbacks.get("location", lambda: None),
            "Order": self.callbacks.get("order", lambda: None),
            "Checkout": self.callbacks.get("checkout", lambda: None),
            "Account": self.callbacks.get("account", lambda: None),
            "Logout": self.callbacks.get("logout", lambda: None),
        }

        y = 80
        for label, command in button_config.items():
            btn = ctk.CTkButton(self.root, text=label, fg_color="white", text_color="green", command=command)
            btn.place(x=10, y=y)
            y += 50
