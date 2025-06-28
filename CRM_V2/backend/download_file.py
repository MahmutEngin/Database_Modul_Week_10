import io
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from auth import auth # Kimlik doğrulama fonksiyonunu içe aktarıyoruz
import os
import re
import sys # sys modülü hata durumunda çıkış için eklendi

def download_file(real_file_id, custom_output_dir):
    """
    Belirtilen Google Drive dosya kimliğine sahip bir dosyayı özel bir çıktı dizinine indirir.
    
    Args:
        real_file_id (str): İndirilecek dosyanın Google Drive kimliği.
        custom_output_dir (str): Dosyanın kaydedileceği dizin. Boş bırakılamaz.
        
    Returns:
        bytes: İndirilen dosyanın içeriği (bayt olarak) veya bir hata oluşursa None.
    """
    creds = auth() # auth.py dosyasındaki kimlik doğrulama fonksiyonunu çağırıyoruz

    if not creds:
        print("Kimlik doğrulama başarısız oldu. Dosya indirilemiyor.")
        return None

    # custom_output_dir belirtilmemiş veya boşsa hata ver
    if not custom_output_dir or custom_output_dir.strip() == "":
        print("Yapılandırma hatası: custom_output_dir belirtilmelidir.")
        return None
    
    try:
        service = build("drive", "v3", credentials=creds)

        file_id = real_file_id

        # Sadece dosya adını çekiyoruz
        file_metadata = service.files().get(fileId=file_id, fields="name").execute()
        name = file_metadata.get("name")
        
        if not name:
            print(f"Hata: Dosya adı bulunamadı for ID: {file_id}. Bu dosya atlanıyor.")
            return None

        request = service.files().get_media(fileId=file_id)
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(f"İndiriliyor {name}: {int(status.progress() * 100)}%.")
        
        # Dizin varlığını kontrol et ve yoksa oluştur
        if not os.path.exists(custom_output_dir):
            os.makedirs(custom_output_dir)
            print(f"'{custom_output_dir}' dizini oluşturuldu.")

        # Dosyayı kaydet
        output_path = os.path.join(custom_output_dir, name)
        with open(output_path, "wb") as f:
            f.write(file_content.getvalue())
        print(f"'{name}' dosyası '{output_path}' konumuna başarıyla indirildi.")

        return file_content.getvalue()
    
    except HttpError as error:
        print(f"Google Drive API hatası oluştu (ID: {real_file_id}): {error}")
        if error.resp.status == 404:
            print("Hata: Belirtilen dosya ID'si Google Drive'da bulunamadı.")
        elif error.resp.status == 403:
            print("Hata: Dosyaya erişim izniniz yok veya API kota sınırına ulaşıldı.")
        return None
    except Exception as e:
        print(f"Beklenmeyen bir hata oluştu (ID: {real_file_id}): {e}")
        return None

def get_latest_vit_folder(base_path):
    """
    Belirtilen ana dizin (base_path) altında 'VIT' ile başlayan klasörleri bulur
    ve en yüksek sayıya sahip olanı döndürür (örn. VIT1, VIT2, VIT3 -> VIT3).
    Eğer hiç VIT klasörü yoksa None döndürür.
    """
    vit_folders = []
    # base_path'in var olduğundan emin olun
    if not os.path.isdir(base_path):
        print(f"Uyarı: '{base_path}' dizini bulunamadı. Yeni bir 'data/VITx' klasörü oluşturulacak mı kontrol edin.")
        # Eğer data dizini yoksa, onu da burada oluşturabiliriz.
        os.makedirs(base_path, exist_ok=True)
        return None # Henüz VIT klasörü yoksa None dön

    for entry_name in os.listdir(base_path):
        full_path = os.path.join(base_path, entry_name)
        # Sadece "VIT" ile başlayan ve hemen ardından sayı gelen klasörleri eşleştir
        if os.path.isdir(full_path) and re.match(r"VIT\d+$", entry_name, re.IGNORECASE):
            vit_folders.append(entry_name)
    
    if not vit_folders:
        return None
    
    # Sayıları çıkar ve en büyük sayıyı içeren klasörü bul
    def extract_number(folder_name):
        match = re.search(r'\d+', folder_name)
        return int(match.group()) if match else 0

    latest_folder_name = max(vit_folders, key=extract_number)
    return os.path.join(base_path, latest_folder_name)


if __name__ == "__main__":
    # Bu betiğin `CRM_V2/backend/` dizininde olduğunu varsayıyoruz.
    # Bu nedenle, `data` klasörüne erişmek için iki üst dizine çıkmalıyız.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    data_dir_path = os.path.join(project_root, "data")

    # Kullanıcılar.xlsx'i doğrudan 'data' klasörüne indir
    # Önemli: Buradaki ID'leri kendi Google Drive'ınızdaki gerçek dosya ID'leri ile eşleştirin!
    kullanicilar_id = "1Yk6viGXA0kLIjDMQiGFSEynuFVgxRWei" # Lütfen kendi ID'nizle değiştirin
    print(f"Kullanicilar.xlsx indirilmeye başlanıyor: {kullanicilar_id}")
    download_file(real_file_id=kullanicilar_id, custom_output_dir=data_dir_path)

    # Diğer 3 dosya (Basvurular, Mulakatlar, Mentor) için ID'ler
    basvurular_id = "1PrI_bRDL60YWCGZxCevUIUgkrzmSYjmN" # Lütfen kendi ID'nizle değiştirin
    mulakatlar_id = "1bcGn0fjv1qzc_SCyZdaK_SQ8Ywm69Ipy" # Lütfen kendi ID'nizle değiştirin
    mentor_id = "10lfoSlzJJjBHtD8BaMfJHM7DcKdglztS"     # Lütfen kendi ID'nizle değiştirin

    # En son VIT klasörünü bul (örneğin 'data/VIT7')
    latest_vit_folder_path = get_latest_vit_folder(base_path=data_dir_path) 

    if latest_vit_folder_path:
        print(f"En son VIT klasörü bulundu: {latest_vit_folder_path}")
        print(f"Basvurular.xlsx indirilmeye başlanıyor: {basvurular_id}")
        download_file(real_file_id=basvurular_id, custom_output_dir=latest_vit_folder_path)
        print(f"Mulakatlar.xlsx indirilmeye başlanıyor: {mulakatlar_id}")
        download_file(real_file_id=mulakatlar_id, custom_output_dir=latest_vit_folder_path)
        print(f"Mentor.xlsx indirilmeye başlanıyor: {mentor_id}")
        download_file(real_file_id=mentor_id, custom_output_dir=latest_vit_folder_path)
    else:
        # Eğer hiçbir VIT klasörü bulunamazsa, bu dosyaları doğrudan 'data' klasörüne indir.
        # Bu, ilk çalıştırmada 'data' içinde bir VIT klasörü yoksa dosyaların kaybolmamasını sağlar.
        print(f"Uyarı: '{data_dir_path}' klasörü içinde hiçbir VIT klasörü bulunamadı. "
              f"Basvurular, Mulakatlar ve Mentor dosyaları doğrudan '{data_dir_path}' klasörüne indirilmeye çalışılıyor.")
        print(f"Basvurular.xlsx indirilmeye başlanıyor: {basvurular_id}")
        download_file(real_file_id=basvurular_id, custom_output_dir=data_dir_path)
        print(f"Mulakatlar.xlsx indirilmeye başlanıyor: {mulakatlar_id}")
        download_file(real_file_id=mulakatlar_id, custom_output_dir=data_dir_path)
        print(f"Mentor.xlsx indirilmeye başlanıyor: {mentor_id}")
        download_file(real_file_id=mentor_id, custom_output_dir=data_dir_path)

    print("Tüm indirme işlemleri tamamlandı veya hatalarla karşılaşıldı.")
