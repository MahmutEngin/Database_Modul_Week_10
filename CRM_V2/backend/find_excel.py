import os
import re

def get_latest_vit_folder(base_path="data"):
    """
    Belirtilen ana dizin (varsayılan olarak 'data' klasörü) altında 'VIT' ile başlayan klasörleri bulur
    ve en yüksek sayıya sahip olanın tam yolunu döndürür (örn. VIT1, VIT2, VIT3 -> data/VIT3).
    Eğer base_path yoksa veya hiç VIT klasörü bulunamazsa None döndürür.
    """
    if not os.path.isdir(base_path):
        print(f"Uyarı: '{base_path}' dizini bulunamadı. VIT klasörleri aranmıyor.")
        return None

    vit_folders = []
    for name in os.listdir(base_path):
        full_path = os.path.join(base_path, name) # Tam yolu oluştur
        if os.path.isdir(full_path): # Bir dizin olduğundan emin ol
            match = re.match(r"VIT(\d+)", name)
            if match:
                vit_folders.append((int(match.group(1)), name))

    if not vit_folders:
        print(f"Uyarı: '{base_path}' dizini içinde hiçbir VIT klasörü bulunamadı.")
        return None

    # En büyük numaralı VIT klasörünü bul
    latest_vit_folder_name = max(vit_folders, key=lambda x: x[0])[1]
    latest_vit_path = os.path.join(base_path, latest_vit_folder_name)
    
    return latest_vit_path

def get_excel_files_from_latest_vit(base_path="data"):
    """
    Belirtilen ana dizin altındaki en son VIT klasöründen tüm Excel dosyalarını ('.xlsx') bulur.
    Dosya adlarını (uzantısız) anahtar, tam yollarını değer olarak içeren bir sözlük döndürür.
    En son VIT klasörü bulunamazsa veya içinde Excel dosyası yoksa boş bir sözlük döndürür.
    """
    latest_folder_path = get_latest_vit_folder(base_path)
    
    excel_files = {}
    if latest_folder_path and os.path.isdir(latest_folder_path): # Klasörün varlığını kontrol et
        for file_name in os.listdir(latest_folder_path):
            if file_name.endswith(".xlsx"):
                key = os.path.splitext(file_name)[0] # Uzantısız dosya adı
                excel_files[key] = os.path.join(latest_folder_path, file_name)
    elif not latest_folder_path:
        print(f"Uyarı: Excel dosyaları için en son VIT klasörü bulunamadı.")

    return excel_files

# Örnek Kullanım (opsiyonel olarak main bloğunda test edilebilir)
if __name__ == "__main__":
    # Test için 'data' klasöründe bazı VIT klasörleri ve dosyalar oluşturabilirsiniz
    # Örn:
    # os.makedirs("data/VIT1", exist_ok=True)
    # os.makedirs("data/VIT2", exist_ok=True)
    # with open("data/VIT1/test1.xlsx", "w") as f: f.write("test")
    # with open("data/VIT2/test2.xlsx", "w") as f: f.write("test")
    # os.makedirs("data/VIT3", exist_ok=True)
    # with open("data/VIT3/Basvurular.xlsx", "w") as f: f.write("test")
    # with open("data/VIT3/Mulakatlar.xlsx", "w") as f: f.write("test")


    print("En son VIT klasörü aranıyor...")
    latest_vit_folder_path = get_latest_vit_folder()
    if latest_vit_folder_path:
        print(f"Bulunan en son VIT klasörü: {latest_vit_folder_path}")
        
        print("\nEn son VIT klasöründeki Excel dosyaları aranıyor...")
        excel_files_in_latest_vit = get_excel_files_from_latest_vit()
        if excel_files_in_latest_vit:
            print("Bulunan Excel dosyaları:")
            for key, path in excel_files_in_latest_vit.items():
                print(f"  {key}: {path}")
        else:
            print("En son VIT klasöründe Excel dosyası bulunamadı.")
    else:
        print("En son VIT klasörü bulunamadı, Excel dosyaları kontrol edilemiyor.")