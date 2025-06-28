# os.path, google.auth.transport.requests, google.oauth2.credentials, google_auth_oauthlib.flow, googleapiclient.errors artık doğrudan kullanılmadığı için kaldırıldı
from googleapiclient.discovery import build
from auth import auth # auth.py modülünden kimlik doğrulama fonksiyonu
# HttpError, Drive API hatalarını yakalamak için hala gerekli.
from googleapiclient.errors import HttpError 


def list_files():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = auth()

    if not creds: # Kimlik doğrulama başarısız olursa
        print("Kimlik doğrulama başarısız oldu. Dosyalar listelenemiyor.")
        return

    try:
        service = build("drive", "v3", credentials=creds)

        # Call the Drive v3 API
        results = (
            service.files()
            .list(pageSize=10, fields="nextPageToken, files(id, name)")
            .execute()
        )
        items = results.get("files", [])

        if not items:
            print("Hiç dosya bulunamadı.")
            return
        print("Dosyalar:")
        for item in items:
            print(f"  {item['name']} (ID: {item['id']})") # Çıktı formatı düzeltildi
    except HttpError as error:
        print(f"Drive API'den bir hata oluştu: {error}")
    except Exception as e:
        print(f"Beklenmeyen bir hata oluştu: {e}")


if __name__ == "__main__":
    list_files()