import sys
import os
from PyQt6 import uic, QtWidgets
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QApplication, QTableWidgetItem, QLineEdit, QComboBox, QVBoxLayout, QPushButton
from datetime import date # Tarih objeleri için

# Veritabanı yönetim modülünü import edin (aynı dizimde olduğu varsayılıyor)
from database_manager import DatabaseManager, DB_CONFIG # DatabaseManager ve DB_CONFIG'i import ediyoruz
import psycopg2 # psycopg2 modülünün tamamını import ediyoruz

class MentorPage(QMainWindow):
    """
    Mentor Görüşmeleri sayfasını yöneten sınıf.
    Mentor görüşmelerini görüntüler, siler ve arar.
    """
    def __init__(self, db_manager): # db_manager parametresi eklendi
        super().__init__()
        self.db_manager = db_manager # DatabaseManager objesini sakla
        print("MentorPage __init__ başladı.") # DEBUG

        # UI dosyasının yolunu dinamik olarak belirliyoruz.
        ui_path = os.path.join(os.path.dirname(__file__), "..", "ui", 'mentor_page_python.ui')
        if not os.path.exists(ui_path):
            QMessageBox.critical(self, "Hata", f"UI dosyası bulunamadı: {ui_path}\nUygulama kapatılıyor.")
            sys.exit(-1)

        uic.loadUi(ui_path, self)
        print(f"UI dosyası yüklendi: {ui_path}") # DEBUG

        self.previous_page = None # Önceki sayfa referansını tutar (geri dönmek için)
        self.logged_in_user_id = None # Giriş yapan kullanıcının ID'sini tutar
        self.logged_in_username = None # Giriş yapan kullanıcının adını tutar
        self.logged_in_user_yetki = None # Giriş yapan kullanıcının yetkisini tutar
        self.stacked_widget = None # MainApp'teki QStackedWidget referansını tutar

        # --- UI öğelerini bulma ---
        self.tableWidget = self.findChild(QtWidgets.QTableWidget, "tableWidget_mentor") 
        if self.tableWidget is None:
            QMessageBox.critical(self, "UI Hatası", "tableWidget_mentor bulunamadı. Lütfen Qt Designer'da objectName'ini kontrol edin.")
            sys.exit(-1)

        self.lineEdit_ara = self.findChild(QLineEdit, "lineEdit_ara")
        if self.lineEdit_ara is None:
            QMessageBox.critical(self, "UI Hatası", "lineEdit_ara bulunamadı. Lütfen Qt Designer'da objectName'ini kontrol edin.") 
            sys.exit(-1)

        self.comboBox_cokluSekme = self.findChild(QComboBox, "comboBox_cokluSekme")
        if self.comboBox_cokluSekme is None:
            QMessageBox.critical(self, "UI Hatası", "comboBox_cokluSekme bulunamadı. Lütfen Qt Designer'da objectName'ini kontrol edin.") 
            sys.exit(-1)
        
        # ComboBox'ı temizlemeden önce kontrol et
        if self.comboBox_cokluSekme:
            self.comboBox_cokluSekme.clear() # Mevcut öğeleri temizle
        
        # ComboBox öğeleri sadece görseldeki seçenekleri içerecek şekilde güncellendi
        self.comboBox_cokluSekme.addItems([
            "Make your choice",
            "VIT Projesinin Tamamına Katılması Uygun Olur",
            "VIT Projesi ilk IT Eğitimi Alarak Yönlendirilmesi Uygun Olur",
            "VIT Projesi İngilizce Eğitimine Yönlendirilmesi Uygun Olur",
            "VIT Projesi Kapsamında Direkt İşe Yönlendirilmesi Uygun Olur",
            "Direkt Bireysel Koçluk ile İşe Yönlendirilmesi Uygun Olur",
            "Bir Sonraki VIT Projesine Katılması Daha Uygun Olur",
            "Başka Bir Sektöre Yönlendirilmeli",
            "Diğer"
        ]) 

        self.btn_search = self.findChild(QPushButton, "pushButton_ara")
        if self.btn_search is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_ara bulunamadı. Lütfen Qt Designer'da objectName'ini kontrol edin.") 
            sys.exit(-1)
        
        self.btn_delete = None # Silme butonu şu an için devre dışı bırakıldı
        
        self.pushButton_tumGorusmeler = self.findChild(QtWidgets.QPushButton, "pushButton_tumGorusmeler")
        if self.pushButton_tumGorusmeler is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_tumGorusmeler bulunamadı. Lütfen Qt Designer'da objectName'ini kontrol edin.") 
            sys.exit(-1)

        self.pushButton_tercihler = self.findChild(QtWidgets.QPushButton,"pushButton_tercihler")
        if self.pushButton_tercihler is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_tercihler bulunamadı.") 
            sys.exit(-1)

        self.pushButton_exit = self.findChild(QtWidgets.QPushButton,"pushButton_exit")
        if self.pushButton_exit is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_exit bulunamadı.") 
            sys.exit(-1)

        print("UI öğeleri başarıyla bulundu.") # DEBUG

        # Sinyal ve Slot Bağlantıları
        # Arama ve filtreleme işlevini tek bir metoda bağla
        self.btn_search.clicked.connect(self.apply_filters)
        self.comboBox_cokluSekme.currentTextChanged.connect(self.apply_filters) # ComboBox değiştiğinde filtrele
        self.lineEdit_ara.textChanged.connect(self.apply_filters) # Arama metni değiştiğinde filtrele

        self.pushButton_tumGorusmeler.clicked.connect(self.display_mentor_gorusmeleri)
        self.pushButton_tercihler.clicked.connect(self.go_to_previous_page)
        self.pushButton_exit.clicked.connect(self.cikis_yap)
        print("Sinyaller başarıyla bağlandı.") # DEBUG

        print("MentorPage __init__ tamamlandı.") # DEBUG

    def set_logged_in_user(self, user_id, username, user_yetki):
        """Giriş yapan kullanıcının ID'sini, adını ve yetkisini ayarlar."""
        self.logged_in_user_id = user_id
        self.logged_in_username = username
        self.logged_in_user_yetki = user_yetki
        print(f"MentorPage: Giriş yapan kullanıcı ayarlandı - ID: {user_id}, Kullanıcı Adı: {username}, Yetki: {user_yetki}")

    def set_previous_page(self, page):
        """Bir önceki sayfanın referansını ayarlar."""
        self.previous_page = page
        print(f"MentorPage: Önceki sayfa referansı ayarlandı: {page.__class__.__name__}")

    def set_stacked_widget(self, stacked_widget_ref):
        """MainApp'taki QStackedWidget referansını ayarlar."""
        self.stacked_widget = stacked_widget_ref
        print("MentorPage: Stacked widget referansı ayarlandı.") # DEBUG

    def go_to_previous_page(self):
        """Önceki sayfaya geri döner."""
        print("MentorPage: 'go_to_previous_page' çağrıldı.")
        if self.previous_page and self.stacked_widget: # stacked_widget kontrolü eklendi
            self.stacked_widget.setCurrentWidget(self.previous_page)
            print("MentorPage: Önceki sayfa gösterildi.")
        else:
            QMessageBox.warning(self, "Uyarı", "Geri dönülecek bir sayfa veya stacked widget tanımlanmamış.")
            print("MentorPage: Uyarı - Geri dönülecek sayfa veya stacked widget bulunamadı.")

    def display_mentor_gorusmeleri(self):
        """Veritabanından mentor görüşmelerini çeker ve tabloda gösterir."""
        self.clear_form_fields()
        if self.db_manager is None:
            QMessageBox.critical(self, "Veritabanı Hatası", "Veritabanı yöneticisi başlatılmamış.")
            print("MentorPage: HATA - Veritabanı yöneticisi başlatılmamış (display_mentor_gorusmeleri).")
            return
        try:
            with self.db_manager as db:
                query = psycopg2.sql.SQL("""
                    SELECT 
                        mg.mentorid, 
                        k.adsoyad AS kursiyer_adsoyad,
                        mg.gorusmetarihi, 
                        mg.yorumlar, 
                        mg.bilgisahibimi,
                        mg.vitprojesinekatilabilirmi,
                        mg.dusunce,
                        mg.yogunlukdurumu
                    FROM mentortablosu AS mg
                    JOIN kursiyerler AS k ON mg.kursiyerid = k.kursiyerid
                    ORDER BY mg.gorusmetarihi DESC; 
                """)
                results = db.fetch_all(query)

                self.tableWidget.clearContents()
                headers_display = ["Mentor ID", "Kursiyer Ad Soyad", "Görüşme Tarihi", "Yorumlar", 
                                   "Bilgi Sahibi Mi?", "VIT Projesine Katılabilir Mi?", "Düşünce", "Yoğunluk Durumu"]
                
                headers_db = ["mentorid", "kursiyer_adsoyad", "gorusmetarihi", "yorumlar",
                              "bilgisahibimi", "vitprojesinekatilabilirmi", "dusunce", "yogunlukdurumu"]

                self.tableWidget.setColumnCount(len(headers_display))
                self.tableWidget.setHorizontalHeaderLabels(headers_display)
                self.tableWidget.setRowCount(0)

                if results:
                    self.tableWidget.setRowCount(len(results))
                    for row_idx, gorusme in enumerate(results):
                        for col_idx, key in enumerate(headers_db):
                            item_data = gorusme.get(key)
                            if isinstance(item_data, date):
                                item_text = item_data.isoformat()
                            else:
                                item_text = str(item_data) if item_data is not None else ""
                            self.tableWidget.setItem(row_idx, col_idx, QTableWidgetItem(item_text))
                else:
                    QMessageBox.information(self, "Bilgi", "Mentor görüşmesi bulunamadı.")

        except psycopg2.Error as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Mentor görüşmeleri çekilirken hata oluştu: {e}")
            print(f"MentorPage: HATA - Veritabanı hatası (display_mentor_gorusmeleri): {e}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Beklenmeyen bir hata oluştu: {e}")
            print(f"MentorPage: HATA - Beklenmeyen hata (display_mentor_gorusmeleri): {e}")

        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        print("MentorPage: 'display_mentor_gorusmeleri' tamamlandı.") # DEBUG

    def clear_form_fields(self):
        """Form alanlarını temizler."""
        if self.lineEdit_ara: 
            self.lineEdit_ara.clear()
        # ComboBox'ı "Make your choice"a sıfırla (isteğe bağlı)
        if self.comboBox_cokluSekme:
            index = self.comboBox_cokluSekme.findText("Make your choice")
            if index != -1:
                self.comboBox_cokluSekme.setCurrentIndex(index)
        print("MentorPage: Form alanları temizlendi.")

    def delete_mentor_gorusmesi(self):
        """Seçili mentor görüşmesini siler."""
        print("MentorPage: 'delete_mentor_gorusmesi' başladı.")
        selected_items = self.tableWidget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Uyarı", "Lütfen silinecek bir mentor görüşmesi seçin.")
            print("MentorPage: Silme için kayıt seçilmedi.")
            return

        QMessageBox.warning(self, "Uyarı", 
                            "Bu tabloda benzersiz bir 'Görüşme ID'si bulunmadığı için silme işlemi şu an için güvenli değildir.\n"
                            "Lütfen veritabanı şemanızda her görüşme için benzersiz bir ID sütunu (örn. gorusmeid) olduğundan emin olun.")
        print("MentorPage: Silme işlemi, benzersiz ID eksikliği nedeniyle durduruldu.")
        return 

    def apply_filters(self):
        """Arama kutusundaki metne ve seçili arama türüne göre mentor görüşmelerini filtreler."""
        print("MentorPage: 'apply_filters' başladı.")
        
        # UI öğelerinin varlığını kontrol et
        if not (self.lineEdit_ara and self.comboBox_cokluSekme):
            QMessageBox.critical(self, "UI Hatası", "Arama alanları (Arama kutusu veya Arama Türü) tanımlanmamış. Arama yapılamaz.") 
            print("MentorPage: ERROR - Gerekli UI alanları eksik.")
            return

        search_text = self.lineEdit_ara.text().strip().lower()
        selected_category = self.comboBox_cokluSekme.currentText()
        print(f"DEBUG: Arama metni: '{search_text}', Seçilen Kategori: '{selected_category}'") # DEBUG: Arama parametrelerini yazdır

        # Eğer "Make your choice" seçili ve arama metni boşsa, tüm verileri göster
        if selected_category == "Make your choice" and not search_text:
            self.display_mentor_gorusmeleri()
            print("MentorPage: 'Make your choice' seçildi ve arama metni boş. Tüm görüşmeler görüntülendi.")
            return
        
        if self.db_manager is None:
            QMessageBox.critical(self, "Veritabanı Hatası", "Veritabanı yöneticisi başlatılmamış.")
            print("MentorPage: ERROR - Veritabanı yöneticisi başlatılmamış (apply_filters).")
            return

        try:
            with self.db_manager as db:
                where_clauses = []
                params = []

                # Kategoriye göre filtreleme (ComboBox)
                if selected_category != "Make your choice":
                    # "Bir Sonraki VIT Projesine Katılması Daha Uygun Olur" ve "Diğer" seçenekleri için özel kontrol
                    if selected_category == "Bir Sonraki VIT Projesine Katılması Daha Uygun Olur":
                        where_clauses.append(psycopg2.sql.SQL("LOWER(mg.vitprojesinekatilabilirmi) LIKE %s"))
                        params.append(f"%{selected_category.lower()}%")
                    elif selected_category == "Diğer":
                        # "Diğer" hem vitprojesinekatilabilirmi hem de dusunce sütunlarında aranabilir
                        # 'ğ' ve 'g' farklılıklarını hesaba katmak için hem "diğer" hem de "diger" arıyoruz.
                        where_clauses.append(psycopg2.sql.SQL("(LOWER(mg.dusunce) LIKE %s OR LOWER(mg.dusunce) LIKE %s OR LOWER(mg.vitprojesinekatilabilirmi) LIKE %s OR LOWER(mg.vitprojesinekatilabilirmi) LIKE %s)"))
                        params.extend([f"%{'diğer'.lower()}%", f"%{'diger'.lower()}%", f"%{'diğer'.lower()}%", f"%{'diger'.lower()}%"])
                    else: # Diğer tüm özel seçenekler için (dusunce sütunu)
                        where_clauses.append(psycopg2.sql.SQL("LOWER(mg.dusunce) LIKE %s"))
                        params.append(f"%{selected_category.lower()}%")
                        
                # Arama metnine göre ikincil filtre (lineEdit_ara)
                if search_text:
                    text_search_clause = psycopg2.sql.SQL("(LOWER(k.adsoyad) LIKE %s OR LOWER(mg.yorumlar) LIKE %s)")
                    text_search_params = [f"%{search_text}%", f"%{search_text}%"]
                    
                    if where_clauses: # Eğer zaten bir kategori filtresi varsa AND ile ekle
                        where_clauses.append(text_search_clause)
                        params.extend(text_search_params)
                    else: # Eğer kategori filtresi yoksa (sadece metin araması)
                        where_clauses.append(text_search_clause)
                        params.extend(text_search_params)


                if not where_clauses: # Hem kategori hem de metin araması yoksa
                    self.display_mentor_gorusmeleri() # Tümünü göster
                    print("MentorPage: Hiçbir filtre seçilmedi veya metin girilmedi. Tüm görüşmeler görüntülendi.")
                    return

                # Tüm WHERE koşullarını birleştir
                combined_where_clause = psycopg2.sql.SQL(" AND ").join(where_clauses)
                
                base_query = psycopg2.sql.SQL("""
                    SELECT 
                        mg.mentorid, 
                        k.adsoyad AS kursiyer_adsoyad,
                        mg.gorusmetarihi, 
                        mg.yorumlar,
                        mg.bilgisahibimi,
                        mg.vitprojesinekatilabilirmi,
                        mg.dusunce,
                        mg.yogunlukdurumu
                    FROM mentortablosu AS mg
                    JOIN kursiyerler AS k ON mg.kursiyerid = k.kursiyerid
                    WHERE {} ORDER BY mg.gorusmetarihi DESC;
                """).format(combined_where_clause)

                print(f"DEBUG: Oluşturulan SQL sorgusu: {base_query.as_string(db.conn.cursor().connection)}") # db.conn.cursor().connection eklendi
                print(f"DEBUG: Sorgu parametreleri: {params}") # DEBUG: Parametreleri yazdır
                
                results = db.fetch_all(base_query, params) 
                print(f"DEBUG: Veritabanından gelen sonuç sayısı: {len(results) if results else 0}") # DEBUG: Sonuç sayısını yazdır

                self.tableWidget.clearContents()
                # Başlıklar güncellendi
                headers_display = ["Mentor ID", "Kursiyer Ad Soyad", "Görüşme Tarihi", "Yorumlar", 
                                   "Bilgi Sahibi Mi?", "VIT Projesine Katılabilir Mi?", "Düşünce", "Yoğunluk Durumu"]
                
                headers_db = ["mentorid", "kursiyer_adsoyad", "gorusmetarihi", "yorumlar",
                              "bilgisahibimi", "vitprojesinekatilabilirmi", "dusunce", "yogunlukdurumu"]

                self.tableWidget.setColumnCount(len(headers_display))
                self.tableWidget.setHorizontalHeaderLabels(headers_display)
                self.tableWidget.setRowCount(0)

                if results:
                    self.tableWidget.setRowCount(len(results))
                    for row_idx, gorusme in enumerate(results):
                        for col_idx, key in enumerate(headers_db):
                            item_data = gorusme.get(key)
                            if isinstance(item_data, date):
                                item_text = item_data.isoformat()
                            else:
                                item_text = str(item_data) if item_data is not None else ""
                            self.tableWidget.setItem(row_idx, col_idx, QTableWidgetItem(item_text))
                else:
                    QMessageBox.information(self, "Sonuç", "Arama kriterlerine uygun mentor görüşmesi bulunamadı.")
                    print("MentorPage: Arama sonucu boş.")

        except psycopg2.Error as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Arama sırasında bir veritabanı hatası oluştu: {e}")
            print(f"MentorPage: ERROR - Arama sırasında veritabanı hatası: {e}")
            import traceback
            traceback.print_exc()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Beklenmeyen bir hata oluştu: {e}")
            print(f"MentorPage: HATA - Beklenmeyen hata (apply_filters): {e}")
            import traceback
            traceback.print_exc()


        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        print("MentorPage: 'apply_filters' tamamlandı.")

    def cikis_yap(self):
        """Uygulamadan güvenli bir şekilde çıkar."""
        print("MentorPage: 'cikis_yap' çağrıldı, uygulama kapatılıyor.")
        QApplication.quit()

# Bu kısım sadece mentor.py dosyasını bağımsız olarak test etmek isterseniz gereklidir.
# Normalde uygulama main.py üzerinden başlatılacaktır.
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Test için geçici bir DatabaseManager nesnesi oluşturuluyor.
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
    
    mentor_page = MentorPage(temp_db_manager)
    
    # Test için basit bir QStackedWidget oluşturup atayalım
    test_stacked_widget = QtWidgets.QStackedWidget()
    test_stacked_widget.addWidget(mentor_page)
    test_stacked_widget.setCurrentWidget(mentor_page)
    mentor_page.set_stacked_widget(test_stacked_widget) 
    
    # Başlangıçta tüm mentor görüşmelerini görüntüle
    mentor_page.display_mentor_gorusmeleri()

    test_stacked_widget.show()
    sys.exit(app.exec())
