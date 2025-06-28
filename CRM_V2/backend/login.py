import sys
import os
from PyQt6 import uic, QtWidgets
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QApplication
from PyQt6.QtCore import pyqtSignal

# Veritabanı yönetim modülünü import edin (aynı dizinde olduğu varsayılıyor)
# Eğer database_manager.py 'backend' klasöründeyse: from backend.database_manager import DatabaseManager
from database_manager import DatabaseManager # DatabaseManager sınıfını import ediyoruz
from psycopg2 import sql, Error # SQL ve hata yönetimi için gerekli

class LoginPage(QMainWindow):
    # Başarılı giriş sinyali. Kullanıcı yetkisini, kullanıcı ID'sini ve kullanıcı adını taşır.
    login_successful = pyqtSignal(str, int, str)

    def __init__(self, db_manager):
        """
        LoginPage sınıfının yapıcı metodu.
        :param db_manager: DatabaseManager sınıfının bir örneği.
        """
        super().__init__()
        self.db_manager = db_manager # DatabaseManager objesini sakla
        print("LoginPage __init__ başladı.")

        # .ui dosyasının yolunu dinamik olarak belirle
        # main.py'den LoginPage çağrıldığında, bu path main.py'nin çalıştığı yere göre belirlenir.
        # Bu dosya (login.py) backend içinde olduğu için, ui klasörü bir üst dizindeki ui klasörüdür.
        ui_path = os.path.join(os.path.dirname(__file__), "..", "ui", 'login_page_python.ui')
        
        if not os.path.exists(ui_path):
            QMessageBox.critical(self, "Hata", f"UI dosyası bulunamadı: {ui_path}\nUygulama kapatılıyor.")
            sys.exit(-1) # UI dosyası yoksa uygulamayı güvenli bir şekilde kapat

        uic.loadUi(ui_path, self)
        print(f"UI dosyası yüklendi: {ui_path}")

        # --- Güncellenmiş Kod: Pencere Boyutunu Ayarla ve Yeniden Boyutlandırmaya İzin Ver ---
        self.resize(400, 350) # Pencereyi 400x350 piksel boyutunda başlat ancak yeniden boyutlandırmaya izin ver
        self.setWindowTitle("Kullanıcı Girişi") # Pencere başlığını belirle
        # -----------------------------------------------------------------------------------

        # UI öğelerine erişim (Verdiğiniz yeni isimlere göre güncellendi)
        self.lineEdit_kullaniciAdi = self.findChild(QtWidgets.QLineEdit, "lineEdit_username")
        if self.lineEdit_kullaniciAdi is None:
            QMessageBox.critical(self, "UI Hatası", "lineEdit_username bulunamadı. Lütfen Qt Designer'da objectName'ini kontrol edin.")
            sys.exit(-1)

        self.lineEdit_sifre = self.findChild(QtWidgets.QLineEdit, "lineEdit_password")
        if self.lineEdit_sifre is None:
            QMessageBox.critical(self, "UI Hatası", "lineEdit_password bulunamadı. Lütfen Qt Designer'da objectName'ini kontrol edin.")
            sys.exit(-1)
        
        # --- Yeni Eklenen Kod: Parola Alanını Gizle ---
        self.lineEdit_sifre.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password) # Parolayı gizle
        # ---------------------------------------------

        self.pushButton_giris = self.findChild(QtWidgets.QPushButton, "pushButton_login")
        if self.pushButton_giris is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_login bulunamadı. Lütfen Qt Designer'da objectName'ini kontrol edin.")
            sys.exit(-1)
        
        self.pushButton_exit = self.findChild(QtWidgets.QPushButton, "pushButton_exit")
        if self.pushButton_exit is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_exit bulunamadı. Lütfen Qt Designer'da objectName'ini kontrol edin.")
            sys.exit(-1)

        print("UI öğeleri başarıyla bulundu.")

        # Sinyal ve Slot Bağlantıları
        self.pushButton_giris.clicked.connect(self.giris_yap)
        self.pushButton_exit.clicked.connect(self.cikis_yap)
        print("Sinyaller başarıyla bağlandı.")

        # Diğer sayfa referansları (main.py tarafından ayarlanacak)
        self.admin_page = None
        self.tercihler_kullanici_page = None # 'user_page' yerine 'tercihler_kullanici_page' kullanıldı
        self.basvurular_page = None
        self.mulakatlar_page = None
        self.mentor_page = None
        self.previous_page = None # Geri dönüş için önceki sayfa referansı
        
        # Giriş yapan kullanıcı bilgileri
        self.logged_in_user_id = None
        self.logged_in_username = None
        self.logged_in_user_yetki = None

        print("LoginPage __init__ tamamlandı.")

    def set_page_references(self, admin_page, tercihler_kullanici_page, basvurular_page, mulakatlar_page, mentor_page):
        """
        Diğer sayfa objelerinin referanslarını ayarlar.
        :param admin_page: AdminPage objesi
        :param tercihler_kullanici_page: TercihlerKullaniciPage objesi
        :param basvurular_page: BasvurularPage objesi
        :param mulakatlar_page: MulakatlarPage objesi
        :param mentor_page: MentorPage objesi
        """
        self.admin_page = admin_page
        self.tercihler_kullanici_page = tercihler_kullanici_page
        self.basvurular_page = basvurular_page
        self.mulakatlar_page = mulakatlar_page
        self.mentor_page = mentor_page
        print("LoginPage: Sayfa referansları ayarlandı.")

    def set_logged_in_user(self, user_id, username, user_yetki):
        """
        Giriş yapan kullanıcının bilgilerini saklar.
        Bu metod, main.py'den çağrıldığında, sayfaStackedWidget'a eklendikten sonra kullanılır.
        Ancak, LoginPage için bu bilgiler zaten login_successful sinyali ile iletildiği için
        bu metodun çağrılması login_page özelinde çok gerekli olmayabilir.
        Diğer sayfalarda kullanışlı olacaktır.
        """
        self.logged_in_user_id = user_id
        self.logged_in_username = username
        self.logged_in_user_yetki = user_yetki
        print(f"LoginPage: Oturum açan kullanıcı bilgileri ayarlandı: ID={user_id}, Kullanıcı Adı={username}, Yetki={user_yetki}")

    def set_previous_page(self, page):
        """
        Geri dönülecek önceki sayfanın referansını saklar.
        """
        self.previous_page = page
        print(f"LoginPage: Önceki sayfa referansı ayarlandı: {type(page).__name__}")


    def giris_yap(self):
        """Giriş yap butonuna basıldığında tetiklenir."""
        kullanici_adi = self.lineEdit_kullaniciAdi.text().strip()
        parola = self.lineEdit_sifre.text().strip()

        if not kullanici_adi or not parola:
            QMessageBox.warning(self, "Giriş Hatası", "Kullanıcı adı ve parola boş bırakılamaz.")
            print("LoginPage: Kullanıcı adı veya parola boş.")
            return

        print(f"LoginPage: Giriş denemesi - Kullanıcı Adı: {kullanici_adi}")

        # Veritabanı bağlantısını 'with' bloğu içinde yönet, mevcut db_manager'ı kullan
        try:
            with self.db_manager as db: # db_manager nesnesini kullanıyoruz
                # SQL sorgusu: 'kullanicilar' tablosundaki 'yetki' ve 'parola' sütunlarını kontrol et
                query = sql.SQL("SELECT kullaniciid, yetki FROM kullanicilar WHERE kullaniciadi = %s AND parola = %s;")
                result = db.fetch_all(query, (kullanici_adi, parola))

                if result:
                    user_data = result[0]
                    user_yetki = user_data['yetki']
                    user_id = user_data['kullaniciid']
                    QMessageBox.information(self, "Giriş Başarılı", f"Hoş geldiniz, {kullanici_adi}!")
                    print(f"LoginPage: Giriş başarılı - Yetki: {user_yetki}, ID: {user_id}")
                    
                    # Başarılı giriş sinyalini yay
                    self.login_successful.emit(user_yetki, user_id, kullanici_adi)

                else:
                    QMessageBox.warning(self, "Giriş Hatası", "Geçersiz kullanıcı adı veya parola.")
                    print("LoginPage: Geçersiz kullanıcı adı/parola.")

        except Error as e:
            # psycopg2'den gelen veritabanı hataları
            QMessageBox.critical(self, "Veritabanı Hatası", 
                                 f"Giriş sırasında bir veritabanı sorgu hatası oluştu: {e}\n"
                                 "Lütfen veritabanı (kullanicilar tablosu) şemasının (sütun isimlerinin) uygulama koduyla eşleştiğinden emin olun (özellikle 'yetki' ve 'parola' sütunları).")
            print(f"LoginPage: HATA - Veritabanı sorgu hatası: {e}")
        except Exception as e:
            # Diğer genel Python hataları
            QMessageBox.critical(self, "Hata", f"Beklenmeyen bir hata oluştu: {e}")
            print(f"LoginPage: HATA - Beklenmeyen hata: {e}")

    def cikis_yap(self):
        """Uygulamadan güvenli bir şekilde çıkar."""
        print("LoginPage: 'cikis_yap' çağrıldı, uygulama kapatılıyor.")
        QApplication.quit() # PyQt uygulamasını kapatır

# Her bir sayfa sınıfının içine (örneğin LoginPage, BasvurularPage vb.)
    def set_stacked_widget(self, stacked_widget_ref):
        self.stacked_widget = stacked_widget_ref
        # Eğer buton fonksiyonlarınızda self.hide(), self.show() gibi çağrılar varsa
        # veya QApplication.instance().stacked_widget kullanıyorsanız,
        # şimdi self.stacked_widget.setCurrentWidget(hedef_sayfa_objesi) şeklinde güncelleyebilirsiniz.
        # Örneğin, MulakatlarPage içindeki go_back metodunuzda:
        # if hasattr(QApplication.instance(), 'stacked_widget'):
        #   QApplication.instance().stacked_widget.setCurrentWidget(self.previous_page)
        # yerine
        # if self.stacked_widget:
        #   self.stacked_widget.setCurrentWidget(self.previous_page)

# Bu blok, sadece login.py dosyası doğrudan çalıştırıldığında aktif olur.
# Normalde uygulama main.py üzerinden başlatılacaktır.
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    # Burada db_manager objesini oluşturmamız gerekiyor, çünkü main.py'den bağımsız çalışıyoruz.
    # Normalde bu main.py tarafından sağlanır.
    DB_CONFIG = { # database_manager.py'den import edilmiş veya buraya manuel eklenmiş olmalı
        "host": "127.0.0.1",
        "database": "dbkursiyer",
        "user": "postgres",
        "password": "Mahmut",
        "port": "5432"
    }
    temp_db_manager = DatabaseManager(DB_CONFIG)
    login_page = LoginPage(temp_db_manager) # db_manager parametresini geçirdik
    login_page.show()
    sys.exit(app.exec())
