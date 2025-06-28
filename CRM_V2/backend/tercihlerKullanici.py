import sys
import os
from PyQt6 import QtWidgets, uic
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QApplication, QVBoxLayout, QWidget, QPushButton, QStackedWidget # QPushButton, QVBoxLayout, QWidget eklendi

# Veritabanı yönetim modülünü import edin (aynı dizinde olduğu varsayılıyor)
# Eğer database_manager.py 'backend' klasöründeyse: from backend.database_manager import DatabaseManager
from database_manager import DatabaseManager # DatabaseManager sınıfını import ediyoruz

class TercihlerKullaniciPage(QMainWindow):
    """
    Kullanıcı tercihleri sayfasını yöneten sınıf.
    Kullanıcıya Başvurular, Mülakatlar ve Mentor Görüşmeleri modüllerine geçiş imkanı sunar.
    """
    
    def __init__(self, db_manager): # db_manager parametresi eklendi
        """
        TercihlerKullaniciPage sınıfının başlatıcısı.
        :param db_manager: DatabaseManager sınıfının bir örneği.
        """
        super().__init__()
        self.db_manager = db_manager # DatabaseManager objesini sakla (ileride kullanılabilir)
        print("TercihlerKullaniciPage __init__ başladı.") # DEBUG

        # .ui dosyasının yolunu dinamik olarak belirliyoruz.
        ui_path = os.path.join(os.path.dirname(__file__), "..", "ui", 'tercihlerKullanici_page_python.ui')
        
        # UI dosyasının varlığını kontrol edin
        if not os.path.exists(ui_path):
            QMessageBox.critical(self, "Hata", f"UI dosyası bulunamadı: {ui_path}\nUygulama kapatılıyor.")
            sys.exit(-1) # UI dosyası yoksa uygulamayı güvenli bir şekilde kapat
            
        uic.loadUi(ui_path, self)
        print(f"UI dosyası yüklendi: {ui_path}") # DEBUG

        # Diğer sayfa referanslarını tutacak değişkenler (MainApp'ten atanacaklar)
        self.stacked_widget = None # MainApp'ten atanacak QStackedWidget referansı
        self.previous_page = None # Önceki sayfanın referansı (MainApp tarafından atanacak)
        self.basvuruform_tk = None
        self.mulakatlarform_tk = None
        self.mentorform_tk = None

        # Giriş yapan kullanıcı bilgilerini tutacak değişkenler
        self.logged_in_user_id = None
        self.logged_in_username = None
        self.logged_in_user_yetki = None

        # UI öğelerine erişim (bu isimlerin .ui dosyanızdaki objectName'ler ile eşleştiğinden emin olun)
        self.pushButton_basvurular = self.findChild(QtWidgets.QPushButton,"pushButton_basvurular")
        if self.pushButton_basvurular is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_basvurular bulunamadı.")
            sys.exit(-1)

        self.pushButton_anaMenu = self.findChild(QtWidgets.QPushButton,"pushButton_anaMenu")
        if self.pushButton_anaMenu is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_anaMenu bulunamadı.")
            sys.exit(-1)

        self.pushButton_exit = self.findChild(QtWidgets.QPushButton,"pushButton_exit")
        if self.pushButton_exit is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_exit bulunamadı.")
            sys.exit(-1)

        self.pushButton_mentorGorusmesi = self.findChild(QtWidgets.QPushButton,"pushButton_mentorGorusmesi")
        if self.pushButton_mentorGorusmesi is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_mentorGorusmesi bulunamadı.")
            sys.exit(-1)

        self.pushButton_mulakatlar = self.findChild(QtWidgets.QPushButton,"pushButton_mulakatlar")
        if self.pushButton_mulakatlar is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_mulakatlar bulunamadı.")
            sys.exit(-1)
        
        print("UI öğeleri başarıyla bulundu.") # DEBUG

        # Olaylar (Signals and Slots) - Butonların tıklama olaylarını ilgili fonksiyonlara bağla
        # Bu fonksiyonlar artık doğrudan sayfa geçişini yapmayacak, sadece MainApp'in ilgili slotlarına bağlanacak.
        # Bu kısım MainApp'teki _connect_navigation_signals metodunda yapılacak.
        # Burada sadece uygulama kapatma sinyali kalabilir.
        self.pushButton_exit.clicked.connect(self.kapatma_fonk)
        print("Sinyaller başarıyla bağlandı (çıkış butonu).") # DEBUG

        print("TercihlerKullaniciPage __init__ tamamlandı.") # DEBUG

    def set_logged_in_user(self, user_id, username, user_yetki):
        """
        Giriş yapan kullanıcının ID'sini, adını ve yetkisini ayarlar.
        """
        self.logged_in_user_id = user_id
        self.logged_in_username = username
        self.logged_in_user_yetki = user_yetki
        print(f"TercihlerKullaniciPage: Oturum açan kullanıcı bilgileri ayarlandı: ID={user_id}, Kullanıcı Adı={username}, Yetki={user_yetki}")

    def set_previous_page(self, page):
        """Bu sayfaya geri dönülecek sayfayı (genellikle LoginPage) ayarlar (MainApp tarafından çağrılır)."""
        self.previous_page = page 
        print(f"TercihlerKullaniciPage: Önceki sayfa referansı ayarlandı: {page.__class__.__name__}") # DEBUG

    def set_stacked_widget(self, stacked_widget_ref):
        """MainApp'ten gelen QStackedWidget referansını ayarlar."""
        self.stacked_widget = stacked_widget_ref
        print("TercihlerKullaniciPage: Stacked widget referansı ayarlandı.")
        # Eğer buton fonksiyonlarınızda self.hide(), self.show() gibi çağrılar varsa
        # veya QApplication.instance().stacked_widget kullanıyorsanız,
        # şimdi self.stacked_widget.setCurrentWidget(hedef_sayfa_objesi) şeklinde güncelleyebilirsiniz.
        # Örneğin, MulakatlarPage içindeki go_back metodunuzda:
        # if hasattr(QApplication.instance(), 'stacked_widget'):
        #    QApplication.instance().stacked_widget.setCurrentWidget(self.previous_page)
        # yerine
        # if self.stacked_widget:
        #    self.stacked_widget.setCurrentWidget(self.previous_page)

    def set_page_references(self, basvuruform, mulakatlarform, mentorform): 
        """
        Uygulamanın diğer sayfa referanslarını bu sayfaya aktarır.
        Bu metot, genellikle main.py tarafından çağrılır ve sayfa geçişleri için referansları ayarlar.
        NOT: Bu metot artık diğer sayfaların 'previous_page'ini ayarlamayacak.
        Bu işlev MainApp'teki geçiş metotlarına taşındı.
        """
        print("TercihlerKullaniciPage: 'set_page_references' çağrıldı (sadece referansları depolayacak).") # DEBUG
        self.basvuruform_tk = basvuruform
        self.mulakatlarform_tk = mulakatlarform
        self.mentorform_tk = mentorform
        print("TercihlerKullaniciPage: Sayfa referansları başarıyla depolandı.") # DEBUG
        
        # Bu kısım artık MainApp tarafından yönetilecek.
        # Örneğin:
        # if self.basvuruform_tk and hasattr(self.basvuruform_tk, 'set_previous_page'):
        #     self.basvuruform_tk.set_previous_page(self)
        
        # if self.mulakatlarform_tk and hasattr(self.mulakatlarform_tk, 'set_previous_page'):
        #     self.mulakatlarform_tk.set_previous_page(self)
        
        # if self.mentorform_tk and hasattr(self.mentorform_tk, 'set_previous_page'):
        #     self.mentorform_tk.set_previous_page(self)

    # Fonksiyonlar (Artık doğrudan geçiş yapmıyorlar, MainApp'e sinyal iletiyor gibi düşünebilirsiniz.)
    # Bu fonksiyonlar MainApp'teki _connect_navigation_signals metoduna bağlanacakları için
    # içleri boş bırakılabilir veya debug mesajları içerebilir.
    def basvuru_fonk(self):
        """Başvurular butonuna basıldığında çağrılır (MainApp yönetecek)."""
        print("TercihlerKullaniciPage: Basvurular butonu tıklandı.")

    def mentorGorusmesi_fonk(self):
        """Mentor Görüşmeleri butonuna basıldığında çağrılır (MainApp yönetecek)."""
        print("TercihlerKullaniciPage: Mentor Görüşmeleri butonu tıklandı.")

    def mulakatlar_fonk(self):
        """Mülakatlar butonuna basıldığında çağrılır (MainApp yönetecek)."""
        print("TercihlerKullaniciPage: Mülakatlar butonu tıklandı.")

    def anamenu_fonk(self):
        """Ana menü butonuna basıldığında çağrılır (MainApp yönetecek)."""
        print("TercihlerKullaniciPage: Ana Menü butonu tıklandı.")
        
    def kapatma_fonk(self):
        """Uygulamayı kapatır."""
        print("TercihlerKullaniciPage: 'kapatma_fonk' çağrıldı, uygulama kapatılıyor.") # DEBUG
        QApplication.quit() # Tüm PyQt uygulamasını kapatır

# Bu kısım sadece tercihlerKullanici.py dosyasını bağımsız olarak test etmek isterseniz gereklidir.
# Normalde bu dosya main.py tarafından içe aktarılır ve kullanılır.
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Test için geçici bir DatabaseManager nesnesi oluşturuluyor.
    # Normalde bu main.py tarafından sağlanır.
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
    
    tercihler_kullanici_page = TercihlerKullaniciPage(temp_db_manager) # db_manager parametresi geçirildi
    
    # Test ortamında QStackedWidget'ı simüle edelim
    test_stacked_widget = QStackedWidget()
    test_stacked_widget.addWidget(tercihler_kullanici_page)
    test_stacked_widget.setCurrentWidget(tercihler_kullanici_page)
    tercihler_kullanici_page.set_stacked_widget(test_stacked_widget)

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

    test_stacked_widget.addWidget(dummy_basvurular)
    test_stacked_widget.addWidget(dummy_mulakatlar)
    test_stacked_widget.addWidget(dummy_mentor)

    dummy_basvurular.set_stacked_widget(test_stacked_widget)
    dummy_mulakatlar.set_stacked_widget(test_stacked_widget)
    dummy_mentor.set_stacked_widget(test_stacked_widget)

    tercihler_kullanici_page.set_page_references(
        dummy_basvurular, 
        dummy_mulakatlar, 
        dummy_mentor
    )

    test_stacked_widget.show()
    sys.exit(app.exec())
