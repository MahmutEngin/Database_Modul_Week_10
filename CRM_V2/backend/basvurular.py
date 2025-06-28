import sys
import os
from PyQt6 import uic, QtWidgets
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QApplication, QTableWidgetItem
from PyQt6.QtCore import pyqtSignal # Sinyal kullanımı için eklendi
from psycopg2 import sql, Error
import pandas as pd # openpyxl'i dolaylı olarak kullanır

# Veritabanı yönetim modülünü import edin (aynı dizinde olduğu varsayılıyor)
from database_manager import DatabaseManager, DB_CONFIG # DB_CONFIG de burada kullanıldığı için import edildi

class BasvurularPage(QMainWindow):
    """
    Başvurular sayfasını yöneten sınıf.
    Kursiyer başvurularını ve ilgili mentor/proje takibi bilgilerini görüntüler.
    """
    def __init__(self, db_manager): # db_manager parametresi eklendi
        """BasvurularPage sınıfının başlatıcısı."""
        super().__init__()
        self.db_manager = db_manager # DatabaseManager objesini sakla
        print("BasvurularPage __init__ başladı.") # DEBUG

        # UI dosyasının yolunu dinamik olarak belirliyoruz.
        ui_path = os.path.join(os.path.dirname(__file__), "..", "ui", 'basvurular_page_python.ui')
        if not os.path.exists(ui_path):
            QMessageBox.critical(self, "Hata", f"UI dosyası bulunamadı: {ui_path}")
            sys.exit(-1)

        uic.loadUi(ui_path, self)
        print(f"UI dosyası yüklendi: {ui_path}") # DEBUG

        self.previous_page = None # Önceki sayfa referansını tutar (geri dönmek için)
        self.logged_in_user_id = None # Giriş yapan kullanıcının ID'sini tutar
        self.logged_in_username = None # Giriş yapan kullanıcının adını tutar
        self.logged_in_user_yetki = None # Giriş yapan kullanıcının yetkisini tutar
        self.stacked_widget = None # MainApp'teki QStackedWidget referansını tutar

        # Tercihler sayfalarına referanslar
        self.admin_tercihler_page = None
        self.kullanici_tercihler_page = None
            
        # UI öğelerini bulma (bu isimlerin .ui dosyanızdaki objectName'ler ile eşleştiğinden emin olun)
        # Her bir findChild çağrısından sonra elemanın None olup olmadığını kontrol edin
        self.pushButton_tumBasvurular = self.findChild(QtWidgets.QPushButton,"pushButton_tumBasvurular")
        if self.pushButton_tumBasvurular is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_tumBasvurular bulunamadı.")
            sys.exit(-1)

        self.pushButton_tanimlananMentorGorusmesi = self.findChild(QtWidgets.QPushButton,"pushButton_tanimlananMentorGorusmesi")
        if self.pushButton_tanimlananMentorGorusmesi is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_tanimlananMentorGorusmesi bulunamadı.")
            sys.exit(-1)

        self.pushButton_tanimlanmayanMentorGorusmesi = self.findChild(QtWidgets.QPushButton,"pushButton_tanimlanmayanMentorGorusmesi")
        if self.pushButton_tanimlanmayanMentorGorusmesi is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_tanimlanmayanMentorGorusmesi bulunamadı.")
            sys.exit(-1)

        self.pushButton_oncekiVitKontrol = self.findChild(QtWidgets.QPushButton,"pushButton_oncekiVitKontrol")
        if self.pushButton_oncekiVitKontrol is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_oncekiVitKontrol bulunamadı.")
            sys.exit(-1)

        self.pushButton_basvuruFiltrele = self.findChild(QtWidgets.QPushButton,"pushButton_basvuruFiltrele")
        if self.pushButton_basvuruFiltrele is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_basvuruFiltrele bulunamadı.")
            sys.exit(-1)

        self.pushButton_mukerrerKayit = self.findChild(QtWidgets.QPushButton,"pushButton_mukerrerKayit")
        if self.pushButton_mukerrerKayit is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_mukerrerKayit bulunamadı.")
            sys.exit(-1)

        self.pushButton_farkliKayit = self.findChild(QtWidgets.QPushButton,"pushButton_farkliKayit")
        if self.pushButton_farkliKayit is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_farkliKayit bulunamadı.")
            sys.exit(-1)

        self.pushButton_tercihler = self.findChild(QtWidgets.QPushButton,"pushButton_tercihler")
        if self.pushButton_tercihler is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_tercihler bulunamadı.")
            sys.exit(-1)

        self.pushButton_exit = self.findChild(QtWidgets.QPushButton,"pushButton_exit")
        if self.pushButton_exit is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_exit bulunamadı.")
            sys.exit(-1)

        self.pushButton_ara = self.findChild(QtWidgets.QPushButton,"pushButton_ara")
        if self.pushButton_ara is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_ara bulunamadı.")
            sys.exit(-1)

        self.lineEdit_ara = self.findChild(QtWidgets.QLineEdit,"lineEdit_ara")
        if self.lineEdit_ara is None:
            QMessageBox.critical(self, "UI Hatası", "lineEdit_ara bulunamadı.")
            sys.exit(-1)

        self.tableWidget_goster = self.findChild(QtWidgets.QTableWidget,"tableWidget_goster")
        if self.tableWidget_goster is None:
            QMessageBox.critical(self, "UI Hatası", "tableWidget_goster bulunamadı.")
            sys.exit(-1)

        print("UI öğeleri başarıyla bulundu.") # DEBUG

        # UI öğeleri oluşturulduktan ve bağlandıktan sonra başlangıçta veri yüklemeyi devre dışı bırak.
        # self.tumbasvulari_getir() # Bu satırın yorum satırı yapıldığından veya silindiğinden emin olun

        # Sinyal ve Slot Bağlantıları
        self.pushButton_tumBasvurular.clicked.connect(self.tumbasvulari_getir)
        self.pushButton_tanimlananMentorGorusmesi.clicked.connect(self.mentor_gosrusmesi_tanimlananlar)
        self.pushButton_tanimlanmayanMentorGorusmesi.clicked.connect(self.mentor_gosrusmesi_tanimlanmayanlar)
        self.pushButton_oncekiVitKontrol.clicked.connect(self.onceki_vit_kontrol)
        self.pushButton_basvuruFiltrele.clicked.connect(self.basvurulari_filtrele)
        self.pushButton_mukerrerKayit.clicked.connect(self.mukerrer_kayitlar)
        self.pushButton_farkliKayit.clicked.connect(self.farkli_kayitlar)
        self.pushButton_tercihler.clicked.connect(self.tercihler_sayfasina_don)
        self.pushButton_exit.clicked.connect(self.cikis_yap)
        self.pushButton_ara.clicked.connect(self.arama_yapilamasi)
        print("Sinyaller başarıyla bağlandı.") # DEBUG
        
        print("BasvurularPage __init__ tamamlandı.") # DEBUG

    def set_logged_in_user(self, user_id, username, user_yetki):
        """Giriş yapan kullanıcının ID'sini, adını ve yetkisini ayarlar."""
        self.logged_in_user_id = user_id
        self.logged_in_username = username
        self.logged_in_user_yetki = user_yetki
        print(f"BasvurularPage: Giriş yapan kullanıcı ayarlandı - ID: {user_id}, Kullanıcı Adı: {username}, Yetki: {user_yetki}") # DEBUG

    def set_tercihler_page_references(self, admin_tercihler_page, kullanici_tercihler_page):
        """Admin ve Kullanıcı Tercihler sayfalarının referanslarını ayarlar."""
        self.admin_tercihler_page = admin_tercihler_page
        self.kullanici_tercihler_page = kullanici_tercihler_page
        print("BasvurularPage: Tercihler sayfa referansları ayarlandı.") # DEBUG

    def set_previous_page(self, page):
        """Bir önceki sayfanın referansını ayarlar."""
        self.previous_page = page
        print(f"BasvurularPage: Önceki sayfa referansı ayarlandı: {page.__class__.__name__}") # DEBUG

    def set_stacked_widget(self, stacked_widget_ref):
        """MainApp'taki QStackedWidget referansını ayarlar."""
        self.stacked_widget = stacked_widget_ref
        print("BasvurularPage: Stacked widget referansı ayarlandı.") # DEBUG

    def tercihler_sayfasina_don(self):
        """Giriş yapan kullanıcının yetkisine göre ilgili tercih sayfasına döner."""
        print("BasvurularPage: 'tercihler_sayfasina_don' çağrıldı.") # DEBUG
        
        if self.logged_in_user_yetki == 'admin':
            if self.admin_tercihler_page and self.stacked_widget:
                self.stacked_widget.setCurrentWidget(self.admin_tercihler_page)
                print("BasvurularPage: Admin Tercihler sayfasına yönlendirildi.") # DEBUG
            else:
                QMessageBox.warning(self, "Uyarı", "Admin Tercihler sayfası referansı veya stacked widget tanımsız.")
                print("BasvurularPage: Uyarı - Admin Tercihler sayfası referansı yok veya stacked widget ayarlanmamış.") # DEBUG
        elif self.logged_in_user_yetki == 'user':
            if self.kullanici_tercihler_page and self.stacked_widget:
                self.stacked_widget.setCurrentWidget(self.kullanici_tercihler_page)
                print("BasvurularPage: Kullanıcı Tercihler sayfasına yönlendirildi.") # DEBUG
            else:
                QMessageBox.warning(self, "Uyarı", "Kullanıcı Tercihler sayfası referansı veya stacked widget tanımsız.")
                print("BasvurularPage: Uyarı - Kullanıcı Tercihler sayfası referansı yok veya stacked widget ayarlanmamış.") # DEBUG
        else:
            # Yetki bilgisi yoksa veya tanımsızsa, önceki sayfaya dönmeye çalış
            if self.previous_page and self.stacked_widget:
                self.stacked_widget.setCurrentWidget(self.previous_page)
                print(f"BasvurularPage: Bilinmeyen yetki, önceki sayfa ({self.previous_page.__class__.__name__}) gösterildi.") # DEBUG
            else:
                QMessageBox.warning(self, "Uyarı", "Kullanıcı yetkisi bilinmiyor veya giriş yapılmamış. Geri dönülecek sayfa veya stacked widget tanımlanamadı.")
                print("BasvurularPage: Uyarı - Bilinmeyen yetki veya giriş yapılmadı, önceki sayfa/stacked widget da tanımlanmamış.") # DEBUG

    def set_table_data(self, headers, data):
        """Genel bir yardımcı fonksiyon: QTableWidget'ı başlıklar ve verilerle doldurur."""
        print("BasvurularPage: 'set_table_data' başladı.") # DEBUG
        self.tableWidget_goster.clearContents()
        self.tableWidget_goster.setRowCount(len(data))
        self.tableWidget_goster.setColumnCount(len(headers))

        # Başlıkları ayarla
        for col_idx, header in enumerate(headers):
            self.tableWidget_goster.setHorizontalHeaderItem(col_idx, QTableWidgetItem(header))
            self.tableWidget_goster.setColumnWidth(col_idx, max(100, len(str(header)) * 10)) # Kolon genişliğini ayarla

        # Verileri doldur
        for row_idx, row_data in enumerate(data):
            for col_idx, item_data in enumerate(row_data):
                self.tableWidget_goster.setItem(row_idx, col_idx, QTableWidgetItem(str(item_data if item_data is not None else '')))
            
        self.tableWidget_goster.resizeColumnsToContents()
        self.tableWidget_goster.horizontalHeader().setStretchLastSection(True)
        print("BasvurularPage: 'set_table_data' tamamlandı, tablo dolduruldu.") # DEBUG

    def tumbasvulari_getir(self):
        """Veritabanından tüm başvuruları çeker ve tabloya doldurur."""
        print("BasvurularPage: 'tumbasvulari_getir' başladı.") # DEBUG
        if self.db_manager is None:
            QMessageBox.critical(self, "Veritabanı Hatası", "Veritabanı yöneticisi başlatılmamış.")
            print("BasvurularPage: HATA - Veritabanı yöneticisi başlatılmamış (tumbasvulari_getir).") # DEBUG
            return

        try:
            with self.db_manager as db: # self.db_manager kullanıldı
                query = sql.SQL("""
                    SELECT 
                        k.adsoyad,           -- KURSİYER AD SOYAD (Yeni ilk sütun)
                        b.basvuruid,         -- BAŞVURU ID (İkinci sütun)
                        b.zamandamgasi, 
                        k.mailadresi, 
                        k.telefonnumarasi, 
                        k.postakodu, 
                        k.yasadiginizeyalet, 
                        b.suankidurum, 
                        b.itphegitimkatilmak, 
                        b.ekonomikdurum, 
                        b.dilkursunadevam, 
                        b.ingilizceseviye, 
                        b.hollandacaseviye, 
                        b.baskigoruyor, 
                        b.bootcampbitirdi, 
                        b.onlineitkursu, 
                        b.ittecrube, 
                        b.projedahil, 
                        b.calismakistegi, 
                        b.nedenkatilmakistiyor, 
                        b.basvurudonemi 
                    FROM 
                        basvurular b 
                    JOIN 
                        kursiyerler k ON b.kursiyerid = k.kursiyerid 
                    ORDER BY 
                        b.zamandamgasi DESC;
                """)
                
                result_dicts = db.fetch_all(query)
                print(f"BasvurularPage: Veritabanından çekilen başvuru verisi sayısı: {len(result_dicts) if result_dicts else 0}") # DEBUG
                
                if result_dicts:
                    # Sütun sırasını güncelledik: adsoyad ilk sırada, basvuruid ikinci sırada
                    db_column_keys_order = [
                        "adsoyad", "basvuruid", "zamandamgasi", "mailadresi", "telefonnumarasi",
                        "postakodu", "yasadiginizeyalet", "suankidurum", "itphegitimkatilmak",
                        "ekonomikdurum", "dilkursunadevam", "ingilizceseviye", "hollandacaseviye",
                        "baskigoruyor", "bootcampbitirdi", "onlineitkursu", "ittecrube",
                        "projedahil", "calismakistegi", "nedenkatilmakistiyor", "basvurudonemi"
                    ]

                    table_data_list_of_lists = []
                    for row_dict in result_dicts:
                        row_list = [row_dict.get(key) for key in db_column_keys_order]
                        table_data_list_of_lists.append(row_list)

                    # Başlık sırasını güncelledik: "Adınız Soyadınız" ilk sırada, "Başvuru ID" ikinci sırada
                    display_headers = [
                        "Adınız Soyadınız", "Başvuru ID", "Zaman Damgası", "Kursiyer Mail Adresi", "Telefon Numaranız", 
                        "Posta Kodunuz", "Yaşadığınız Eyalet", "Şu Anki Durum", "ITPH Eğitime Katılmak", 
                        "Ekonomik Durum", "Dil Kursuna Devam", "İngilizce Seviye", "Hollandaca Seviye", 
                        "Baskı Görüyor", "Bootcamp Bitirdi", "Online IT Kursu", "IT Tecrübe", 
                        "Projeye Dahil", "Çalışmak İstegi", "Neden Katılmak İstiyor", "Başvuru Dönemi"
                    ]
                    self.set_table_data(display_headers, table_data_list_of_lists)
                else:
                    QMessageBox.information(self, "Bilgi", "Veritabanında hiç başvuru bulunamadı.")
                    self.tableWidget_goster.clearContents()
                    self.tableWidget_goster.setRowCount(0)
                    self.tableWidget_goster.setColumnCount(0)
                    print("BasvurularPage: Tüm başvurular için boş sonuç.") # DEBUG

        except Error as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Veri çekme sırasında hata oluştu: {e}")
            print(f"BasvurularPage: HATA - Veritabanı hatası (tumbasvulari_getir): {e}") # DEBUG
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Beklenmeyen bir hata oluştu: {e}")
            print(f"BasvurularPage: HATA - Beklenmeyen hata (tumbasvulari_getir): {e}") # DEBUG
        print("BasvurularPage: 'tumbasvulari_getir' tamamlandı.")

    def mentor_gosrusmesi_tanimlananlar(self):
            """
            Mentor görüşmesi yapılmış (mentor_gorusmesi_yapildi sütunu 'OK' olan) başvuruları getirir.
            """
            print("BasvurularPage: 'mentor_gosrusmesi_tanimlananlar' başladı.") # DEBUG
            if self.db_manager is None:
                QMessageBox.critical(self, "Veritabanı Hatası", "Veritabanı yöneticisi başlatılmamış.")
                print("BasvurularPage: HATA - Veritabanı yöneticisi başlatılmamış (mentor_gosrusmesi_tanimlananlar).") # DEBUG
                return

            try:
                with self.db_manager as db:
                    query = sql.SQL("""
                        SELECT
                            k.adsoyad,                   -- KURSİYER AD SOYAD
                            b.basvuruid,                 -- BAŞVURU ID
                            b.zamandamgasi,
                            k.mailadresi,
                            k.telefonnumarasi,
                            k.postakodu,
                            k.yasadiginizeyalet,
                            b.suankidurum,
                            b.itphegitimkatilmak,
                            b.ekonomikdurum,
                            b.dilkursunadevam,
                            b.ingilizceseviye,
                            b.hollandacaseviye,
                            b.baskigoruyor,
                            b.bootcampbitirdi,
                            b.onlineitkursu,
                            b.ittecrube,
                            b.projedahil,
                            b.calismakistegi,
                            b.nedenkatilmakistiyor,
                            b.basvurudonemi,
                            b.mentor_gorusmesi_yapildi   -- Yeni eklendi
                        FROM
                            basvurular b
                        JOIN
                            kursiyerler k ON b.kursiyerid = k.kursiyerid
                        WHERE
                            TRIM(UPPER(b.mentor_gorusmesi_yapildi)) = 'OK'
                        ORDER BY
                            b.zamandamgasi DESC;
                    """)

                    result_dicts = db.fetch_all(query)
                    print(f"BasvurularPage: 'OK' olarak tanımlanmış mentor görüşmesi olan başvuru sayısı: {len(result_dicts) if result_dicts else 0}") # DEBUG

                    if result_dicts:
                        # Sütun sırasını güncelledik: adsoyad ilk sırada, basvuruid ikinci sırada
                        db_column_keys_order = [
                            "adsoyad", "basvuruid", "zamandamgasi", "mailadresi", "telefonnumarasi",
                            "postakodu", "yasadiginizeyalet", "suankidurum", "itphegitimkatilmak",
                            "ekonomikdurum", "dilkursunadevam", "ingilizceseviye", "hollandacaseviye",
                            "baskigoruyor", "bootcampbitirdi", "onlineitkursu", "ittecrube",
                            "projedahil", "calismakistegi", "nedenkatilmakistiyor", "basvurudonemi",
                            "mentor_gorusmesi_yapildi" # Yeni eklendi
                        ]

                        table_data_list_of_lists = []
                        for row_dict in result_dicts:
                            row_list = [row_dict.get(key) for key in db_column_keys_order]
                            table_data_list_of_lists.append(row_list)

                        # Başlık sırasını güncelledik: "Adınız Soyadınız" ilk sırada, "Başvuru ID" ikinci sırada
                        display_headers = [
                            "Adınız Soyadınız", "Başvuru ID", "Zaman Damgası", "Kursiyer Mail Adresi", "Telefon Numaranız",
                            "Posta Kodunuz", "Yaşadığınız Eyalet", "Şu Anki Durum", "ITPH Eğitime Katılmak",
                            "Ekonomik Durum", "Dil Kursuna Devam", "İngilizce Seviye", "Hollandaca Seviye",
                            "Baskı Görüyor", "Bootcamp Bitirdi", "Online IT Kursu", "IT Tecrübe",
                            "Projeye Dahil", "Çalışmak İstegi", "Neden Katılmak İstiyor", "Başvuru Dönemi",
                            "Mentor Görüşmesi Yapıldı" # Yeni eklendi
                        ]
                        self.set_table_data(display_headers, table_data_list_of_lists)
                    else:
                        QMessageBox.information(self, "Bilgi", " 'OK' olarak tanımlanan mentor görüşmesi olan başvuru bulunamadı.")
                        self.tableWidget_goster.clearContents()
                        self.tableWidget_goster.setRowCount(0)
                        self.tableWidget_goster.setColumnCount(0)
                        print("BasvurularPage: Tanımlanmış mentor görüşmesi için boş sonuç.") # DEBUG

            except Error as e:
                QMessageBox.critical(self, "Veritabanı Hatası", f"Veri çekme sırasında hata oluştu: {e}")
                print(f"BasvurularPage: HATA - Veritabanı hatası (mentor_gosrusmesi_tanimlananlar): {e}") # DEBUG
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Beklenmeyen bir hata oluştu: {e}")
                print(f"BasvurularPage: HATA - Beklenmeyen hata (mentor_gosrusmesi_tanimlananlar): {e}") # DEBUG
            print("BasvurularPage: 'mentor_gosrusmesi_tanimlananlar' tamamlandı.") # DEBUG

    def mentor_gosrusmesi_tanimlanmayanlar(self):
            """
            Mentor görüşmesi tanımlanmamış (mentor_gorusmesi_yapildi sütunu 'ATANMADI' olan) başvuruları getirir.
            """
            print("BasvurularPage: 'mentor_gosrusmesi_tanimlanmayanlar' başladı.") # DEBUG
            if self.db_manager is None:
                QMessageBox.critical(self, "Veritabanı Hatası", "Veritabanı yöneticisi başlatılmamış.")
                print("BasvurularPage: HATA - Veritabanı yöneticisi başlatılmamış (mentor_gosrusmesi_tanimlanmayanlar).") # DEBUG
                return

            try:
                with self.db_manager as db:
                    query = sql.SQL("""
                        SELECT
                            k.adsoyad,                   -- KURSİYER AD SOYAD
                            b.basvuruid,                 -- BAŞVURU ID
                            b.zamandamgasi,
                            k.mailadresi,
                            k.telefonnumarasi,
                            k.postakodu,
                            k.yasadiginizeyalet,
                            b.suankidurum,
                            b.itphegitimkatilmak,
                            b.ekonomikdurum,
                            b.dilkursunadevam,
                            b.ingilizceseviye,
                            b.hollandacaseviye,
                            b.baskigoruyor,
                            b.bootcampbitirdi,
                            b.onlineitkursu,
                            b.ittecrube,
                            b.projedahil,
                            b.calismakistegi,
                            b.nedenkatilmakistiyor,
                            b.basvurudonemi,
                            b.mentor_gorusmesi_yapildi   -- Yeni eklendi
                        FROM
                            basvurular b
                        JOIN
                            kursiyerler k ON b.kursiyerid = k.kursiyerid
                        WHERE
                            TRIM(UPPER(b.mentor_gorusmesi_yapildi)) = 'ATANMADI'
                            OR b.mentor_gorusmesi_yapildi IS NULL OR TRIM(b.mentor_gorusmesi_yapildi) = '' -- NULL veya boş stringleri de dahil et
                        ORDER BY
                            b.zamandamgasi DESC;
                    """)

                    result_dicts = db.fetch_all(query)
                    print(f"BasvurularPage: 'ATANMADI' olarak tanımlanmış mentor görüşmesi olan başvuru sayısı: {len(result_dicts) if result_dicts else 0}") # DEBUG

                    if result_dicts:
                        # Sütun sırasını güncelledik: adsoyad ilk sırada, basvuruid ikinci sırada
                        db_column_keys_order = [
                            "adsoyad", "basvuruid", "zamandamgasi", "mailadresi", "telefonnumarasi",
                            "postakodu", "yasadiginizeyalet", "suankidurum", "itphegitimkatilmak",
                            "ekonomikdurum", "dilkursunadevam", "ingilizceseviye", "hollandacaseviye",
                            "baskigoruyor", "bootcampbitirdi", "onlineitkursu", "ittecrube",
                            "projedahil", "calismakistegi", "nedenkatilmakistiyor", "basvurudonemi",
                            "mentor_gorusmesi_yapildi" # Yeni eklendi
                        ]

                        table_data_list_of_lists = []
                        for row_dict in result_dicts:
                            row_list = [row_dict.get(key) for key in db_column_keys_order]
                            table_data_list_of_lists.append(row_list)

                        # Başlık sırasını güncelledik: "Adınız Soyadınız" ilk sırada, "Başvuru ID" ikinci sırada
                        display_headers = [
                            "Adınız Soyadınız", "Başvuru ID", "Zaman Damgası", "Kursiyer Mail Adresi", "Telefon Numaranız",
                            "Posta Kodunuz", "Yaşadığınız Eyalet", "Şu Anki Durum", "ITPH Eğitime Katılmak",
                            "Ekonomik Durum", "Dil Kursuna Devam", "İngilizce Seviye", "Hollandaca Seviye",
                            "Baskı Görüyor", "Bootcamp Bitirdi", "Online IT Kursu", "IT Tecrübe",
                            "Projeye Dahil", "Çalışmak İstegi", "Neden Katılmak İstiyor", "Başvuru Dönemi",
                            "Mentor Görüşmesi Yapıldı" # Yeni eklendi
                        ]
                        self.set_table_data(display_headers, table_data_list_of_lists)
                    else:
                        QMessageBox.information(self, "Bilgi", " 'ATANMADI' olarak tanımlanmayan mentor görüşmesi olan başvuru bulunamadı.")
                        self.tableWidget_goster.clearContents()
                        self.tableWidget_goster.setRowCount(0)
                        self.tableWidget_goster.setColumnCount(0)
                        print("BasvurularPage: Tanımlanmamış mentor görüşmesi için boş sonuç.") # DEBUG

            except Error as e:
                QMessageBox.critical(self, "Veritabanı Hatası", f"Veri çekme sırasında hata oluştu: {e}")
                print(f"BasvurularPage: HATA - Veritabanı hatası (mentor_gosrusmesi_tanimlanmayanlar): {e}") # DEBUG
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Beklenmeyen bir hata oluştu: {e}")
                print(f"BasvurularPage: HATA - Beklenmeyen hata (mentor_gosrusmesi_tanimlanmayanlar): {e}") # DEBUG
            print("BasvurularPage: 'mentor_gosrusmesi_tanimlanmayanlar' tamamlandı.") # DEBUG

    def onceki_vit_kontrol(self):
        """
        data klasörü içindeki VIT klasörlerinde (VIT1, VIT2, VIT3 vb.) bulunan
        Basvurular.xlsx dosyalarını tarar. Aynı mail adresine sahip kişileri
        bulur ve hangi VIT'lere başvurduklarını tabloda gösterir.
        Mail adresi ile birlikte kursiyer ad ve soyadını da getirir.
        """
        print("BasvurularPage: 'onceki_vit_kontrol' başladı.") # DEBUG

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_folder_path = os.path.join(base_dir, "data")
        
        print(f"BasvurularPage: Aranacak data klasörü yolu: {data_folder_path}") # DEBUG
        
        if not os.path.exists(data_folder_path):
            QMessageBox.critical(self, "Hata", f"Data klasörü bulunamadı:\n{data_folder_path}\nLütfen klasör yapısını kontrol edin ve 'data' klasörünün doğru yerde olduğundan emin olun.")
            print(f"BasvurularPage: HATA - Data klasörü bulunamadı: {data_folder_path}") # DEBUG
            return

        # Tüm başvuruları tutacak sözlük: {mail_adresi: {'name': ad_soyad, 'vits': set_of_vits}}
        all_applicants = {} 

        for vit_folder_name in os.listdir(data_folder_path):
            vit_folder_full_path = os.path.join(data_folder_path, vit_folder_name)
            
            if vit_folder_name.startswith("VIT") and os.path.isdir(vit_folder_full_path):
                vit_number = vit_folder_name
                excel_file_path = os.path.join(vit_folder_full_path, "Basvurular.xlsx")

                if os.path.exists(excel_file_path):
                    print(f"BasvurularPage: '{excel_file_path}' dosyası okunuyor.") # DEBUG
                    try:
                        df = pd.read_excel(excel_file_path)

                        mail_col = None
                        name_col = None # Yeni: Ad Soyad sütunu için
                        
                        # Sütunları küçük harfe çevirerek arama yapalım
                        for col in df.columns:
                            col_lower = str(col).lower()
                            if "mail" in col_lower:
                                mail_col = col
                            if "ad soyad" in col_lower or "adınız soyadınız" in col_lower or "adı soyadı" in col_lower or "isim" in col_lower: # Ad soyad için alternatifler
                                name_col = col
                            
                            # Her ikisi de bulunduysa aramayı durdur
                            if mail_col is not None and name_col is not None:
                                break

                        if mail_col is not None: # Mail sütunu bulunduysa
                            if name_col is None: # Ad Soyad sütunu bulunamadıysa uyarı ver
                                print(f"BasvurularPage: UYARI - '{excel_file_path}' dosyasında 'Ad Soyad' sütunu bulunamadı. Mevcut sütunlar: {df.columns.tolist()}") # DEBUG
                                QMessageBox.warning(self, "Uyarı", f"'{vit_folder_name}' klasöründeki Basvurular.xlsx dosyasında 'Ad Soyad' sütunu bulunamadı.\nLütfen Excel dosyasındaki ad soyad sütun adını kontrol edin.")
                                # name_col bulunamasa bile mail ile devam edelim, ad soyad boş gelir
                                
                            for index, row in df.iterrows():
                                email = str(row[mail_col]).strip().lower()
                                name = str(row[name_col]).strip() if name_col is not None and pd.notna(row[name_col]) else "Bilinmiyor" # Ad soyad yoksa "Bilinmiyor"
                                
                                if email and '@' in email:
                                    if email not in all_applicants:
                                        all_applicants[email] = {'name': name, 'vits': set()}
                                    
                                    # Eğer aynı mail farklı VIT'lerde bulunuyorsa ve ad soyad bilgisi ilk kaydedilenden farklıysa,
                                    # ilk bulunan ad soyadı koruyabiliriz veya birleştirme stratejisi izleyebiliriz.
                                    # Şimdilik, ilk bulunan ad soyadı kullanmaya devam edelim veya sonrakini alalım.
                                    # Basitlik adına, mevcut ad soyad bilgisini güncelleyelim.
                                    all_applicants[email]['name'] = name # En son okunan ad soyadı kaydet
                                    all_applicants[email]['vits'].add(vit_number)
                        else:
                            print(f"BasvurularPage: UYARI - '{excel_file_path}' dosyasında 'Mail Adresi' sütunu bulunamadı. Mevcut sütunlar: {df.columns.tolist()}") # DEBUG
                            QMessageBox.warning(self, "Uyarı", f"'{vit_folder_name}' klasöründeki Basvurular.xlsx dosyasında 'Mail Adresi' sütunu bulunamadı.\nLütfen Excel dosyasındaki mail adresi sütun adını kontrol edin.")

                    except Exception as e:
                        QMessageBox.warning(self, "Dosya Okuma Hatası", f"'{excel_file_path}' okunurken hata oluştu:\n{e}")
                        print(f"BasvurularPage: HATA - '{excel_file_path}' okunurken hata: {e}") # DEBUG
                else:
                    print(f"BasvurularPage: '{excel_file_path}' bulunamadı, atlanıyor.") # DEBUG
        
        table_data = []
        for email, data in all_applicants.items():
            if len(data['vits']) > 1: # Birden fazla VIT'e başvurmuş olanlar
                table_data.append([data['name'], email, ", ".join(sorted(list(data['vits'])))])

        if table_data:
            headers = ["Ad Soyad", "Mail Adresi", "Başvurduğu VIT'ler"] # Başlıkları güncelledik
            self.set_table_data(headers, table_data)
            QMessageBox.information(self, "Bilgi", f"{len(table_data)} mükerrer başvuru bulundu ve tabloda gösterildi.")
            print(f"BasvurularPage: {len(table_data)} mükerrer başvuru bulundu.") # DEBUG
        else:
            QMessageBox.information(self, "Bilgi", "Mükerrer başvuru bulunamadı.")
            self.tableWidget_goster.clearContents()
            self.tableWidget_goster.setRowCount(0)
            self.tableWidget_goster.setColumnCount(0)
            print("BasvurularPage: Mükerrer başvuru bulunamadı.") # DEBUG

        print("BasvurularPage: 'onceki_vit_kontrol' tamamlandı.") # DEBUG
    
    def basvurulari_filtrele(self):
        QMessageBox.information(self, "Bilgi", "Bu özellik henüz uygulanmadı: Başvuruları Filtrele.")
        print("BasvurularPage: basvurulari_filtrele çağrıldı (uygulanmadı).") # DEBUG

    def mukerrer_kayitlar(self):
        QMessageBox.information(self, "Bilgi", "Bu özellik henüz uygulanmadı: Mükerrer Kayıtlar.")
        print("BasvurularPage: mukerrer_kayitlar çağrıldı (uygulanmadı).") # DEBUG

    def farkli_kayitlar(self):
        """
        data klasörü içindeki VIT klasörlerinde (VIT1, VIT2, VIT3 vb.) bulunan
        Basvurular.xlsx dosyalarını tarar. SADECE tek bir VIT dönemine
        başvurmuş kişileri (mükerrer olmayanları) bulur ve kursiyer ad soyadları
        ile birlikte hangi VIT'e başvurduklarını tabloda gösterir.
        """
        print("BasvurularPage: 'farkli_kayitlar' başladı.") # DEBUG

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_folder_path = os.path.join(base_dir, "data")
        
        print(f"BasvurularPage: Aranacak data klasörü yolu: {data_folder_path}") # DEBUG
        
        if not os.path.exists(data_folder_path):
            QMessageBox.critical(self, "Hata", f"Data klasörü bulunamadı:\n{data_folder_path}\nLütfen klasör yapısını kontrol edin ve 'data' klasörünün doğru yerde olduğundan emin olun.")
            print(f"BasvurularPage: HATA - Data klasörü bulunamadı: {data_folder_path}") # DEBUG
            return

        # Tüm başvuruları tutacak sözlük: {mail_adresi: {'name': ad_soyad, 'vits': set_of_vits}}
        all_applicants = {} 

        for vit_folder_name in os.listdir(data_folder_path):
            vit_folder_full_path = os.path.join(data_folder_path, vit_folder_name)
            
            if vit_folder_name.startswith("VIT") and os.path.isdir(vit_folder_full_path):
                vit_number = vit_folder_name
                excel_file_path = os.path.join(vit_folder_full_path, "Basvurular.xlsx")

                if os.path.exists(excel_file_path):
                    print(f"BasvurularPage: '{excel_file_path}' dosyası okunuyor.") # DEBUG
                    try:
                        df = pd.read_excel(excel_file_path)

                        mail_col = None
                        name_col = None 
                        
                        for col in df.columns:
                            col_lower = str(col).lower()
                            if "mail" in col_lower:
                                mail_col = col
                            if "ad soyad" in col_lower or "adiniz soyadiniz" in col_lower or "adı soyadı" in col_lower or "isim" in col_lower or "ad" in col_lower: 
                                name_col = col
                            
                            if mail_col is not None and name_col is not None:
                                break

                        if mail_col is not None:
                            if name_col is None: 
                                print(f"BasvurularPage: UYARI - '{vit_folder_name}' Basvurular.xlsx dosyasında 'Ad Soyad' sütunu bulunamadı. Mevcut sütunlar: {df.columns.tolist()}") # DEBUG
                                QMessageBox.warning(self, "Uyarı", f"'{vit_folder_name}' klasöründeki Basvurular.xlsx dosyasında 'Ad Soyad' sütunu bulunamadı.\nLütfen Excel dosyasındaki ad soyad sütun adını kontrol edin.")
                                
                            for index, row in df.iterrows():
                                email = str(row[mail_col]).strip().lower()
                                name = str(row[name_col]).strip() if name_col is not None and pd.notna(row[name_col]) else "Bilinmiyor"
                                
                                if email and '@' in email:
                                    if email not in all_applicants:
                                        all_applicants[email] = {'name': name, 'vits': set()}
                                    
                                    # Önemli: Eğer aynı mail adresiyle farklı ad soyadlar gelirse, ilk geleni koruyalım veya daha karmaşık bir mantık ekleyebiliriz.
                                    # Şimdilik, sadece ilk bulunan adı kullanacağız, çünkü buradaki hedef mükerrer olmayanları bulmak.
                                    # Veya her zaman son okunan adı güncelleyelim.
                                    all_applicants[email]['name'] = name # En son okunan adı kaydet
                                    all_applicants[email]['vits'].add(vit_number)
                        else:
                            print(f"BasvurularPage: UYARI - '{vit_folder_name}' Basvurular.xlsx dosyasında 'Mail Adresi' sütunu bulunamadı. Mevcut sütunlar: {df.columns.tolist()}") # DEBUG
                            QMessageBox.warning(self, "Uyarı", f"'{vit_folder_name}' klasöründeki Basvurular.xlsx dosyasında 'Mail Adresi' sütunu bulunamadı.\nLütfen Excel dosyasındaki mail adresi sütun adını kontrol edin.")

                    except Exception as e:
                        QMessageBox.warning(self, "Dosya Okuma Hatası", f"'{excel_file_path}' okunurken hata oluştu:\n{e}")
                        print(f"BasvurularPage: HATA - '{excel_file_path}' okunurken hata: {e}") # DEBUG
                else:
                    print(f"BasvurularPage: '{excel_file_path}' bulunamadı, atlanıyor.") # DEBUG
        
        # Sadece tek bir VIT'e başvurmuş olanları bul
        table_data = []
        for email, data in all_applicants.items():
            if len(data['vits']) == 1: # SADECE bir VIT'e başvurmuşsa
                vit_applied = list(data['vits'])[0] # Kümedeki tek öğeyi al
                table_data.append([data['name'], email, vit_applied]) # Ad Soyad, Mail, VIT

        if table_data:
            headers = ["Ad Soyad", "Mail Adresi", "Başvurduğu VIT"] # Başlıkları güncelledik
            self.set_table_data(headers, table_data)
            QMessageBox.information(self, "Bilgi", f"{len(table_data)} tekil başvuru bulundu ve tabloda gösterildi.")
            print(f"BasvurularPage: {len(table_data)} tekil başvuru bulundu.") # DEBUG
        else:
            QMessageBox.information(self, "Bilgi", "Tekil başvuru bulunamadı.")
            self.tableWidget_goster.clearContents()
            self.tableWidget_goster.setRowCount(0)
            self.tableWidget_goster.setColumnCount(0)
            print("BasvurularPage: Tekil başvuru bulunamadı.") # DEBUG

        print("BasvurularPage: 'farkli_kayitlar' tamamlandı.") # DEBUG

    def arama_yapilamasi(self):
        search_text = self.lineEdit_ara.text().strip().lower()
        print(f"BasvurularPage: 'arama_yapilamasi' çağrıldı. Arama metni: '{search_text}'") # DEBUG

        if not search_text:
            QMessageBox.information(self, "Bilgi", "Lütfen arama metni giriniz.")
            self.tumbasvulari_getir() # Arama metni boşsa tüm başvuruları tekrar göster
            print("BasvurularPage: Arama metni boş, tüm başvurular yenilendi.") # DEBUG
            return

        if self.db_manager is None:
            QMessageBox.critical(self, "Veritabanı Hatası", "Veritabanı yöneticisi başlatılmamış.")
            print("BasvurularPage: HATA - Veritabanı yöneticisi başlatılmamış (arama_yapilamasi).") # DEBUG
            return

        try:
            with self.db_manager as db: # self.db_manager kullanıldı
                # Hem Kursiyerler tablosundaki adsoyad ve mailadresi hem de Basvurular tablosundaki basvurudonemi, suankidurum alanlarında arama yapılıyor.
                # Arama türü seçeneği olmadığı için genel bir arama yapıldı.
                query = sql.SQL("""
                    SELECT 
                        k.adsoyad,           -- KURSİYER AD SOYAD (Yeni ilk sütun)
                        b.basvuruid,         -- BAŞVURU ID (İkinci sütun)
                        b.zamandamgasi, 
                        k.mailadresi, 
                        k.telefonnumarasi, 
                        k.postakodu, 
                        k.yasadiginizeyalet, 
                        b.suankidurum, 
                        b.itphegitimkatilmak, 
                        b.ekonomikdurum, 
                        b.dilkursunadevam, 
                        b.ingilizceseviye, 
                        b.hollandacaseviye, 
                        b.baskigoruyor, 
                        b.bootcampbitirdi, 
                        b.onlineitkursu, 
                        b.ittecrube, 
                        b.projedahil, 
                        b.calismakistegi, 
                        b.nedenkatilmakistiyor, 
                        b.basvurudonemi 
                    FROM 
                        basvurular b 
                    JOIN 
                        kursiyerler k ON b.kursiyerid = k.kursiyerid 
                    WHERE 
                        LOWER(k.adsoyad) LIKE %s OR 
                        LOWER(k.mailadresi) LIKE %s OR
                        LOWER(b.basvurudonemi) LIKE %s OR
                        LOWER(b.suankidurum) LIKE %s
                    ORDER BY 
                        b.zamandamgasi DESC;
                """)
                # search_text'i hem %s hem de %s olarak dört kez parametreye ekleyin
                results_dicts = db.fetch_all(query, (f"%{search_text}%", f"%{search_text}%", f"%{search_text}%", f"%{search_text}%"))
                print(f"BasvurularPage: Arama sonucu başvuru sayısı: {len(results_dicts) if results_dicts else 0}") # DEBUG

                if results_dicts:
                    # Sütun sırasını güncelledik: adsoyad ilk sırada, basvuruid ikinci sırada
                    db_column_keys_order = [
                        "adsoyad", "basvuruid", "zamandamgasi", "mailadresi", "telefonnumarasi",
                        "postakodu", "yasadiginizeyalet", "suankidurum", "itphegitimkatilmak",
                        "ekonomikdurum", "dilkursunadevam", "ingilizceseviye", "hollandacaseviye",
                        "baskigoruyor", "bootcampbitirdi", "onlineitkursu", "ittecrube",
                        "projedahil", "calismakistegi", "nedenkatilmakistiyor", "basvurudonemi"
                    ]

                    table_data_list_of_lists = []
                    for row_dict in results_dicts:
                        row_list = [row_dict.get(key) for key in db_column_keys_order]
                        table_data_list_of_lists.append(row_list)

                    # Başlık sırasını güncelledik: "Adınız Soyadınız" ilk sırada, "Başvuru ID" ikinci sırada
                    display_headers = [
                        "Adınız Soyadınız", "Başvuru ID", "Zaman Damgası", "Kursiyer Mail Adresi", "Telefon Numaranız", 
                        "Posta Kodunuz", "Yaşadığınız Eyalet", "Şu Anki Durum", "ITPH Eğitime Katılmak", 
                        "Ekonomik Durum", "Dil Kursuna Devam", "İngilizce Seviye", "Hollandaca Seviye", 
                        "Baskı Görüyor", "Bootcamp Bitirdi", "Online IT Kursu", "IT Tecrübe", 
                        "Projeye Dahil", "Çalışmak İstegi", "Neden Katılmak İstiyor", "Başvuru Dönemi"
                    ]
                    self.set_table_data(display_headers, table_data_list_of_lists)
                else:
                    QMessageBox.information(self, "Sonuç", "Arama kriterlerine uygun kayıt bulunamadı.")
                    self.tableWidget_goster.clearContents()
                    self.tableWidget_goster.setRowCount(0)
                    self.tableWidget_goster.setColumnCount(0)
                    print("BasvurularPage: Arama için boş sonuç.") # DEBUG

        except Error as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Arama sırasında bir hata oluştu: {e}")
            print(f"BasvurularPage: HATA - Veritabanı hatası (arama_yapilamasi): {e}") # DEBUG
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Beklenmeyen bir hata oluştu: {e}")
            print(f"BasvurularPage: HATA - Beklenmeyen hata (arama_yapilamasi): {e}") # DEBUG
        print("BasvurularPage: 'arama_yapilamasi' tamamlandı.") # DEBUG
    
    def cikis_yap(self):
        """Uygulamadan güvenli bir şekilde çıkar."""
        print("BasvurularPage: 'cikis_yap' çağrıldı, uygulama kapatılıyor.") # DEBUG
        QApplication.quit() # Uygulamayı kapat

# Bu blok, sadece basvurular.py dosyası doğrudan çalıştırıldığında aktif olur.
# Normalde uygulama main.py üzerinden başlatılacaktır.
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # DB_CONFIG'in database_manager.py'den doğru şekilde import edildiğinden emin olun.
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
    basvurular_page = BasvurularPage(temp_db_manager)
    
    # BasvurularPage'in test için bir stacked_widget'a ihtiyacı var
    # Basit bir QStackedWidget oluşturup atayalım
    test_stacked_widget = QtWidgets.QStackedWidget()
    test_stacked_widget.addWidget(basvurular_page)
    test_stacked_widget.setCurrentWidget(basvurular_page)
    basvurular_page.set_stacked_widget(test_stacked_widget)
    
    # Test ortamında display_all_basvurular'ı çağırabiliriz
    basvurular_page.tumbasvulari_getir()

    test_stacked_widget.show()
    sys.exit(app.exec())
