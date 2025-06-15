from back import ProductManager

def main():
    manager = ProductManager()
    qr = input("Enter QR number: ")
    print("\n--- Product JSON ---")
    json_data = manager.get_product_json(qr)
    print(json_data)
    print("\n--- Showing Image ---")
    product = manager.get_product_by_qr(qr)
    if product:
        manager.show_product_image(product)
    else:
        print("Product not found.")

if __name__ == "__main__":
    main()
