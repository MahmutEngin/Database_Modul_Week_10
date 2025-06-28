import sys
import os
from PyQt6 import QtWidgets, uic
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QApplication, QVBoxLayout, QWidget, QPushButton, QStackedWidget # QPushButton, QVBoxLayout, QWidget eklendi

# Veritabanı yönetim modülünü import edin (aynı dizinde olduğu varsayılıyor)
from database_manager import DatabaseManager # DatabaseManager sınıfını import ediyoruz

class TercihlerAdminPage(QMainWindow):
    """
    Yönetici tercihleri sayfasını (Admin Paneli) yöneten sınıf.
    Farklı uygulama modüllerine (Başvurular, Mülakatlar, Mentor, Admin) geçiş sağlar.
    """
    
    def __init__(self, db_manager): # db_manager parametresi eklendi
        """
        TercihlerAdminPage sınıfının başlatıcısı.
        :param db_manager: DatabaseManager sınıfının bir örneği.
        """
        super().__init__()
        self.db_manager = db_manager # DatabaseManager objesini sakla (ileride kullanılabilir)
        print("TercihlerAdminPage __init__ başladı.") # DEBUG

        ui_path = os.path.join(os.path.dirname(__file__), "..", "ui", 'tercihlerAdmin_page_python.ui')
        
        if not os.path.exists(ui_path):
            QMessageBox.critical(self, "Hata", f"UI dosyası bulunamadı: {ui_path}\nUygulama kapatılıyor.")
            sys.exit(-1)

        uic.loadUi(ui_path, self)
        print(f"UI dosyası yüklendi: {ui_path}") # DEBUG
        
        # Sayfa referanslarını tutacak değişkenler (MainApp'ten atanacaklar)
        self.stacked_widget = None # MainApp'ten atanacak QStackedWidget referansı
        self.previous_page = None # Önceki sayfanın referansı (MainApp tarafından atanacak)
        self.basvuruform_ta = None
        self.mulakatlarform_ta = None
        self.mentorform_ta = None
        self.adminform_ta = None
        self.tercihlerKullanici_ta = None 
        # self.tercihlerAdmin_ta artık gerekli değil çünkü bu sayfa kendisi.

        # Giriş yapan kullanıcı bilgilerini tutacak değişkenler
        self.logged_in_user_id = None
        self.logged_in_username = None
        self.logged_in_user_yetki = None

        # UI öğelerine erişim (bu isimlerin .ui dosyanızdaki objectName'ler ile eşleştiğinden emin olun)
        # Her findChild çağrısından sonra elemanın None olup olmadığını kontrol etmek iyi bir pratiktir.
        self.pushButton_adminMenu = self.findChild(QtWidgets.QPushButton, "pushButton_adminMenu")
        if self.pushButton_adminMenu is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_adminMenu bulunamadı.")
            sys.exit(-1)

        self.pushButton_basvurular = self.findChild(QtWidgets.QPushButton, "pushButton_basvurular")
        if self.pushButton_basvurular is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_basvurular bulunamadı.")
            sys.exit(-1)

        self.pushButton_anaMenu = self.findChild(QtWidgets.QPushButton, "pushButton_anaMenu")
        if self.pushButton_anaMenu is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_anaMenu bulunamadı.")
            sys.exit(-1)

        self.pushButton_exit = self.findChild(QtWidgets.QPushButton, "pushButton_exit")
        if self.pushButton_exit is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_exit bulunamadı.")
            sys.exit(-1)

        self.pushButton_mentorGorusmesi = self.findChild(QtWidgets.QPushButton, "pushButton_mentorGorusmesi")
        if self.pushButton_mentorGorusmesi is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_mentorGorusmesi bulunamadı.")
            sys.exit(-1)

        self.pushButton_mulakatlar = self.findChild(QtWidgets.QPushButton, "pushButton_mulakatlar") 
        if self.pushButton_mulakatlar is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_mulakatlar bulunamadı.")
            sys.exit(-1)

        print("UI öğeleri başarıyla bulundu.") # DEBUG

        # Sinyal ve Slot Bağlantıları - Butonların tıklama olaylarını ilgili fonksiyonlara bağla
        # Bu fonksiyonlar artık doğrudan sayfa geçişini yapmayacak, sadece MainApp'in ilgili slotlarına bağlanacak.
        # Bu kısım MainApp'teki _connect_navigation_signals metodunda yapılacak.
        # Burada sadece uygulama kapatma sinyali kalabilir.
        self.pushButton_exit.clicked.connect(self.kapatma_fonk)
        
        print("Sinyaller başarıyla bağlandı (çıkış butonu).") # DEBUG
        print("TercihlerAdminPage __init__ tamamlandı.") # DEBUG

    def set_logged_in_user(self, user_id, username, user_yetki):
        """Giriş yapan kullanıcının ID'sini, adını ve yetkisini ayarlar."""
        self.logged_in_user_id = user_id
        self.logged_in_username = username
        self.logged_in_user_yetki = user_yetki
        print(f"TercihlerAdminPage: Giriş yapan kullanıcı ayarlandı - ID: {user_id}, Kullanıcı Adı: {username}, Yetki: {user_yetki}") # DEBUG

    def set_previous_page(self, page):
        """Bu sayfaya geri dönülecek sayfayı ayarlar (MainApp tarafından çağrılır)."""
        print(f"TercihlerAdminPage: 'set_previous_page' atandı: {page.__class__.__name__}") # DEBUG
        self.previous_page = page

    def set_stacked_widget(self, stacked_widget_ref):
        """MainApp'ten gelen QStackedWidget referansını ayarlar."""
        self.stacked_widget = stacked_widget_ref
        print("TercihlerAdminPage: Stacked widget referansı ayarlandı.")

    def sayfayaGeriDon(self):
        """
        Önceki sayfaya döner. Bu metod, MainApp tarafından yönetilen
        stacked_widget'ı kullanarak geçişi sağlar.
        """
        print("TercihlerAdminPage: 'sayfayaGeriDon' çağrıldı.") # DEBUG
        if self.stacked_widget and self.previous_page:
            self.stacked_widget.setCurrentWidget(self.previous_page)
            print("TercihlerAdminPage: Önceki sayfa gösterildi.") # DEBUG
        else:
            QMessageBox.warning(self, "Uyarı", "Geri dönülecek bir sayfa veya stacked widget tanımlanmamış.")
            print("TercihlerAdminPage: Uyarı - Geri dönülecek sayfa veya stacked widget bulunamadı.") # DEBUG


    def set_page_references(self, basvuruform, mulakatlarform, mentorform, adminform, tercihlerKullanici): 
        """
        Uygulamanın diğer sayfa referanslarını bu sayfaya aktarır.
        Bu metot, genellikle main.py tarafından çağrılır ve sayfa geçişleri için referansları ayarlar.
        NOT: Bu metot artık diğer sayfaların 'previous_page'ini ayarlamayacak.
        Bu işlev MainApp'teki geçiş metotlarına taşındı.
        """
        print("TercihlerAdminPage: 'set_page_references' çağrıldı (sadece referansları depolayacak).") # DEBUG
        self.basvuruform_ta = basvuruform
        self.mulakatlarform_ta = mulakatlarform
        self.mentorform_ta = mentorform
        self.adminform_ta = adminform
        self.tercihlerKullanici_ta = tercihlerKullanici
        
        print("TercihlerAdminPage: Sayfa referansları başarıyla depolandı.") # DEBUG

    # Fonksiyonlar (Artık doğrudan geçiş yapmıyorlar, MainApp'e sinyal iletiyor gibi düşünebilirsiniz.)
    # Bu fonksiyonlar MainApp'teki _connect_navigation_signals metoduna bağlanacakları için
    # içleri boş bırakılabilir veya debug mesajları içerebilir.
    def basvurular_fonk(self):
        """Başvurular butonuna basıldığında çağrılır (MainApp yönetecek)."""
        print("TercihlerAdminPage: Basvurular butonu tıklandı.")

    def mentorGorusmesi_fonk(self):
        """Mentor Görüşmeleri butonuna basıldığında çağrılır (MainApp yönetecek)."""
        print("TercihlerAdminPage: Mentor Görüşmeleri butonu tıklandı.")

    def mulakatlar_fonk(self):
        """Mülakatlar butonuna basıldığında çağrılır (MainApp yönetecek)."""
        print("TercihlerAdminPage: Mülakatlar butonu tıklandı.")

    def adminMenu_fonk(self):
        """Admin Menüsü butonuna basıldığında çağrılır (MainApp yönetecek)."""
        print("TercihlerAdminPage: Admin Menü butonu tıklandı.")

    def anamenu_fonk(self): 
        """Ana menü butonuna basıldığında çağrılır (MainApp yönetecek)."""
        print("TercihlerAdminPage: Ana Menü butonu tıklandı.")

    def kapatma_fonk(self):
        """Uygulamayı kapatır."""
        print("TercihlerAdminPage: 'kapatma_fonk' çağrıldı, uygulama kapatılıyor.") # DEBUG
        QApplication.quit() # Tüm PyQt uygulamasını kapatır


# Bu kısım sadece tercihlerAdmin.py dosyasını bağımsız olarak test etmek isterseniz gereklidir.
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    
    try:
        from database_manager import DB_CONFIG 
    except ImportError:
        DB_CONFIG = {
            "host": "127.0.0.1",
            "database": "dbkursiyer",
            "user": "postgres",
            "password": "Mahmut",
            "port": "5432"
        }
        print("UYARI: DB_CONFIG database_manager.py'den import edilemedi, geçici DB_CONFIG kullanılıyor.")

    temp_db_manager = DatabaseManager(DB_CONFIG)
    
    tercihler_admin_page = TercihlerAdminPage(temp_db_manager) 
    tercihler_admin_page.show()

    # Test ortamındaStackedWidget'ı simüle edebiliriz.
    test_stacked_widget = QStackedWidget()
    test_stacked_widget.addWidget(tercihler_admin_page)
    test_stacked_widget.setCurrentWidget(tercihler_admin_page)
    tercihler_admin_page.set_stacked_widget(test_stacked_widget)

    # Test amaçlı diğer sayfaları simüle edip referansları atayalım (isteğe bağlı)
    class DummyPage(QMainWindow):
        def __init__(self, name):
            super().__init__()
            self.setWindowTitle(name)
            self.name = name
            layout = QVBoxLayout()
            layout.addWidget(QtWidgets.QLabel(f"{name} İçeriği"))
            btn_back = QPushButton("Geri Dön (Dummy)")
            layout.addWidget(btn_back)
            container = QWidget()
            container.setLayout(layout)
            self.setCentralWidget(container)
            self.stacked_widget = None
            self.previous_page = None
            btn_back.clicked.connect(self.go_back)

        def set_stacked_widget(self, sw):
            self.stacked_widget = sw
        def set_previous_page(self, prev):
            self.previous_page = prev
        def go_back(self):
            if self.stacked_widget and self.previous_page:
                self.stacked_widget.setCurrentWidget(self.previous_page)

    dummy_basvurular = DummyPage("Basvurular")
    dummy_mulakatlar = DummyPage("Mulakatlar")
    dummy_mentor = DummyPage("Mentor")
    dummy_admin = DummyPage("Admin")
    dummy_tercihler_kullanici = DummyPage("Tercihler Kullanici")

    test_stacked_widget.addWidget(dummy_basvurular)
    test_stacked_widget.addWidget(dummy_mulakatlar)
    test_stacked_widget.addWidget(dummy_mentor)
    test_stacked_widget.addWidget(dummy_admin)
    test_stacked_widget.addWidget(dummy_tercihler_kullanici)

    dummy_basvurular.set_stacked_widget(test_stacked_widget)
    dummy_mulakatlar.set_stacked_widget(test_stacked_widget)
    dummy_mentor.set_stacked_widget(test_stacked_widget)
    dummy_admin.set_stacked_widget(test_stacked_widget)
    dummy_tercihler_kullanici.set_stacked_widget(test_stacked_widget)


    tercihler_admin_page.set_page_references(
        dummy_basvurular, 
        dummy_mulakatlar, 
        dummy_mentor, 
        dummy_admin, 
        dummy_tercihler_kullanici
    )

    # test_stacked_widget'ı göster
    test_stacked_widget.show()
    sys.exit(app.exec())
