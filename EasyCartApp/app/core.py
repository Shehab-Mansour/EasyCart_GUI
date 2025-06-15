import customtkinter as ctk

class EasyCartApp:
    def __init__(self):
        self.app = ctk.CTk()
        self.app.title("Easy Cart")
        self.app.geometry("1080x600")
        self.app.configure(fg_color="white")
        ctk.set_default_color_theme("green")

    def run(self):
        self.app.mainloop()
