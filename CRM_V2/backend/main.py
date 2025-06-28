import sys
from PyQt6.QtWidgets import QApplication, QStackedWidget, QMessageBox, QMainWindow

# Sayfa sınıflarını içe aktar
from database_manager import DatabaseManager, DB_CONFIG 
from login import LoginPage
from mentor import MentorPage
from mulakatlar import MulakatlarPage
from basvurular import BasvurularPage

# Eğer AdminPage ve TercihlerKullaniciPage dosyalarınız mevcutsa, bu importları aktif tutun.
# Yoksa, "ModuleNotFoundError" alabilirsiniz.
try:
    from admin import AdminPage 
except ImportError:
    AdminPage = None # Sınıf bulunamazsa None olarak ayarla
    print("UYARI: AdminPage modülü bulunamadı.")

try:
    from tercihlerKullanici import TercihlerKullaniciPage
except ImportError:
    TercihlerKullaniciPage = None # Sınıf bulunamazsa None olarak ayarla
    print("UYARI: TercihlerKullaniciPage modülü bulunamadı.")

from tercihlerAdmin import TercihlerAdminPage

class MainApp(QMainWindow):
    """
    CRM Uygulamasının ana penceresi ve sayfa yöneticisi.
    Tüm uygulama sayfalarını içerir ve sayfalar arası geçişi sağlar.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CRM Uygulaması")
        self.resize(500, 300) # Uygulamanın başlangıç boyutunu ayarla

        self.db_manager = None
        # Veritabanı bağlantısını kur ve tabloları oluştur
        if not self._initialize_database():
            QMessageBox.critical(self, "Veritabanı Hatası", "Veritabanı bağlantısı kurulamadı veya tablolar oluşturulamadı. Uygulama kapatılıyor.")
            sys.exit(1) # Uygulamadan çıkış

        # QStackedWidget'ı ana pencerenin merkezi widget'ı olarak ayarla
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Tüm sayfa nesnelerini burada oluşturun
        # Her sayfa nesnesine DatabaseManager'ı geçireceğiz.
        # Sayfalar, geçiş yapacakları stacked_widget'a erişebilmeli.
        self.login_page = LoginPage(self.db_manager)
        self.basvurular_page = BasvurularPage(self.db_manager)
        self.mulakatlar_page = MulakatlarPage(self.db_manager)
        self.mentor_page = MentorPage(self.db_manager)
        self.tercihler_admin_page = TercihlerAdminPage(self.db_manager)
        
        # AdminPage ve TercihlerKullaniciPage'in varlığını kontrol et
        self.admin_page = AdminPage(self.db_manager) if AdminPage else None
        self.tercihler_kullanici_page = TercihlerKullaniciPage(self.db_manager) if TercihlerKullaniciPage else None

        # Stacked Widget'a tüm sayfaları ekle
        self.stacked_widget.addWidget(self.login_page)
        self.stacked_widget.addWidget(self.basvurular_page)
        self.stacked_widget.addWidget(self.mulakatlar_page)
        self.stacked_widget.addWidget(self.mentor_page)
        if self.admin_page: self.stacked_widget.addWidget(self.admin_page) 
        if self.tercihler_kullanici_page: self.stacked_widget.addWidget(self.tercihler_kullanici_page) 
        self.stacked_widget.addWidget(self.tercihler_admin_page)

        # LoginPage'den başarılı giriş sinyalini yakala
        # LoginPage sinyalinin (yetki, user_id, username) şeklinde veri gönderdiği varsayılıyor.
        self.login_page.login_successful.connect(self.handle_login_success)

        # TÜM SAYFALARA REFERANSLARINI VE ANA STACKED_WIDGET'I ATA
        # Bu metod tüm sayfalar oluşturulduktan sonra çağrılmalı.
        self._set_all_page_references()
        self._connect_navigation_signals() # Sayfa geçiş sinyallerini bağla

        # Uygulama başladığında ilk olarak giriş sayfasını göster
        self.stacked_widget.setCurrentWidget(self.login_page)
        # self.showMaximized() # Bu satır yoruma alındı. Pencere artık başlangıç boyutunda açılacak.


    def _initialize_database(self):
        """
        Veritabanı bağlantısını kurar ve uygulamanın ihtiyaç duyduğu tabloları oluşturur.
        Bağlantı hatası durumunda False döner.
        """
        try:
            self.db_manager = DatabaseManager(DB_CONFIG)
            with self.db_manager as db:
                db.create_tables()
            print("Veritabanı bağlantısı ve tablolar başarıyla başlatıldı.")
            return True
        except Exception as e:
            print(f"Veritabanı başlatılırken kritik hata oluştu: {e}")
            return False

    def _set_all_page_references(self):
        """
        Tüm sayfa nesnelerine birbirlerinin referanslarını ve ana stacked_widget'ı atar.
        Bu metod, tüm sayfa nesneleri oluşturulduktan sonra çağrılır.
        """
        print("MainApp: Tüm sayfa referansları atanıyor.")

        # Her bir sayfaya stacked_widget referansını ata
        # Bu, her sayfanın 'set_stacked_widget' metoduna sahip olduğunu varsayar.
        pages_to_set_stacked_widget = [
            self.login_page, self.basvurular_page, self.mulakatlar_page, 
            self.mentor_page, self.tercihler_admin_page
        ]
        if self.admin_page: pages_to_set_stacked_widget.append(self.admin_page)
        if self.tercihler_kullanici_page: pages_to_set_stacked_widget.append(self.tercihler_kullanici_page)

        for page in pages_to_set_stacked_widget:
            if page and hasattr(page, 'set_stacked_widget'):
                page.set_stacked_widget(self.stacked_widget)
            elif page:
                print(f"UYARI: {page.__class__.__name__} sınıfında 'set_stacked_widget' metodu bulunamadı.")
        
        # TercihlerAdminPage'e diğer sayfa referanslarını ayarla
        # Bu çağrı artık TercihlerAdminPage'in kendi set_page_references metodunu çağırıyor.
        self.tercihler_admin_page.set_page_references(
            self.basvurular_page,
            self.mulakatlar_page,
            self.mentor_page,
            self.admin_page, # AdminPage nesnesini geçir (None olabilir)
            self.tercihler_kullanici_page # TercihlerKullaniciPage nesnesini geçir (None olabilir)
            # Kendi referansı (tercihlerAdmin_ta) artık tercihlerAdmin içinde tutulmuyor, doğrudan self oluyor
        )

        # TercihlerKullaniciPage'e diğer sayfa referanslarını ata (varsa)
        if self.tercihler_kullanici_page:
            if hasattr(self.tercihler_kullanici_page, 'set_page_references'):
                self.tercihler_kullanici_page.set_page_references(
                    self.basvurular_page,
                    self.mulakatlar_page,
                    self.mentor_page
                )
            else:
                print(f"UYARI: TercihlerKullaniciPage sınıfında 'set_page_references' metodu bulunamadı.")
        
        # BasvurularPage'e tercih sayfaları referanslarını ata (varsa)
        if hasattr(self.basvurular_page, 'set_tercihler_page_references'):
            self.basvurular_page.set_tercihler_page_references(
                self.tercihler_admin_page,
                self.tercihler_kullanici_page
            )
        
        print("MainApp: Tüm sayfa referansları ataması tamamlandı.")

    def _connect_navigation_signals(self):
        """
        Sayfalar arasındaki geçiş sinyallerini MainApp'teki ilgili slotlara bağlar.
        Bu, sayfa geçişlerinin merkezi olarak MainApp tarafından yönetilmesini sağlar.
        """
        print("MainApp: Sayfa geçiş sinyalleri bağlanıyor.")

        # TercihlerAdminPage'deki butonları MainApp'teki geçiş metotlarına bağla
        # Her butonun tıklandığında, ilgili hedef sayfaya geçişi MainApp yönetecek.
        self.tercihler_admin_page.pushButton_basvurular.clicked.connect(self._go_to_basvurular_from_tercihler_admin)
        self.tercihler_admin_page.pushButton_mentorGorusmesi.clicked.connect(self._go_to_mentor_from_tercihler_admin)
        self.tercihler_admin_page.pushButton_mulakatlar.clicked.connect(self._go_to_mulakatlar_from_tercihler_admin)
        self.tercihler_admin_page.pushButton_adminMenu.clicked.connect(self._go_to_admin_from_tercihler_admin)
        self.tercihler_admin_page.pushButton_anaMenu.clicked.connect(self._go_to_login_from_tercihler_admin) # Login'e dönüş

        # TercihlerKullaniciPage'deki butonları MainApp'teki geçiş metotlarına bağla
        if self.tercihler_kullanici_page: # TercihlerKullaniciPage yüklendiğinden emin ol
            self.tercihler_kullanici_page.pushButton_basvurular.clicked.connect(self._go_to_basvurular_from_tercihler_kullanici)
            self.tercihler_kullanici_page.pushButton_mentorGorusmesi.clicked.connect(self._go_to_mentor_from_tercihler_kullanici)
            self.tercihler_kullanici_page.pushButton_mulakatlar.clicked.connect(self._go_to_mulakatlar_from_tercihler_kullanici)
            self.tercihler_kullanici_page.pushButton_anaMenu.clicked.connect(self._go_to_login_from_tercihler_kullanici)
            self.tercihler_kullanici_page.pushButton_exit.clicked.connect(self.kapatma_fonk) # Exit butonu da buraya bağlandı

        print("MainApp: Sayfa geçiş sinyalleri bağlandı.")

    # handle_login_success metodunun parametre sırası, LoginPage'den gelen sinyale göre ayarlandı.
    # LoginPage sinyalinin (yetki, user_id, username) şeklinde veri gönderdiği varsayılıyor.
    def handle_login_success(self, user_yetki, user_id, username): # Parametre sırası düzeltildi
        """
        Kullanıcı girişi başarılı olduğunda çağrılır.
        Kullanıcı yetkisine göre ilgili sayfaya yönlendirme yapar
        ve gerekli kullanıcı bilgilerini sayfalara aktarır.
        """
        # HATA AYIKLAMA: Gelen user_yetki değerini konsola yazdır
        print(f"DEBUG: handle_login_success'e gelen user_yetki: '{user_yetki}'") 
        print(f"DEBUG: handle_login_success'e gelen user_id: '{user_id}'")
        print(f"DEBUG: handle_login_success'e gelen username: '{username}'")

        print(f"Giriş başarılı - Yetki: {user_yetki}, ID: {user_id}, Kullanıcı Adı: {username}")

        # Her sayfaya giriş yapan kullanıcının bilgilerini ayarla
        pages_to_set_user = [
            self.basvurular_page, self.mulakatlar_page, self.mentor_page, 
            self.tercihler_admin_page
        ]
        if self.admin_page: pages_to_set_user.append(self.admin_page)
        if self.tercihler_kullanici_page: pages_to_set_user.append(self.tercihler_kullanici_page)

        for page in pages_to_set_user:
            if page and hasattr(page, 'set_logged_in_user'):
                page.set_logged_in_user(user_id, username, user_yetki)
            elif page:
                print(f"UYARI: {page.__class__.__name__} sınıfında 'set_logged_in_user' metodu bulunamadı.")

        # Kullanıcı yetkisine göre doğru sayfaya yönlendir
        if user_yetki == 'admin':
            self.tercihler_admin_page.set_previous_page(self.login_page) # Login sayfasını önceki sayfa olarak ayarla
            self.stacked_widget.setCurrentWidget(self.tercihler_admin_page)
        elif user_yetki == 'user':
            if self.tercihler_kullanici_page:
                self.tercihler_kullanici_page.set_previous_page(self.login_page) # Login sayfasını önceki sayfa olarak ayarla
                self.stacked_widget.setCurrentWidget(self.tercihler_kullanici_page)
            else:
                QMessageBox.warning(self, "Uyarı", "Kullanıcı tercihleri sayfası bulunamadı veya yüklanamadı.")
                self.stacked_widget.setCurrentWidget(self.login_page)
        elif user_yetki == 'mentor':
            if self.mentor_page:
                self.mentor_page.set_previous_page(self.login_page) # Login sayfasını önceki sayfa olarak ayarla
                self.stacked_widget.setCurrentWidget(self.mentor_page)
                self.mentor_page.display_mentor_gorusmeleri() # Mentor sayfası açıldığında verileri yenile
            else:
                QMessageBox.warning(self, "Uyarı", "Mentor sayfası bulunamadı veya yüklanamadı.")
                self.stacked_widget.setCurrentWidget(self.login_page)
        else:
            QMessageBox.warning(self, "Yetki Hatası", "Bilinmeyen kullanıcı yetkisi. Giriş sayfasına yönlendiriliyor.")
            self.stacked_widget.setCurrentWidget(self.login_page)

    # --- TercihlerAdminPage'den Gelen Geçiş Metotları ---
    # Bu metotlar, TercihlerAdminPage'deki butonlara bağlanacak
    # ve sayfa geçişini yönetecek.

    def _go_to_basvurular_from_tercihler_admin(self):
        """TercihlerAdminPage'den Basvurular sayfasına geçiş yapar."""
        print("MainApp: TercihlerAdminPage'den Basvurular sayfasına geçiliyor.")
        self.basvurular_page.set_previous_page(self.tercihler_admin_page) # Önceki sayfayı ayarla
        self.stacked_widget.setCurrentWidget(self.basvurular_page)
        # self.basvurular_page.display_data() # Gerekirse Başvurular sayfasının verilerini yenile

    def _go_to_mentor_from_tercihler_admin(self):
        """TercihlerAdminPage'den Mentor Görüşmeleri sayfasına geçiş yapar."""
        print("MainApp: TercihlerAdminPage'den Mentor sayfasına geçiliyor.")
        self.mentor_page.set_previous_page(self.tercihler_admin_page) # Önceki sayfayı ayarla
        self.stacked_widget.setCurrentWidget(self.mentor_page)
        self.mentor_page.display_mentor_gorusmeleri() # Mentor sayfasının verilerini yenile

    def _go_to_mulakatlar_from_tercihler_admin(self):
        """TercihlerAdminPage'den Mulakatlar sayfasına geçiş yapar."""
        print("MainApp: TercihlerAdminPage'den Mulakatlar sayfasına geçiliyor.")
        self.mulakatlar_page.set_previous_page(self.tercihler_admin_page) # Önceki sayfayı ayarla
        self.stacked_widget.setCurrentWidget(self.mulakatlar_page)
        # self.mulakatlar_page.display_data() # Gerekirse Mülakatlar sayfasının verilerini yenile

    def _go_to_admin_from_tercihler_admin(self):
        """TercihlerAdminPage'den Admin Menüsü sayfasına geçiş yapar."""
        if self.admin_page:
            print("MainApp: TercihlerAdminPage'den Admin Menü sayfasına geçiliyor.")
            self.admin_page.set_previous_page(self.tercihler_admin_page) # Önceki sayfayı ayarla
            self.stacked_widget.setCurrentWidget(self.admin_page)
            # self.admin_page.display_data() # Gerekirse Admin Menü sayfasının verilerini yenile
        else:
            QMessageBox.warning(self, "Uyarı", "Admin Menü sayfası yüklenemedi.")

    def _go_to_login_from_tercihler_admin(self):
        """TercihlerAdminPage'den Login sayfasına geçiş yapar."""
        print("MainApp: TercihlerAdminPage'den Login sayfasına geçiliyor.")
        self.login_page.set_previous_page(self.tercihler_admin_page) # Önceki sayfayı ayarla (opsiyonel)
        self.stacked_widget.setCurrentWidget(self.login_page)

    # --- TercihlerKullaniciPage'den Gelen Geçiş Metotları ---
    def _go_to_basvurular_from_tercihler_kullanici(self):
        """TercihlerKullaniciPage'den Basvurular sayfasına geçiş yapar."""
        print("MainApp: TercihlerKullaniciPage'den Basvurular sayfasına geçiliyor.")
        self.basvurular_page.set_previous_page(self.tercihler_kullanici_page)
        self.stacked_widget.setCurrentWidget(self.basvurular_page)
        # self.basvurular_page.display_data() # Gerekirse verileri yenile

    def _go_to_mentor_from_tercihler_kullanici(self):
        """TercihlerKullaniciPage'den Mentor Görüşmeleri sayfasına geçiş yapar."""
        print("MainApp: TercihlerKullaniciPage'den Mentor sayfasına geçiliyor.")
        self.mentor_page.set_previous_page(self.tercihler_kullanici_page)
        self.stacked_widget.setCurrentWidget(self.mentor_page)
        self.mentor_page.display_mentor_gorusmeleri() # Mentor sayfasının verilerini yenile

    def _go_to_mulakatlar_from_tercihler_kullanici(self):
        """TercihlerKullaniciPage'den Mulakatlar sayfasına geçiş yapar."""
        print("MainApp: TercihlerKullaniciPage'den Mulakatlar sayfasına geçiliyor.")
        self.mulakatlar_page.set_previous_page(self.tercihler_kullanici_page)
        self.stacked_widget.setCurrentWidget(self.mulakatlar_page)
        # self.mulakatlar_page.display_data() # Gerekirse verileri yenile

    def _go_to_login_from_tercihler_kullanici(self):
        """TercihlerKullaniciPage'den Login sayfasına geçiş yapar."""
        print("MainApp: TercihlerKullaniciPage'den Login sayfasına geçiliyor.")
        self.login_page.set_previous_page(self.tercihler_kullanici_page) # Opsiyonel
        self.stacked_widget.setCurrentWidget(self.login_page)

    def kapatma_fonk(self):
        """Uygulamayı kapatır."""
        print("MainApp: 'kapatma_fonk' çağrıldı, uygulama kapatılıyor.") # DEBUG
        QApplication.quit() # Tüm PyQt uygulamasını kapatır


# Uygulama başlangıç noktası
if __name__ == "__main__":
    # database_manager'dan DB_CONFIG'in doğru şekilde import edildiğinden emin olun.
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

    app = QApplication(sys.argv)
    main_window = MainApp() # MainApp'i ana pencere olarak oluştur
    main_window.show() # Pencereyi normal boyutunda göster
    sys.exit(app.exec())
