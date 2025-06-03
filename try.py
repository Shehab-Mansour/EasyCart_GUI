# import customtkinter as ctk
# from PIL import Image, ImageTk
# import cv2
# import os
# 
# app = ctk.CTk()
# app.title("Cart Program")
# 
# 
# screen_width = app.winfo_screenwidth()
# screen_height = app.winfo_screenheight()
# app.geometry("1080x600")
# app.configure(fg_color="white")
# ctk.set_default_color_theme("green")
# 
# 
# img_path = [
#     "photos/download_18.jpeg",
#     "photos/download_19.jpeg",
#     "photos/product_design.jpeg",
#     "photos/download_20.jpeg"
# ]
# 
# img_index = 0
# 
# img_label = ctk.CTkLabel(app, text="")
# img_label.pack(expand=True, fill="both")
# 
# 
# l = ctk.CTkLabel(app, text=" X ", text_color="white", font=("Arial", 30, "bold"),
#                  bg_color="transparent", fg_color="black", corner_radius=0)
# l.place(x=app.winfo_width() + 790, y=10, anchor="nw")
# 
# 
# def update_image():
#     global img_index
#     window_width = app.winfo_width()
#     window_height = app.winfo_height()
#     img = Image.open(img_path[img_index])
#     img = img.resize((window_width, window_height))
#     img_tk = ImageTk.PhotoImage(img)
#     img_label.configure(image=img_tk)
#     img_label.image = img_tk
#     img_index = (img_index + 1) % len(img_path)
#     app.after(2000, update_image)
# 
# 
# update_image()
# app.mainloop()
#


import customtkinter as ctk
from PIL import Image
import os

app = ctk.CTk()
app.title("Cart Program")
screen_width = app.winfo_screenwidth()
screen_height = app.winfo_screenheight()
app.geometry("1080x600")
app.configure(fg_color="white")
ctk.set_default_color_theme("green")

img_path = [
    "photos/download_18.jpeg",
    "photos/download_19.jpeg",
    "photos/product_design.jpeg",
    "photos/download_20.jpeg"
]

img_index = 0
img_label = ctk.CTkLabel(app, text="")
img_label.pack(expand=True, fill="both")

l = ctk.CTkLabel(app, text=" X ", text_color="white", font=("Arial", 30, "bold"),
                 bg_color="transparent", fg_color="black", corner_radius=0)
l.place(x=app.winfo_width() + 790, y=10, anchor="nw")

def update_image():
    global img_index
    window_width = app.winfo_width()
    window_height = app.winfo_height()
    
    # ????? ?????? ???????? ??? CTkImage
    pil_img = Image.open(img_path[img_index])
    ctk_img = ctk.CTkImage(light_image=pil_img, size=(window_width, window_height))
    
    img_label.configure(image=ctk_img)
    img_label.image = ctk_img  # ???? ????? ??? ???? ??????
    
    img_index = (img_index + 1) % len(img_path)
    app.after(2000, update_image)

update_image()
app.mainloop()
