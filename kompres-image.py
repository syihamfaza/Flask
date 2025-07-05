from PIL import Image
import os

def compress_images(input_folder, output_folder, quality=70, max_size=(1024, 1024)):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for filename in os.listdir(input_folder):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            file_path = os.path.join(input_folder, filename)
            img = Image.open(file_path)

            # Resize jika gambar lebih besar dari max_size
            img.thumbnail(max_size)

            # Kompres dan simpan
            output_path = os.path.join(output_folder, filename)
            img.save(output_path, optimize=True, quality=quality)
            print(f"✅ {filename} dikompres dan disimpan ke {output_path}")

# Contoh pemakaian
input_folder = "C:\\Users\\Admin\\Downloads\\Dokumentasi"
output_folder = "C:\\Users\\Admin\\Downloads\\Dokumentasi\\Result"
compress_images(input_folder, output_folder)
