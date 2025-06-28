import sys
import os
from PyQt6 import uic, QtWidgets
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QTableWidgetItem, QPushButton, QLineEdit, QApplication
from datetime import date 

# Veritabanı yönetim modülünü import edin
from database_manager import DatabaseManager, DB_CONFIG 
import psycopg2 

class MulakatlarPage(QMainWindow):
    """
    Mülakatlar (Proje Takibi) sayfasını yöneten sınıf.
    Proje takip verilerini veritabanından çeker, tabloya doldurur,
    arama ve gönderiliş/geliş durumuna göre filtreleme yapar.
    """
    def __init__(self, db_manager): 
        super().__init__()
        self.db_manager = db_manager 
        print("MulakatlarPage __init__ başladı.") 

        ui_path = os.path.join(os.path.dirname(__file__), "..", "ui", 'mulakatlar_page_python.ui')
        if not os.path.exists(ui_path):
            QMessageBox.critical(self, "Hata", f"UI dosyası bulunamadı: {ui_path}\nUygulama kapatılıyor.")
            sys.exit(-1)

        uic.loadUi(ui_path, self)
        print(f"UI dosyası yüklendi: {ui_path}") 

        self.pushButton_ara = self.findChild(QtWidgets.QPushButton, "pushButton_ara")
        if self.pushButton_ara is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_ara bulunamadı. Lütfen Qt Designer'da objectName'ini kontrol edin.")
            sys.exit(-1)

        self.pushButton_projesiGonderilmisOlanlar = self.findChild(QtWidgets.QPushButton, "pushButton_projesiGonderilmisOlanlar")
        if self.pushButton_projesiGonderilmisOlanlar is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_projesiGonderilmisOlanlar bulunamadı. Lütfen Qt Designer'da objectName'ini kontrol edin.")
            sys.exit(-1)

        self.pushButton_ProjesiGelmisOlanlar = self.findChild(QtWidgets.QPushButton, "pushButton_ProjesiGelmisOlanlar")
        if self.pushButton_ProjesiGelmisOlanlar is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_ProjesiGelmisOlanlar bulunamadı. Lütfen Qt Designer'da objectName'ini kontrol edin.")
            sys.exit(-1)

        self.pushButton_tercihler = self.findChild(QtWidgets.QPushButton, "pushButton_tercihler")
        if self.pushButton_tercihler is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_tercihler bulunamadı. Lütfen Qt Designer'da objectName'ini kontrol edin.")
            sys.exit(-1)
        
        self.lineEdit_ara = self.findChild(QLineEdit, "lineEdit_ara")
        if self.lineEdit_ara is None:
            QMessageBox.critical(self, "UI Hatası", "lineEdit_ara bulunamadı. Lütfen Qt Designer'da objectName'ini kontrol edin.")
            sys.exit(-1)

        self.tableWidget = self.findChild(QtWidgets.QTableWidget, "tableWidget") 
        if self.tableWidget is None:
            self.tableWidget = self.findChild(QtWidgets.QTableWidget, "tableWidget_mentor") 
            if self.tableWidget is None:
                QMessageBox.critical(self, "UI Hatası", "tableWidget veya tableWidget_mentor bulunamadı. Lütfen Qt Designer'da objectName'ini kontrol edin.")
                sys.exit(-1)

        print("UI öğeleri başarıyla bulundu.") 

        self.pushButton_ara.clicked.connect(self.search)
        self.pushButton_projesiGonderilmisOlanlar.clicked.connect(self.projesi_gonderilmis_olanlar)
        self.pushButton_ProjesiGelmisOlanlar.clicked.connect(self.projesi_gelmis_olanlar)
        self.pushButton_tercihler.clicked.connect(self.go_back)
        print("Sinyaller başarıyla bağlandı.") 
        
        self.tableWidget.setColumnCount(0)
        self.tableWidget.setRowCount(0)
        self.tableWidget.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        print("Tablo düzenleme devre dışı bırakıldı.") 

        self.previous_page = None
        self.logged_in_user_id = None
        self.logged_in_username = None
        self.logged_in_user_yetki = None

        print("MulakatlarPage __init__ tamamlandı.") 

    def set_logged_in_user(self, user_id, username, user_yetki):
        self.logged_in_user_id = user_id
        self.logged_in_username = username
        self.logged_in_user_yetki = user_yetki
        print(f"MulakatlarPage: Giriş yapan kullanıcı ayarlandı - ID: {user_id}, Kullanıcı Adı: {username}, Yetki: {user_yetki}") 

    def set_previous_page(self, page):
        self.previous_page = page
        print(f"MulakatlarPage: Önceki sayfa referansı ayarlandı: {page.__class__.__name__}") 

    def load_mulakat_data_from_db(self):
        """
        Veritabanından proje takip verilerini çeker.
        projetakiptablosu'nu kursiyerler ve kullanicilar tablolarıyla JOIN ederek 
        kursiyer adını, sorumlu kullanıcı adını ve proje_gonderildi_mi bilgisini getirir.
        """
        print("MulakatlarPage: 'load_mulakat_data_from_db' başladı.") 
        
        headers = []
        data = []

        if self.db_manager is None:
            QMessageBox.critical(self, "Veritabanı Hatası", "Veritabanı yöneticisi başlatılmamış.")
            print("MulakatlarPage: HATA - Veritabanı yöneticisi başlatılmamış (load_mulakat_data_from_db).") 
            return [], []

        try:
            with self.db_manager as db: 
                query = psycopg2.sql.SQL("""
                SELECT
                    pt.projetakipid,
                    pt.kursiyerid,
                    k.adsoyad AS kursiyer_ad_soyad,
                    u.kullaniciadi AS sorumlu_kullanici_adi,
                    pt.projegonderilistarihi,
                    pt.projeningelistarihi,
                    pt.proje_gonderildi_mi
                FROM projetakiptablosu AS pt
                JOIN kursiyerler AS k ON pt.kursiyerid = k.kursiyerid
                JOIN kullanicilar AS u ON pt.kullaniciid = u.kullaniciid
                ORDER BY pt.projetakipid ASC;
                """)
                
                result_dicts = db.fetch_all(query)
                print(f"MulakatlarPage: Veritabanından çekilen mülakat verisi sayısı: {len(result_dicts) if result_dicts else 0}") 

                if not result_dicts: 
                    print("MulakatlarPage: load_mulakat_data_from_db: Veritabanı sorgusu boş sonuç döndürdü.") 
                    return [], []

                # Headers (Sütun başlıkları) - Sorgudaki SELECT kısmındaki alias'lar ile eşleşmelidir.
                # Yorum satırı Python listesi elemanının hemen yanında olmamalıdır.
                headers = [
                    "projetakipid", 
                    "kursiyerid", 
                    "kursiyer_ad_soyad", 
                    "sorumlu_kullanici_adi", 
                    "projegonderilistarihi", 
                    "projeningelistarihi", 
                    "proje_gonderildi_mi" # Düzeltildi: Yorum kaldırıldı
                ]
                
                for row_dict in result_dicts:
                    row_list = [row_dict.get(key) for key in headers] 
                    data.append(row_list)
                
            print("MulakatlarPage: 'load_mulakat_data_from_db' tamamlandı.") 
            return headers, data
        except psycopg2.Error as e: 
            QMessageBox.critical(self, "Veritabanı Hatası", f"Mülakat verileri çekilirken bir hata oluştu: {e}")
            print(f"MulakatlarPage: HATA - Veritabanı hatası (load_mulakat_data_from_db): {e}") 
            return [], []
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Beklenmeyen bir hata oluştu: {e}")
            print(f"MulakatlarPage: HATA - Beklenmeyen hata (load_mulakat_data_from_db): {e}") 
            return [], []

    def display_data(self, headers, data):
        """Verilen başlık ve veriyi tablo widget'ında gösterir."""
        print("MulakatlarPage: 'display_data' başladı.") 
        
        # UI'da gösterilecek daha kullanıcı dostu başlıklar
        # Bu listenin sırası load_mulakat_data_from_db'den gelen 'headers' ile aynı olmalıdır.
        display_headers = [
            "Proje Takip ID", "Kursiyer ID", "Kursiyer Ad Soyad", "Sorumlu Kullanıcı Adı",
            "Proje Gönderiliş Tarihi", "Projenin Geliş Tarihi", "Proje Gönderildi Mi?" 
        ]
        
        self.tableWidget.clearContents() 
        
        if len(display_headers) != len(headers):
            print("UYARI: display_headers ile çekilen headers uzunluğu uyuşmuyor. display_headers kullanılmayacak.") 
            self.tableWidget.setColumnCount(len(headers))
            self.tableWidget.setHorizontalHeaderLabels(headers)
        else:
            self.tableWidget.setColumnCount(len(display_headers))
            self.tableWidget.setHorizontalHeaderLabels(display_headers) 

        self.tableWidget.setRowCount(len(data))

        for row_idx, row_data in enumerate(data):
            for col_idx, cell_data in enumerate(row_data):
                if isinstance(cell_data, date):
                    item_text = cell_data.isoformat() 
                else:
                    item_text = str(cell_data) if cell_data is not None else ""
                
                item = QTableWidgetItem(item_text)
                self.tableWidget.setItem(row_idx, col_idx, item)

        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableWidget.horizontalHeader().setStretchLastSection(True) 
        print("MulakatlarPage: 'display_data' tamamlandı, tablo dolduruldu.") 

    def display_all_mulakatlar(self):
        """Tüm mülakat verilerini tabloda gösterir."""
        print("MulakatlarPage: 'display_all_mulakatlar' başladı.") 
        headers, data = self.load_mulakat_data_from_db()
        if not data:
            print("MulakatlarPage: Görüntülenecek tüm mülakat verisi bulunamadı.") 
            self.tableWidget.clearContents()
            self.tableWidget.setRowCount(0)
            self.tableWidget.setColumnCount(0)
            QMessageBox.information(self, "Bilgi", "Veritabanında hiç mülakat/proje takip kaydı bulunamadı.")
            return
        self.display_data(headers, data)
        print("MulakatlarPage: 'display_all_mulakatlar' tamamlandı.") 

    def search(self):
        print("MulakatlarPage: 'search' başladı.") 
        
        if self.lineEdit_ara is None:
            QMessageBox.critical(self, "Hata", "Arama kutusu (lineEdit_ara) UI'da bulunamadı. Arama yapılamaz.")
            print("MulakatlarPage: HATA - lineEdit_ara bulunamadı.") 
            return

        search_text = self.lineEdit_ara.text().strip().lower()
        if not search_text:
            QMessageBox.information(self, "Bilgi", "Lütfen arama metni giriniz.")
            self.display_all_mulakatlar()
            print("MulakatlarPage: Arama metni boş, tüm mülakatlar gösterildi.") 
            return

        headers, all_data_list_of_lists = self.load_mulakat_data_from_db()
        if not all_data_list_of_lists:
            print("MulakatlarPage: Hata - Arama için veri bulunamadı.") 
            QMessageBox.information(self, "Bilgi", "Veritabanında arama yapılacak mülakat verisi bulunamadı.")
            return

        filtered_list_of_lists = []
        kursiyer_ad_index = headers.index("kursiyer_ad_soyad") if "kursiyer_ad_soyad" in headers else -1
        sorumlu_kullanici_index = headers.index("sorumlu_kullanici_adi") if "sorumlu_kullanici_adi" in headers else -1

        for row_list in all_data_list_of_lists:
            kursiyer_matched = (kursiyer_ad_index != -1 and 
                                 row_list[kursiyer_ad_index] is not None and 
                                 str(row_list[kursiyer_ad_index]).lower().startswith(search_text))
            
            sorumlu_matched = (sorumlu_kullanici_index != -1 and 
                               row_list[sorumlu_kullanici_index] is not None and 
                               str(row_list[sorumlu_kullanici_index]).lower().startswith(search_text))

            if kursiyer_matched or sorumlu_matched:
                filtered_list_of_lists.append(row_list)

        if not filtered_list_of_lists:
            QMessageBox.information(self, "Sonuç", "Arama kriterlerine uygun kayıt bulunamadı.")
            self.tableWidget.clearContents()
            self.tableWidget.setRowCount(0)
            self.tableWidget.setColumnCount(0)
            print("MulakatlarPage: Arama sonucu boş.") 
            return
        
        self.display_data(headers, filtered_list_of_lists)
        print("MulakatlarPage: 'search' tamamlandı, filtrelenmiş veriler gösterildi.") 


    def filter_mulakat_data(self, filter_type):
        """
        Mülakat verilerini belirli bir duruma göre filtreler.
        filter_type: 
            'gonderilmis': proje_gonderildi_mi = 'evet' olanlar
            'gelmis': projeningelistarihi NOT NULL olanlar
        """
        print(f"MulakatlarPage: 'filter_mulakat_data' başladı (filter_type: {filter_type}).") 
        headers, all_data_list_of_lists = self.load_mulakat_data_from_db()
        if not all_data_list_of_lists:
            print("MulakatlarPage: Filtreleme için veri bulunamadı.") 
            QMessageBox.information(self, "Bilgi", "Veritabanında filtreleme yapılacak mülakat verisi bulunamadı.")
            return

        proje_gonderildi_mi_idx = -1
        projeningelistarihi_idx = -1

        if "proje_gonderildi_mi" in headers:
            proje_gonderildi_mi_idx = headers.index("proje_gonderildi_mi")
        if "projeningelistarihi" in headers:
            projeningelistarihi_idx = headers.index("projeningelistarihi")

        if filter_type == 'gonderilmis' and proje_gonderildi_mi_idx == -1:
            QMessageBox.critical(self, "Hata", "Veritabanından 'proje_gonderildi_mi' sütunu çekilemedi. Lütfen SQL sorgunuzu ve tablo yapınızı kontrol edin.")
            print("MulakatlarPage: HATA - 'proje_gonderildi_mi' sütunu bulunamadı.")
            return
        
        if filter_type == 'gelmis' and projeningelistarihi_idx == -1:
            QMessageBox.critical(self, "Hata", "Veritabanından 'projeningelistarihi' sütunu çekilemedi. Lütfen SQL sorgunuzu ve tablo yapınızı kontrol edin.")
            print("MulakatlarPage: HATA - 'projeningelistarihi' sütunu bulunamadı.")
            return

        filtered_list_of_lists = []
        for row_list in all_data_list_of_lists:
            if filter_type == 'gonderilmis': 
                # 'proje_gonderildi_mi' sütunu 'evet' olanları filtrele
                proje_gonderildi_mi_value = str(row_list[proje_gonderildi_mi_idx]).lower() if proje_gonderildi_mi_idx != -1 and row_list[proje_gonderildi_mi_idx] is not None else ""
                if proje_gonderildi_mi_value == 'evet':
                    filtered_list_of_lists.append(row_list)
            elif filter_type == 'gelmis': 
                # 'projeningelistarihi' sütunu NULL olmayanları filtrele
                project_received_date = row_list[projeningelistarihi_idx] if projeningelistarihi_idx != -1 else None
                if project_received_date is not None:
                    filtered_list_of_lists.append(row_list)

        if not filtered_list_of_lists:
            status_text = "proje_gonderildi_mi 'evet' olan" if filter_type == 'gonderilmis' else "gelmiş olan"
            QMessageBox.information(self, "Sonuç", f"{status_text} kayıt bulunamadı.")
            self.tableWidget.clearContents()
            self.tableWidget.setRowCount(0)
            self.tableWidget.setColumnCount(0)
            print(f"MulakatlarPage: {status_text} kayıtlar için boş sonuç.") 
            return
        
        self.display_data(headers, filtered_list_of_lists)
        print("MulakatlarPage: 'filter_mulakat_data' tamamlandı, filtrelenmiş veriler gösterildi.") 


    def projesi_gonderilmis_olanlar(self):
        """'proje_gonderildi_mi' sütunu 'evet' olanları gösterir."""
        print("MulakatlarPage: 'projesi_gonderilmis_olanlar' çağrıldı.") 
        self.filter_mulakat_data('gonderilmis')

    def projesi_gelmis_olanlar(self):
        """'projeningelistarihi' sütunu dolu olan adayları gösterir (projesi teslim edilmiş)."""
        print("MulakatlarPage: 'projesi_gelmis_olanlar' çağrıldı.") 
        self.filter_mulakat_data('gelmis')

    def go_back(self):
        print("MulakatlarPage: 'go_back' çağrıldı.") 
        if self.previous_page:
            if hasattr(QApplication.instance(), 'stacked_widget'):
                QApplication.instance().stacked_widget.setCurrentWidget(self.previous_page)
            else:
                self.previous_page.show()
                self.hide()
            print("MulakatlarPage: Önceki sayfa gösterildi, bu sayfa gizlendi.") 
        else:
            QMessageBox.warning(self, "Uyarı", "Geri dönülecek bir sayfa tanımlanmamış.")
            print("MulakatlarPage: Uyarı - Geri dönülecek sayfa bulunamadı.") 

    def set_stacked_widget(self, stacked_widget_ref):
        self.stacked_widget = stacked_widget_ref


if __name__ == "__main__":
    app = QApplication(sys.argv)
    temp_db_manager = DatabaseManager(DB_CONFIG)
    mulakatlar_window = MulakatlarPage(temp_db_manager)
    mulakatlar_window.show()
    sys.exit(app.exec())