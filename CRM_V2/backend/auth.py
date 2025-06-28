import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Google API'lerine erişim için gerekli izin kapsamlarını (scopes) tanımlıyoruz.
# Eğer bu izinleri değiştirirseniz, token.json dosyasını silmeniz gerekebilir
# çünkü yeni izinler için kullanıcıdan tekrar onay alınması gerekir.
SCOPES = [
    # Google Drive'dan sadece dosya okuma izni. Excel dosyalarınızı çekiyorsanız gereklidir.
    "https://www.googleapis.com/auth/drive.readonly",
    # Google Takvim'den sadece etkinlikleri okuma izni. Takvim etkinliklerini kullanıyorsanız gereklidir.
    "https://www.googleapis.com/auth/calendar.readonly" 
]

def auth():
    """
    Google API'leri için kullanıcı kimlik doğrulamasını (OAuth 2.0) yapar.
    
    1. Öncelikle 'token.json' dosyasında kayıtlı kimlik doğrulama belirteçlerini arar.
    2. Eğer belirteçler varsa ve geçerliyse bunları kullanır.
    3. Eğer belirteçler süresi dolmuşsa ve yenilenebilirse (refresh token varsa) yeniler.
    4. Eğer belirteçler yoksa veya geçersizse, 'credentials.json' dosyasını kullanarak
       yeni bir kimlik doğrulama akışı başlatır (kullanıcıdan tarayıcı üzerinden izin ister).
    5. Elde edilen belirteçleri 'token.json' dosyasına kaydeder ve döndürür.

    Bu fonksiyon, Google API'leri ile etkileşim kuracak diğer Python betikleri tarafından
    çağrılmalıdır.
    """
    creds = None
    # token.json dosyasının varlığını kontrol et. Bu dosya, önceki oturumlardan
    # alınan kimlik doğrulama bilgilerini içerir.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        
    # Eğer belirteçler yoksa veya geçerli değillerse
    if not creds or not creds.valid:
        # Belirteçler süresi dolmuşsa ve yenileme belirteci varsa, yenilemeye çalış
        if creds and creds.expired and creds.refresh_token:
            print("Google kimlik doğrulama belirteçleri süresi dolmuş, yenileniyor...") # DEBUG
            creds.refresh(Request())
        else:
            # Belirteçler yoksa veya yenilenemiyorsa, yeni bir akış başlat.
            # 'credentials.json' dosyasının yolu güncellendi:
            # auth.py'nin bulunduğu dizinden bir üst dizindeki 'credentials.json' dosyasını arar.
            credentials_path = os.path.join(os.path.dirname(__file__), "..", "credentials.json")
            if not os.path.exists(credentials_path):
                print(f"HATA: credentials.json dosyası bulunamadı: {credentials_path}")
                # Uygulamanızın ne yapması gerektiğine bağlı olarak bir hata fırlatabilir veya çıkabiliriz.
                # Şimdilik hata mesajı verip None dönüyoruz.
                return None 

            print("Yeni Google kimlik doğrulama akışı başlatılıyor...") # DEBUG
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES ) # Güncellenmiş yol kullanıldı
            creds = flow.run_local_server(port=0) # Dinamik bir portta yerel sunucu çalıştırır
        
        # Yeni veya yenilenen belirteçleri token.json dosyasına kaydet
        if creds: # Kimlik doğrulama başarılı ise token kaydet
            with open("token.json", "w") as token:
                token.write(creds.to_json())
                print("Google kimlik doğrulama belirteçleri 'token.json' dosyasına kaydedildi.") # DEBUG
        else:
            print("Kimlik doğrulama başarısız oldu, token kaydedilemedi.") # DEBUG

    return creds

# Bu kısım, 'auth.py' dosyasını doğrudan çalıştırarak kimlik doğrulamasını test etmek içindir.
if __name__ == '__main__':
    print("auth.py doğrudan çalıştırılıyor. Kimlik doğrulama başlatılıyor...")
    try:
        credentials = auth()
        if credentials:
            print("Google kimlik doğrulaması başarıyla tamamlandı.")
            print(f"Elde edilen belirteçler: {credentials.token}")
        else:
            print("Google kimlik doğrulaması başarısız oldu.")
    except Exception as e:
        print(f"Google kimlik doğrulama sırasında bir hata oluştu: {e}")

