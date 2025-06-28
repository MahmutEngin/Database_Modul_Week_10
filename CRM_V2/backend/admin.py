import sys
import os
from PyQt6 import uic, QtWidgets
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QTableWidgetItem, QLineEdit, QApplication, QComboBox, QVBoxLayout, QWidget, QStackedWidget # QStackedWidget buraya taşındı
from PyQt6.QtCore import Qt
import datetime

# Google Calendar API kütüphaneleri
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle

# Veritabanı yönetim modülünü import edin
from database_manager import DatabaseManager
from psycopg2 import sql, Error

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

class AdminPage(QMainWindow):
    """
    Yönetici (Admin) sayfasını yöneten sınıf.
    Kullanıcı ve kursiyer CRUD işlemlerini, arama ve filtrelemeyi sağlar.
    Google Takvim etkinliklerini çekme özelliğini de içerir.
    """
    
    def __init__(self, db_manager):
        """
        AdminPage sınıfının başlatıcısı.
        :param db_manager: DatabaseManager sınıfının bir örneği.
        """
        super().__init__()
        self.db_manager = db_manager
        print("AdminPage __init__ başladı.")

        ui_path = os.path.join(os.path.dirname(__file__), "..", "ui", 'admin_page_python.ui')
        if not os.path.exists(ui_path):
            QMessageBox.critical(self, "Hata", f"UI dosyası bulunamadı: {ui_path}\nUygulama kapatılıyor.")
            sys.exit(-1)

        uic.loadUi(ui_path, self)
        print(f"UI dosyası yüklendi: {ui_path}")

        self.previous_page = None
        self.stacked_widget = None

        self.logged_in_user_id = None 
        self.logged_in_username = None
        self.logged_in_user_yetki = None

        self.tableWidget = self.findChild(QtWidgets.QTableWidget, "tableWidget_show")
        if self.tableWidget is None:
            QMessageBox.critical(self, "UI Hatası", "tableWidget_show bulunamadı. Lütfen Qt Designer'da objectName'ini kontrol edin.")
            sys.exit(-1)

        self.pushButton_mailgonder = self.findChild(QtWidgets.QPushButton, "pushButton_mailgonder")
        if self.pushButton_mailgonder is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_mailgonder bulunamadı.")
            sys.exit(-1)

        self.pushButton_etkinlikkontrolu = self.findChild(QtWidgets.QPushButton, "pushButton_etkinlikkontrolu")
        if self.pushButton_etkinlikkontrolu is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_etkinlikkontrolu bulunamadı.")
            sys.exit(-1)
        
        self.pushButton_tercihler = self.findChild(QtWidgets.QPushButton, "pushButton_tercihler")
        if self.pushButton_tercihler is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_tercihler bulunamadı.")
            sys.exit(-1)

        self.pushButton_exit = self.findChild(QtWidgets.QPushButton, "pushButton_exit")
        if self.pushButton_exit is None:
            QMessageBox.critical(self, "UI Hatası", "pushButton_exit bulunamadı.")
            sys.exit(-1)

        self.pushButton_kullaniciGetir = self.findChild(QtWidgets.QPushButton, "pushButton_kullaniciGetir")
        self.pushButton_kursiyerGetir = self.findChild(QtWidgets.QPushButton, "pushButton_kursiyerGetir")
        self.pushButton_guncelle = self.findChild(QtWidgets.QPushButton, "pushButton_guncelle")
        self.pushButton_ekle = self.findChild(QtWidgets.QPushButton, "pushButton_ekle")
        self.pushButton_sil = self.findChild(QtWidgets.QPushButton, "pushButton_sil")
        self.pushButton_ara = self.findChild(QtWidgets.QPushButton, "pushButton_ara")
        self.lineEdit_kullaniciAdi = self.findChild(QLineEdit, "lineEdit_kullaniciAdi")
        self.lineEdit_sifre = self.findChild(QLineEdit, "lineEdit_sifre")
        self.comboBox_rol = self.findChild(QComboBox, "comboBox_rol")
        self.lineEdit_telefon = self.findChild(QLineEdit, "lineEdit_telefon")
        self.lineEdit_eposta = self.findChild(QLineEdit, "lineEdit_eposta")
        self.lineEdit_adSoyad = self.findChild(QLineEdit, "lineEdit_adSoyad")
        self.lineEdit_arama = self.findChild(QLineEdit, "lineEdit_arama")
        self.comboBox_aramaTuru = self.findChild(QComboBox, "comboBox_aramaTuru")
        
        self.lineEdit_postaKodu = self.findChild(QLineEdit, "lineEdit_postaKodu")
        self.lineEdit_eyalet = self.findChild(QLineEdit, "lineEdit_eyalet")
        
        print("Tüm gerekli UI öğeleri başarıyla bulundu.")

        self.pushButton_mailgonder.clicked.connect(self.send_mail)
        self.pushButton_etkinlikkontrolu.clicked.connect(self.fetch_google_calendar_events) 
        self.pushButton_tercihler.clicked.connect(self._go_to_previous_page_wrapper)
        self.pushButton_exit.clicked.connect(self.cikis_yap)

        if self.pushButton_kullaniciGetir:
            self.pushButton_kullaniciGetir.clicked.connect(self.display_users)
        if self.pushButton_kursiyerGetir:
            self.pushButton_kursiyerGetir.clicked.connect(self.display_kursiyerler)
        if self.pushButton_ekle:
            self.pushButton_ekle.clicked.connect(self.add_entry)
        if self.pushButton_guncelle:
            self.pushButton_guncelle.clicked.connect(self.update_entry)
        if self.pushButton_sil:
            self.pushButton_sil.clicked.connect(self.delete_entry)
        if self.pushButton_ara:
            self.pushButton_ara.clicked.connect(self.search_entry)
        
        self.tableWidget.itemClicked.connect(self.fill_form_from_table)
        
        if self.comboBox_aramaTuru:
            self.comboBox_aramaTuru.addItems(["Kullanıcı Adı", "Yetki", "Kursiyer Adı", "Kursiyer Telefon", "Kursiyer E-posta", "Etkinlik ID", "Etkinlik Özeti"]) # Yeni arama türleri eklendi
        
        if self.comboBox_rol:
            self.comboBox_rol.addItems(["admin", "user", "mentor"])

        self.current_table_type = None 
        
        # Uygulama açıldığında varsayılan olarak kullanıcıları göster (eğer ilgili butonlar varsa)
        if self.pushButton_kullaniciGetir and self.pushButton_kullaniciGetir.parent():
             self.display_users()
        else:
            self.tableWidget.clearContents()
            self.tableWidget.setRowCount(0)
            self.tableWidget.setColumnCount(0)
            QMessageBox.information(self, "Bilgi", "UI'da varsayılan gösterilecek bir tablo tipi belirlenemedi. Lütfen bir işlem seçin.")

        print("AdminPage: Varsayılan olarak kullanıcılar görüntülendi.")

        self.tableWidget.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        print("AdminPage __init__ tamamlandı.")
    
    def set_logged_in_user(self, user_id, username, user_yetki):
        """
        Giriş yapan kullanıcının bilgilerini saklar ve yetkiye göre UI ayarları yapar.
        """
        self.logged_in_user_id = user_id
        self.logged_in_username = username
        self.logged_in_user_yetki = user_yetki
        print(f"AdminPage: Oturum açan kullanıcı bilgileri ayarlandı: ID={user_id}, Kullanıcı Adı={username}, Yetki={user_yetki}")
        
        if user_yetki == "admin":
            print("Admin yetkisi ile giriş yapıldı.")
        elif user_yetki == "user":
            print("Kullanıcı yetkisi ile giriş yapıldı.")
        elif user_yetki == "mentor":
            print("Mentor yetkisi ile giriş yapıldı.")
        else:
            print(f"Bilinmeyen yetki: {user_yetki}")

    def set_previous_page(self, page):
        """Bir önceki sayfanın referansını ayarlar."""
        self.previous_page = page
        print(f"AdminPage: Önceki sayfa referansı ayarlandı: {page.__class__.__name__}")
    
    def set_stacked_widget(self, stacked_widget_ref):
        """MainApp'ten gelen QStackedWidget referansını ayarlar."""
        self.stacked_widget = stacked_widget_ref
        print("AdminPage: Stacked widget referansı ayarlandı.")

    def _go_to_previous_page_wrapper(self):
        """
        'Tercihler' butonuna basıldığında önceki sayfaya dönmek için MainApp'teki
        stacked_widget'ı kullanan bir sarmalayıcı metod.
        """
        print("AdminPage: 'Tercihler' butonu tıklandı. Önceki sayfaya dönülüyor.")
        if self.stacked_widget and self.previous_page:
            self.stacked_widget.setCurrentWidget(self.previous_page)
            print("AdminPage: Önceki sayfa gösterildi.")
        else:
            QMessageBox.warning(self, "Uyarı", "Geri dönülecek bir sayfa veya stacked widget tanımlanmamış.")
            print("AdminPage: Uyarı - Geri dönülecek sayfa veya stacked widget bulunamadı.")


    def clear_form_fields(self):
        """Form alanlarını temizler."""
        if self.lineEdit_kullaniciAdi: self.lineEdit_kullaniciAdi.clear()
        if self.lineEdit_sifre: self.lineEdit_sifre.clear()
        if self.comboBox_rol: self.comboBox_rol.setCurrentIndex(-1) 
        if self.lineEdit_adSoyad: self.lineEdit_adSoyad.clear()
        if self.lineEdit_telefon: self.lineEdit_telefon.clear()
        if self.lineEdit_eposta: self.lineEdit_eposta.clear()
        if self.lineEdit_arama: self.lineEdit_arama.clear()
        # self.lineEdit_postaKodu ve self.lineEdit_eyalet nesnelerinin varlığını kontrol et
        if hasattr(self, 'lineEdit_postaKodu') and self.lineEdit_postaKodu: self.lineEdit_postaKodu.clear()
        if hasattr(self, 'lineEdit_eyalet') and self.lineEdit_eyalet: self.lineEdit_eyalet.clear()
        print("AdminPage: Form alanları temizlendi.")

    def display_users(self):
        """Veritabanından kullanıcıları çeker ve tabloda gösterir."""
        print("AdminPage: 'display_users' başladı.")
        self.current_table_type = "users"
        self.clear_form_fields()

        headers = ["Kullanıcı ID", "Kullanıcı Adı", "Parola", "Yetki"]
        self.tableWidget.setColumnCount(len(headers))
        self.tableWidget.setHorizontalHeaderLabels(headers)
        self.tableWidget.setRowCount(0)

        try:
            with self.db_manager as db:
                query = sql.SQL("SELECT kullaniciid, kullaniciadi, parola, yetki FROM kullanicilar ORDER BY kullaniciid ASC;")
                users = db.fetch_all(query)
                print(f"AdminPage: Çekilen kullanıcı sayısı: {len(users)}")

                if users:
                    self.tableWidget.setRowCount(len(users))
                    for row_idx, user in enumerate(users):
                        self.tableWidget.setItem(row_idx, 0, QTableWidgetItem(str(user.get('kullaniciid', ''))))
                        self.tableWidget.setItem(row_idx, 1, QTableWidgetItem(user.get('kullaniciadi', '')))
                        self.tableWidget.setItem(row_idx, 2, QTableWidgetItem(user.get('parola', '')))
                        self.tableWidget.setItem(row_idx, 3, QTableWidgetItem(user.get('yetki', '')))
                else:
                    QMessageBox.information(self, "Bilgi", "Kullanıcı bulunamadı.")
                    print("AdminPage: Kullanıcı bulunamadı.")
        except Error as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Kullanıcılar çekilirken bir hata oluştu: {e}")
            print(f"AdminPage: HATA - Kullanıcılar çekilirken veritabanı hatası: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Beklenmeyen bir hata oluştu: {e}")
            print(f"AdminPage: HATA - Kullanıcılar çekilirken beklenmeyen hata: {e}")

        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        print("AdminPage: 'display_users' tamamlandı.")

    def display_kursiyerler(self):
        """Veritabanından kursiyerleri çeker ve tabloda gösterir."""
        print("AdminPage: 'display_kursiyerler' başladı.")
        self.current_table_type = "kursiyerler"
        self.clear_form_fields()

        headers = ["Kursiyer ID", "Ad Soyad", "Telefon", "E-posta", "Posta Kodu", "Eyalet"]
        self.tableWidget.setColumnCount(len(headers))
        self.tableWidget.setHorizontalHeaderLabels(headers)
        self.tableWidget.setRowCount(0)

        try:
            with self.db_manager as db:
                query = sql.SQL("SELECT KursiyerID, AdSoyad, TelefonNumarasi, MailAdresi, PostaKodu, YasadiginizEyalet FROM Kursiyerler ORDER BY KursiyerID ASC;")
                kursiyerler = db.fetch_all(query)
                print(f"AdminPage: Çekilen kursiyer sayısı: {len(kursiyerler)}")

                if kursiyerler:
                    self.tableWidget.setRowCount(len(kursiyerler))
                    for row_idx, kursiyer in enumerate(kursiyerler):
                        self.tableWidget.setItem(row_idx, 0, QTableWidgetItem(str(kursiyer.get('kursiyerid', ''))))
                        self.tableWidget.setItem(row_idx, 1, QTableWidgetItem(kursiyer.get('adsoyad', '')))
                        self.tableWidget.setItem(row_idx, 2, QTableWidgetItem(kursiyer.get('telefonnumarasi', '')))
                        self.tableWidget.setItem(row_idx, 3, QTableWidgetItem(kursiyer.get('mailadresi', '')))
                        self.tableWidget.setItem(row_idx, 4, QTableWidgetItem(kursiyer.get('postakodu', '')))
                        self.tableWidget.setItem(row_idx, 5, QTableWidgetItem(kursiyer.get('yasadiginizeyalet', '')))
                else:
                    QMessageBox.information(self, "Bilgi", "Kursiyer bulunamadı.")
                    print("AdminPage: Kursiyer bulunamadı.")
        except Error as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Kursiyerler çekilirken bir hata oluştu: {e}")
            print(f"AdminPage: HATA - Kursiyerler çekilirken veritabanı hatası: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Beklenmeyen bir hata oluştu: {e}")
            print(f"AdminPage: HATA - Beklenmeyen hata: {e}")

        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        print("AdminPage: 'display_kursiyerler' tamamlandı.")

    def fill_form_from_table(self, item):
        """Tablodan bir öğe seçildiğinde form alanlarını doldurur."""
        print(f"AdminPage: Tabloda {item.row()}. satır seçildi.")
        row = item.row()
        
        if self.current_table_type == "users":
            if self.lineEdit_kullaniciAdi and self.lineEdit_sifre and self.comboBox_rol:
                self.lineEdit_kullaniciAdi.setText(self.tableWidget.item(row, 1).text())
                self.lineEdit_sifre.setText(self.tableWidget.item(row, 2).text())
                yetki = self.tableWidget.item(row, 3).text()
                index = self.comboBox_rol.findText(yetki, Qt.MatchFlag.MatchExactly)
                if index != -1:
                    self.comboBox_rol.setCurrentIndex(index)
                
                # Kursiyer ve Etkinlik alanlarını temizle
                if self.lineEdit_adSoyad: self.lineEdit_adSoyad.clear()
                if self.lineEdit_telefon: self.lineEdit_telefon.clear()
                if self.lineEdit_eposta: self.lineEdit_eposta.clear()
                if hasattr(self, 'lineEdit_postaKodu') and self.lineEdit_postaKodu: self.lineEdit_postaKodu.clear()
                if hasattr(self, 'lineEdit_eyalet') and self.lineEdit_eyalet: self.lineEdit_eyalet.clear()
            else:
                QMessageBox.warning(self, "Uyarı", "Kullanıcı form alanları UI'da bulunamadığı için form doldurulamadı.")
                print("AdminPage: HATA - fill_form_from_table (users) için gerekli UI alanları eksik.")

        elif self.current_table_type == "kursiyerler":
            if self.lineEdit_adSoyad and self.lineEdit_telefon and self.lineEdit_eposta:
                self.lineEdit_adSoyad.setText(self.tableWidget.item(row, 1).text())
                self.lineEdit_telefon.setText(self.tableWidget.item(row, 2).text())
                self.lineEdit_eposta.setText(self.tableWidget.item(row, 3).text())
                if self.lineEdit_postaKodu: self.lineEdit_postaKodu.setText(self.tableWidget.item(row, 4).text())
                if self.lineEdit_eyalet: self.lineEdit_eyalet.setText(self.tableWidget.item(row, 5).text())

                # Kullanıcı ve Etkinlik alanlarını temizle
                if self.lineEdit_kullaniciAdi: self.lineEdit_kullaniciAdi.clear()
                if self.lineEdit_sifre: self.lineEdit_sifre.clear()
                if self.comboBox_rol: self.comboBox_rol.setCurrentIndex(-1)
            else:
                QMessageBox.warning(self, "Uyarı", "Kursiyer form alanları UI'da bulunamadığı için form doldurulamadı.")
                print("AdminPage: HATA - fill_form_from_table (kursiyerler) için gerekli UI alanları eksik.")
        
        elif self.current_table_type == "etkinlikler":
            # Etkinlikler için ilgili form alanlarını doldurun (eğer UI'da varsa)
            # Şu an için etkinlikler tablosundan form doldurma işlevselliği yok
            # Bu kısım sadece placeholder olarak duruyor.
            print("AdminPage: Etkinlikler tablosundan form doldurma desteklenmiyor.")
            self.clear_form_fields() # Tüm form alanlarını temizle
        else:
            QMessageBox.warning(self, "Uyarı", "Seçili tablo türüne uygun form alanları UI'da bulunamadığı için form doldurulamadı.")
            print("AdminPage: HATA - fill_form_from_table için tablo tipi uyumsuz veya UI alanları eksik.")
        print("AdminPage: Form alanları dolduruldu.")

    def add_entry(self):
        """Yeni kullanıcı veya kursiyer ekler."""
        print("AdminPage: 'add_entry' başladı.")
        if self.current_table_type == "users":
            if not (self.lineEdit_kullaniciAdi and self.lineEdit_sifre and self.comboBox_rol):
                QMessageBox.critical(self, "Hata", "Kullanıcı ekleme için gerekli form alanları (Kullanıcı Adı, Şifre, Yetki) bulunamadı.")
                print("AdminPage: HATA - Kullanıcı ekleme için gerekli UI alanları eksik.")
                return

            kullanici_adi = self.lineEdit_kullaniciAdi.text().strip()
            parola = self.lineEdit_sifre.text().strip()
            yetki = self.comboBox_rol.currentText()

            if not kullanici_adi or not parola or not yetki:
                QMessageBox.warning(self, "Eksik Bilgi", "Kullanıcı adı, parola ve yetki boş bırakılamaz.")
                print("AdminPage: Kullanıcı ekleme - Eksik bilgi.")
                return

            try:
                with self.db_manager as db:
                    check_query = sql.SQL("SELECT kullaniciadi FROM kullanicilar WHERE kullaniciadi = %s;")
                    existing_user = db.fetch_all(check_query, (kullanici_adi,))
                    if existing_user:
                        QMessageBox.warning(self, "Hata", "Bu kullanıcı adı zaten mevcut.")
                        print("AdminPage: Kullanıcı adı zaten mevcut.")
                        return

                    query = sql.SQL("INSERT INTO kullanicilar (kullaniciadi, parola, yetki) VALUES (%s, %s, %s);")
                    db.execute_query(query, (kullanici_adi, parola, yetki))
                    QMessageBox.information(self, "Başarılı", "Kullanıcı başarıyla eklendi.")
                    print("AdminPage: Kullanıcı başarıyla eklendi.")
                    self.display_users()
                    self.clear_form_fields()
            except Error as e:
                QMessageBox.critical(self, "Veritabanı Hatası", f"Kullanıcı eklenirken bir hata oluştu: {e}")
                print(f"AdminPage: HATA - Kullanıcı eklenirken veritabanı hatası: {e}")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Beklenmeyen bir hata oluştu: {e}")
                print(f"AdminPage: HATA - Kullanıcı eklenirken beklenmeyen hata: {e}")

        elif self.current_table_type == "kursiyerler":
            if not (self.lineEdit_adSoyad and self.lineEdit_telefon and self.lineEdit_eposta):
                QMessageBox.critical(self, "Hata", "Kursiyer ekleme için gerekli form alanları (Ad Soyad, Telefon, E-posta) bulunamadı.")
                print("AdminPage: HATA - Kursiyer ekleme için gerekli UI alanları eksik.")
                return

            ad_soyad = self.lineEdit_adSoyad.text().strip()
            telefon = self.lineEdit_telefon.text().strip()
            eposta = self.lineEdit_eposta.text().strip()
            posta_kodu = self.lineEdit_postaKodu.text().strip() if self.lineEdit_postaKodu else None
            eyalet = self.lineEdit_eyalet.text().strip() if self.lineEdit_eyalet else None

            if not ad_soyad:
                QMessageBox.warning(self, "Eksik Bilgi", "Kursiyer Adı Soyadı boş bırakılamaz.")
                print("AdminPage: Kursiyer ekleme - Eksik bilgi.")
                return

            try:
                with self.db_manager as db:
                    if eposta:
                        check_query = sql.SQL("SELECT mailadresi FROM kursiyerler WHERE mailadresi = %s;")
                        existing_email = db.fetch_all(check_query, (eposta,))
                        if existing_email:
                            QMessageBox.warning(self, "Hata", "Bu e-posta adresi zaten mevcut.")
                            print("AdminPage: E-posta adresi zaten mevcut.")
                            return

                    query = sql.SQL("INSERT INTO kursiyerler (adsoyad, telefonnumarasi, mailadresi, postakodu, yasadiginizeyalet) VALUES (%s, %s, %s, %s, %s);")
                    
                    db.execute_query(query, (ad_soyad, telefon, eposta, posta_kodu, eyalet))
                    QMessageBox.information(self, "Başarılı", "Kursiyer başarıyla eklendi.")
                    print("AdminPage: Kursiyer başarıyla eklendi.")
                    self.display_kursiyerler()
                    self.clear_form_fields()
            except Error as e:
                QMessageBox.critical(self, "Veritabanı Hatası", f"Kursiyer eklenirken bir hata oluştu: {e}")
                print(f"AdminPage: HATA - Kursiyer eklenirken veritabanı hatası: {e}")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Beklenmeyen bir hata oluştu: {e}")
                print(f"AdminPage: HATA - Kursiyer eklenirken beklenmeyen hata: {e}")
        else:
            QMessageBox.warning(self, "Uyarı", "Eklenecek kayıt türü seçili değil veya form alanları eksik.")
            print("AdminPage: HATA - add_entry için tablo tipi belirlenmedi veya UI alanları eksik.")

        print("AdminPage: 'add_entry' tamamlandı.")

    def update_entry(self):
        """Seçili kullanıcı veya kursiyeri günceller."""
        print("AdminPage: 'update_entry' başladı.")
        selected_items = self.tableWidget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Uyarı", "Lütfen güncellenecek bir kayıt seçin.")
            print("AdminPage: Güncelleme için kayıt seçilmedi.")
            return

        row = selected_items[0].row()
        
        try:
            with self.db_manager as db:
                if self.current_table_type == "users":
                    if not (self.lineEdit_kullaniciAdi and self.lineEdit_sifre and self.comboBox_rol):
                        QMessageBox.critical(self, "Hata", "Kullanıcı güncelleme için gerekli form alanları (Kullanıcı Adı, Şifre, Yetki) bulunamadı.")
                        print("AdminPage: HATA - Kullanıcı güncelleme için gerekli UI alanları eksik.")
                        return

                    kullanici_id = int(self.tableWidget.item(row, 0).text())
                    kullanici_adi = self.lineEdit_kullaniciAdi.text().strip()
                    parola = self.lineEdit_sifre.text().strip()
                    yetki = self.comboBox_rol.currentText()

                    if not kullanici_adi or not parola or not yetki:
                        QMessageBox.warning(self, "Eksik Bilgi", "Kullanıcı adı, parola ve yetki boş bırakılamaz.")
                        print("AdminPage: Kullanıcı güncelleme - Eksik bilgi.")
                        return

                    original_kullanici_adi = self.tableWidget.item(row, 1).text()
                    if kullanici_adi != original_kullanici_adi:
                        check_query = sql.SQL("SELECT kullaniciadi FROM kullanicilar WHERE kullaniciadi = %s AND kullaniciid != %s;")
                        existing_user = db.fetch_all(check_query, (kullanici_adi, kullanici_id))
                        if existing_user:
                            QMessageBox.warning(self, "Hata", "Bu kullanıcı adı zaten başka bir kullanıcı tarafından kullanılıyor.")
                            print("AdminPage: Kullanıcı adı zaten mevcut (güncelleme).")
                            return

                    query = sql.SQL("UPDATE kullanicilar SET kullaniciadi = %s, parola = %s, yetki = %s WHERE kullaniciid = %s;")
                    db.execute_query(query, (kullanici_adi, parola, yetki, kullanici_id))
                    QMessageBox.information(self, "Başarılı", "Kullanıcı başarıyla güncellendi.")
                    print("AdminPage: Kullanıcı başarıyla güncellendi.")
                    self.display_users()
                    self.clear_form_fields()

                elif self.current_table_type == "kursiyerler":
                    if not (self.lineEdit_adSoyad and self.lineEdit_telefon and self.lineEdit_eposta):
                        QMessageBox.critical(self, "Hata", "Kursiyer güncelleme için gerekli form alanları (Ad Soyad, Telefon, E-posta) bulunamadı.")
                        print("AdminPage: HATA - Kursiyer güncelleme için gerekli UI alanları eksik.")
                        return

                    kursiyer_id = int(self.tableWidget.item(row, 0).text())
                    ad_soyad = self.lineEdit_adSoyad.text().strip()
                    telefon = self.lineEdit_telefon.text().strip()
                    eposta = self.lineEdit_eposta.text().strip()
                    posta_kodu = self.lineEdit_postaKodu.text().strip() if self.lineEdit_postaKodu else None
                    eyalet = self.lineEdit_eyalet.text().strip() if self.lineEdit_eyalet else None


                    if not ad_soyad:
                        QMessageBox.warning(self, "Eksik Bilgi", "Kursiyer Adı Soyadı boş bırakılamaz.")
                        print("AdminPage: Kursiyer güncelleme - Eksik bilgi.")
                        return

                    original_eposta = self.tableWidget.item(row, 3).text()
                    if eposta and eposta != original_eposta:
                        check_query = sql.SQL("SELECT mailadresi FROM kursiyerler WHERE mailadresi = %s AND kursiyerid != %s;")
                        existing_email = db.fetch_all(check_query, (eposta, kursiyer_id))
                        if existing_email:
                            QMessageBox.warning(self, "Hata", "Bu e-posta adresi zaten başka bir kursiyer tarafından kullanılıyor.")
                            print("AdminPage: E-posta zaten mevcut (güncelleme).")
                            return

                    query = sql.SQL("UPDATE kursiyerler SET adsoyad = %s, telefonnumarasi = %s, mailadresi = %s, postakodu = %s, yasadiginizeyalet = %s WHERE kursiyerid = %s;")
                    
                    db.execute_query(query, (ad_soyad, telefon, eposta, posta_kodu, eyalet, kursiyer_id))
                    QMessageBox.information(self, "Başarılı", "Kursiyer başarıyla güncellendi.")
                    print("AdminPage: Kursiyer başarıyla güncellendi.")
                    self.display_kursiyerler()
                    self.clear_form_fields()
        except Error as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Güncelleme sırasında bir hata oluştu: {e}")
            print(f"AdminPage: HATA - Güncelleme sırasında veritabanı hatası: {e}")
        except ValueError:
            QMessageBox.warning(self, "Hata", "ID alanı geçerli bir sayı olmalıdır.")
            print("AdminPage: Geçersiz ID formatı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Beklenmeyen bir hata oluştu: {e}")
            print(f"AdminPage: HATA - Beklenmeyen hata: {e}")
        print("AdminPage: 'update_entry' tamamlandı.")

    def delete_entry(self):
        """Seçili kullanıcı veya kursiyeri siler."""
        print("AdminPage: 'delete_entry' başladı.")
        selected_items = self.tableWidget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Uyarı", "Lütfen silinecek bir kayıt seçin.")
            print("AdminPage: Silme için kayıt seçilmedi.")
            return

        reply = QMessageBox.question(self, 'Silme Onayı', 'Seçili kaydı silmek istediğinizden emin misiniz?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            row = selected_items[0].row()
            try:
                with self.db_manager as db:
                    if self.current_table_type == "users":
                        kullanici_id = int(self.tableWidget.item(row, 0).text())
                        query = sql.SQL("DELETE FROM kullanicilar WHERE kullaniciid = %s;")
                        db.execute_query(query, (kullanici_id,))
                        QMessageBox.information(self, "Başarılı", "Kullanıcı başarıyla silindi.")
                        print("AdminPage: Kullanıcı başarıyla silindi.")
                        self.display_users()
                    elif self.current_table_type == "kursiyerler":
                        kursiyer_id = int(self.tableWidget.item(row, 0).text())
                        query = sql.SQL("DELETE FROM kursiyerler WHERE kursiyerid = %s;")
                        db.execute_query(query, (kursiyer_id,))
                        QMessageBox.information(self, "Başarılı", "Kursiyer başarıyla silindi.")
                        print("AdminPage: Kursiyer başarıyla silindi.")
                        self.display_kursiyerler()
                self.clear_form_fields()
            except Error as e:
                QMessageBox.critical(self, "Veritabanı Hatası", f"Silme sırasında bir hata oluştu: {e}\n"
                                     "Bu kayıt başka tablolarda referans olarak kullanılıyor olabilir (Foreign Key kısıtlaması).")
                print(f"AdminPage: HATA - Silme sırasında veritabanı hatası: {e}")
            except ValueError:
                QMessageBox.warning(self, "Hata", "Silinecek kaydın ID'si geçerli bir sayı olmalıdır.")
                print("AdminPage: Geçersiz ID formatı (silme).")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Beklenmeyen bir hata oluştu: {e}")
                print(f"AdminPage: HATA - Beklenmeyen hata: {e}")
        else:
            print("AdminPage: Silme işlemi iptal edildi.")
        print("AdminPage: 'delete_entry' tamamlandı.")

    def search_entry(self):
        """Arama kutusundaki metne ve seçili arama türüne göre kayıtları arar."""
        print("AdminPage: 'search_entry' başladı.")
        
        if not (self.lineEdit_arama and self.comboBox_aramaTuru):
            QMessageBox.critical(self, "Hata", "Arama alanları (Arama kutusu veya Arama Türü) tanımlanmamış. Arama yapılamaz.")
            print("AdminPage: HATA - Arama için gerekli UI alanları eksik.")
            return

        search_text = self.lineEdit_arama.text().strip().lower()
        search_type = self.comboBox_aramaTuru.currentText()

        if not search_text:
            QMessageBox.information(self, "Bilgi", "Lütfen arama metni giriniz.")
            if self.current_table_type == "users":
                self.display_users()
            elif self.current_table_type == "kursiyerler":
                self.display_kursiyerler()
            elif self.current_table_type == "etkinlikler": # Etkinlikler için de eklendi
                self.display_etkinlikler()
            print("AdminPage: Arama metni boş, mevcut tablo yenilendi.")
            return

        try:
            with self.db_manager as db:
                results = []
                headers = []

                if search_type == "Kullanıcı Adı":
                    self.current_table_type = "users"
                    headers = ["Kullanıcı ID", "Kullanıcı Adı", "Parola", "Yetki"]
                    query = sql.SQL("SELECT kullaniciid, kullaniciadi, parola, yetki FROM kullanicilar WHERE LOWER(kullaniciadi) LIKE %s ORDER BY kullaniciid ASC;")
                    results = db.fetch_all(query, (f"%{search_text.lower()}%",))
                elif search_type == "Yetki":
                    self.current_table_type = "users"
                    headers = ["Kullanıcı ID", "Kullanıcı Adı", "Parola", "Yetki"]
                    query = sql.SQL("SELECT kullaniciid, kullaniciadi, parola, yetki FROM kullanicilar WHERE LOWER(yetki) LIKE %s ORDER BY kullaniciid ASC;")
                    results = db.fetch_all(query, (f"%{search_text.lower()}%",))
                elif search_type == "Kursiyer Adı":
                    self.current_table_type = "kursiyerler"
                    headers = ["Kursiyer ID", "Ad Soyad", "Telefon", "E-posta", "Posta Kodu", "Eyalet"]
                    query = sql.SQL("SELECT KursiyerID, AdSoyad, TelefonNumarasi, MailAdresi, PostaKodu, YasadiginizEyalet FROM Kursiyerler WHERE LOWER(AdSoyad) LIKE %s ORDER BY KursiyerID ASC;")
                    results = db.fetch_all(query, (f"%{search_text.lower()}%",))
                elif search_type == "Kursiyer Telefon":
                    self.current_table_type = "kursiyerler"
                    headers = ["Kursiyer ID", "Ad Soyad", "Telefon", "E-posta", "Posta Kodu", "Eyalet"]
                    query = sql.SQL("SELECT KursiyerID, AdSoyad, TelefonNumarasi, MailAdresi, PostaKodu, YasadiginizEyalet FROM Kursiyerler WHERE LOWER(TelefonNumarasi) LIKE %s ORDER BY KursiyerID ASC;")
                    results = db.fetch_all(query, (f"%{search_text.lower()}%",))
                elif search_type == "Kursiyer E-posta":
                    self.current_table_type = "kursiyerler"
                    headers = ["Kursiyer ID", "Ad Soyad", "Telefon", "E-posta", "Posta Kodu", "Eyalet"]
                    query = sql.SQL("SELECT KursiyerID, AdSoyad, TelefonNumarasi, MailAdresi, PostaKodu, YasadiginizEyalet FROM Kursiyerler WHERE LOWER(MailAdresi) LIKE %s ORDER BY KursiyerID ASC;")
                    results = db.fetch_all(query, (f"%{search_text.lower()}%",))
                # Yeni: Etkinlikler için arama türleri
                elif search_type == "Etkinlik ID": # Yeni arama türü eklenebilir
                    self.current_table_type = "etkinlikler"
                    headers = ["Etkinlik ID", "Başlangıç Zamanı", "Katılımcı E-postaları", "Düzenleyici E-posta", "Özet"]
                    query = sql.SQL("SELECT event_id, start_datetime, attendee_emails, organizer_email, summary FROM etkinliklertablosu WHERE LOWER(event_id) LIKE %s ORDER BY start_datetime DESC;")
                    results = db.fetch_all(query, (f"%{search_text.lower()}%",))
                elif search_type == "Etkinlik Özeti": # Yeni arama türü eklenebilir
                    self.current_table_type = "etkinlikler"
                    headers = ["Etkinlik ID", "Başlangıç Zamanı", "Katılımcı E-postaları", "Düzenleyici E-posta", "Özet"]
                    query = sql.SQL("SELECT event_id, start_datetime, attendee_emails, organizer_email, summary FROM etkinliklertablosu WHERE LOWER(summary) LIKE %s ORDER BY start_datetime DESC;")
                    results = db.fetch_all(query, (f"%{search_text.lower()}%",))
                else:
                    QMessageBox.warning(self, "Uyarı", "Geçersiz arama türü seçimi.")
                    print("AdminPage: Geçersiz arama türü.")
                    return

                self.tableWidget.clear()
                self.tableWidget.setColumnCount(len(headers))
                self.tableWidget.setHorizontalHeaderLabels(headers)
                self.tableWidget.setRowCount(0)

                if results:
                    self.tableWidget.setRowCount(len(results))
                    for row_idx, data_dict in enumerate(results):
                        if self.current_table_type == "users":
                            self.tableWidget.setItem(row_idx, 0, QTableWidgetItem(str(data_dict.get('kullaniciid', ''))))
                            self.tableWidget.setItem(row_idx, 1, QTableWidgetItem(data_dict.get('kullaniciadi', '')))
                            self.tableWidget.setItem(row_idx, 2, QTableWidgetItem(data_dict.get('parola', '')))
                            self.tableWidget.setItem(row_idx, 3, QTableWidgetItem(data_dict.get('yetki', '')))
                        elif self.current_table_type == "kursiyerler":
                            self.tableWidget.setItem(row_idx, 0, QTableWidgetItem(str(data_dict.get('kursiyerid', ''))))
                            self.tableWidget.setItem(row_idx, 1, QTableWidgetItem(data_dict.get('adsoyad', '')))
                            self.tableWidget.setItem(row_idx, 2, QTableWidgetItem(data_dict.get('telefonnumarasi', '')))
                            self.tableWidget.setItem(row_idx, 3, QTableWidgetItem(data_dict.get('mailadresi', '')))
                            self.tableWidget.setItem(row_idx, 4, QTableWidgetItem(data_dict.get('postakodu', '')))
                            self.tableWidget.setItem(row_idx, 5, QTableWidgetItem(data_dict.get('yasadiginizeyalet', '')))
                        elif self.current_table_type == "etkinlikler": # Etkinlik sonuçlarını tabloya ekle
                            self.tableWidget.setItem(row_idx, 0, QTableWidgetItem(str(data_dict.get('event_id', ''))))
                            self.tableWidget.setItem(row_idx, 1, QTableWidgetItem(str(data_dict.get('start_datetime', ''))))
                            self.tableWidget.setItem(row_idx, 2, QTableWidgetItem(data_dict.get('attendee_emails', '')))
                            self.tableWidget.setItem(row_idx, 3, QTableWidgetItem(data_dict.get('organizer_email', '')))
                            self.tableWidget.setItem(row_idx, 4, QTableWidgetItem(data_dict.get('summary', '')))
                else:
                    QMessageBox.information(self, "Sonuç", "Arama kriterlerine uygun kayıt bulunamadı.")
                    print("AdminPage: Arama sonucu boş.")

        except Error as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Arama sırasında bir veritabanı hatası oluştu: {e}")
            print(f"AdminPage: HATA - Arama sırasında veritabanı hatası: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Beklenmeyen bir hata oluştu: {e}")
            print(f"AdminPage: HATA - Arama sırasında beklenmeyen hata: {e}")

        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        print("AdminPage: 'search_entry' tamamlandı.")
    
    # --- Ek Metodlar ---
    def send_mail(self):
        """Seçili Google Takvim etkinliğinin katılımcılarına mail gönderme işlevini simüle eder."""
        print("AdminPage: 'send_mail' başladı.")
        selected_items = self.tableWidget.selectedItems()

        if not selected_items:
            QMessageBox.warning(self, "Uyarı", "Lütfen mail göndermek için bir etkinlik seçin.")
            print("AdminPage: Mail göndermek için etkinlik seçilmedi.")
            return

        if self.current_table_type != "etkinlikler":
            QMessageBox.warning(self, "Uyarı", "Mail gönderme işlemi sadece 'Etkinlikler' tablosunda yapılabilir.")
            print(f"AdminPage: Yanlış tablo türü seçili: {self.current_table_type}. 'etkinlikler' bekleniyordu.")
            return

        row = selected_items[0].row()
        try:
            # Etkinlik ID, Başlangıç Zamanı, Katılımcı E-postaları, Düzenleyici E-posta, Özet
            # Kolon indeksleri: 0       , 1              , 2                    , 3                 , 4
            summary = self.tableWidget.item(row, 4).text()
            attendee_emails_str = self.tableWidget.item(row, 2).text()

            if not attendee_emails_str:
                QMessageBox.information(self, "Bilgi", "Seçilen etkinliğin katılımcı e-postası bulunamadı.")
                print("AdminPage: Seçilen etkinlikte katılımcı e-postası yok.")
                return

            message = f"Seçilen etkinliğin katılımcılarına e-posta gönderiliyor:\n\n" \
                      f"Gönderilecek Adres(ler): {attendee_emails_str}\n" \
                      f"Konu: '{summary}' konulu etkinlik hakkında bilgilendirme\n\n" \
                      f"Bu, bir simülasyon mesajıdır ve gerçek bir mail gönderimi yapılmamıştır."
            
            QMessageBox.information(self, "Mail Gönderimi Simülasyonu", message)
            print(f"AdminPage: Mail gönderme simülasyonu başarılı. Kime: {attendee_emails_str}, Konu: {summary}")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Mail gönderme sırasında bir hata oluştu: {e}")
            print(f"AdminPage: HATA - Mail gönderme sırasında beklenmeyen hata: {e}")
        
        print("AdminPage: 'send_mail' tamamlandı.")

    def check_activity(self):
        """Etkinlik kontrolü işlevini başlatır."""
        # Bu metod artık Google Takvim'den etkinlikleri çeken fetch_google_calendar_events() tarafından değiştirildi.
        # Bu metodun çağrıldığı yerler fetch_google_calendar_events() ile değiştirilmelidir.
        QMessageBox.information(self, "Bilgi", "Etkinlik kontrolü özelliği artık Google Takvim senkronizasyonu ile sağlanmaktadır. Lütfen 'Etkinlik Kontrolü' butonunu kullanın.")
        print("AdminPage: 'check_activity' çağrıldı (eski metod).")


    def fetch_google_calendar_events(self):
        """
        Google Takvim'den etkinlikleri çeker ve veritabanına kaydeder.
        """
        print("AdminPage: 'fetch_google_calendar_events' başladı.")
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    QMessageBox.critical(self, "Kimlik Doğrulama Hatası", f"Google kimlik bilgileri yenilenirken hata oluştu: {e}\nLütfen yeniden yetkilendirin.")
                    print(f"AdminPage: HATA - Google kimlik bilgileri yenilenirken hata: {e}")
                    creds = None
            if not creds or not creds.valid:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                    with open('token.pickle', 'wb') as token:
                        pickle.dump(creds, token)
                except Exception as e:
                    QMessageBox.critical(self, "Kimlik Doğrulama Hatası", f"Google kimlik doğrulama akışı sırasında hata oluştu: {e}\n"
                                         "Lütfen 'credentials.json' dosyasının doğru olduğundan ve internet bağlantınızın olduğundan emin olun.")
                    print(f"AdminPage: HATA - Google kimlik doğrulama akışı hatası: {e}")
                    return

        if not creds:
            QMessageBox.critical(self, "Kimlik Doğrulama Hatası", "Google kimlik bilgileri yüklenemedi veya oluşturulamadı.")
            print("AdminPage: HATA - Kimlik bilgileri yok.")
            return

        try:
            service = build('calendar', 'v3', credentials=creds)

            now = datetime.datetime.utcnow().isoformat() + 'Z'
            time_min = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).isoformat() + 'Z'
            time_max = (datetime.datetime.utcnow() + datetime.timedelta(days=30)).isoformat() + 'Z'

            events_result = service.events().list(calendarId='primary', timeMin=time_min,
                                                  timeMax=time_max, singleEvents=True,
                                                  orderBy='startTime').execute()
            events = events_result.get('items', [])

            if not events:
                QMessageBox.information(self, "Bilgi", "Google Takvim'de etkinlik bulunamadı.")
                print("AdminPage: Google Takvim'de etkinlik bulunamadı.")
                return

            inserted_count = 0
            updated_count = 0
            with self.db_manager as db:
                for event in events:
                    event_id = event.get('id')
                    summary = event.get('summary', 'Etkinlik Başlığı Yok')
                    
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    
                    attendee_emails = []
                    if 'attendees' in event:
                        for attendee in event['attendees']:
                            if 'email' in attendee:
                                attendee_emails.append(attendee['email'])
                    attendee_emails_str = ', '.join(attendee_emails)

                    organizer_email = event['organizer'].get('email', '') if 'organizer' in event else ''

                    check_query = sql.SQL("SELECT event_id FROM etkinliklertablosu WHERE event_id = %s;")
                    existing_event = db.fetch_one(check_query, (event_id,))

                    if existing_event:
                        update_query = sql.SQL("""
                            UPDATE etkinliklertablosu 
                            SET start_datetime = %s, attendee_emails = %s, organizer_email = %s, summary = %s
                            WHERE event_id = %s;
                        """)
                        db.execute_query(update_query, (start, attendee_emails_str, organizer_email, summary, event_id))
                        updated_count += 1
                        print(f"AdminPage: Etkinlik güncellendi: {event_id} - {summary}")
                    else:
                        insert_query = sql.SQL("""
                            INSERT INTO etkinliklertablosu (event_id, start_datetime, attendee_emails, organizer_email, summary)
                            VALUES (%s, %s, %s, %s, %s);
                        """)
                        db.execute_query(insert_query, (event_id, start, attendee_emails_str, organizer_email, summary))
                        inserted_count += 1
                        print(f"AdminPage: Etkinlik eklendi: {event_id} - {summary}")

            QMessageBox.information(self, "Başarılı", 
                                    f"Google Takvim'den {inserted_count} yeni etkinlik eklendi, {updated_count} etkinlik güncellendi.")
            print(f"AdminPage: Google Takvim senkronizasyonu tamamlandı. Eklendi: {inserted_count}, Güncellendi: {updated_count}")

            self.display_etkinlikler() 
            
        except HttpError as error:
            QMessageBox.critical(self, "Google API Hatası", f"Google Takvim API'sinden etkinlikler çekilirken hata oluştu: {error}")
            print(f"AdminPage: HATA - Google API hatası: {error}")
        except Error as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Etkinlikler veritabanına kaydedilirken hata oluştu: {e}")
            print(f"AdminPage: HATA - Veritabanı hatası: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Beklenmeyen bir hata oluştu: {e}")
            print(f"AdminPage: HATA - Beklenmeyen hata: {e}")

        print("AdminPage: 'fetch_google_calendar_events' tamamlandı.")

    def display_etkinlikler(self):
        """Veritabanındaki etkinlikleri çeker ve tabloda gösterir."""
        print("AdminPage: 'display_etkinlikler' başladı.")
        self.current_table_type = "etkinlikler"
        self.clear_form_fields()

        headers = ["Etkinlik ID", "Başlangıç Zamanı", "Katılımcı E-postaları", "Düzenleyici E-posta", "Özet"]
        self.tableWidget.setColumnCount(len(headers))
        self.tableWidget.setHorizontalHeaderLabels(headers)
        self.tableWidget.setRowCount(0)

        try:
            with self.db_manager as db:
                query = sql.SQL("SELECT event_id, start_datetime, attendee_emails, organizer_email, summary FROM etkinliklertablosu ORDER BY start_datetime DESC;")
                events = db.fetch_all(query)
                print(f"AdminPage: Çekilen etkinlik sayısı: {len(events)}")

                if events:
                    self.tableWidget.setRowCount(len(events))
                    for row_idx, event in enumerate(events):
                        self.tableWidget.setItem(row_idx, 0, QTableWidgetItem(str(event.get('event_id', ''))))
                        self.tableWidget.setItem(row_idx, 1, QTableWidgetItem(str(event.get('start_datetime', ''))))
                        self.tableWidget.setItem(row_idx, 2, QTableWidgetItem(event.get('attendee_emails', '')))
                        self.tableWidget.setItem(row_idx, 3, QTableWidgetItem(event.get('organizer_email', '')))
                        self.tableWidget.setItem(row_idx, 4, QTableWidgetItem(event.get('summary', '')))
                else:
                    QMessageBox.information(self, "Bilgi", "Etkinlik bulunamadı.")
                    print("AdminPage: Etkinlik bulunamadı.")
        except Error as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Etkinlikler çekilirken bir hata oluştu: {e}")
            print(f"AdminPage: HATA - Etkinlikler çekilirken veritabanı hatası: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Beklenmeyen bir hata oluştu: {e}")
            print(f"AdminPage: HATA - Beklenmeyen hata: {e}")

        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        print("AdminPage: 'display_etkinlikler' tamamlandı.")

    def cikis_yap(self):
        """Uygulamadan güvenli bir şekilde çıkar."""
        print("AdminPage: 'cikis_yap' çağrıldı, uygulama kapatılıyor.")
        QApplication.quit()

# Bu kısım sadece admin.py dosyasını bağımsız olarak test etmek isterseniz gereklidir.
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
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
    
    admin_page = AdminPage(temp_db_manager)
    
    test_stacked_widget = QStackedWidget()
    test_stacked_widget.addWidget(admin_page)
    test_stacked_widget.setCurrentWidget(admin_page)
    admin_page.set_stacked_widget(test_stacked_widget)

    class DummyPreviousPage(QMainWindow):
        def __init__(self, name="Dummy Previous Page"):
            super().__init__()
            self.setWindowTitle(name)
            layout = QVBoxLayout()
            layout.addWidget(QtWidgets.QLabel(f"{name} Content"))
            container = QWidget()
            container.setLayout(layout)
            self.setCentralWidget(container)
    
    dummy_prev_page = DummyPreviousPage("Tercihler Admin Sayfası (Dummy)")
    admin_page.set_previous_page(dummy_prev_page)
    test_stacked_widget.addWidget(dummy_prev_page)

    test_stacked_widget.show()
    sys.exit(app.exec())
