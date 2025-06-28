import os
import pandas as pd
from psycopg2 import Error
from contextlib import contextmanager
from datetime import datetime # datetime modülünü ekledik
import re # re modülünü de ekledik
import psycopg2 # Bağlantı için psycopg2'yi burada da içe aktarıyoruz

# Database config (database_manager'dan alınan DB_CONFIG'u kullanıyoruz)
DB_CONFIG = {
    "host": "127.0.0.1",
    "database": "dbkursiyer",
    "user": "postgres",
    "password": "Mahmut",
    "port": "5432"
}

@contextmanager
def get_db_cursor():
    """Veritabanı bağlantısı ve imleç için context manager.
    'with' ifadesiyle kullanıldığında bağlantıyı otomatik olarak açar ve kapatır.
    """
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        yield cursor
        conn.commit() # Başarılı işlemlerden sonra commit et
    except Error as e:
        if conn:
            conn.rollback() # Hata durumunda rollback et
        print(f"DB Hatası (psycopg2 Error): {e}")
        # Hatanın daha detaylı incelenmesi için exception'ı yeniden fırlatabiliriz
        # raise e
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"DB Hatası (Genel Exception): {e}")
        # raise e
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Data klasörü ve en son VIT klasörü
# Bu path'in import_data_from_excel.py'nin çalıştığı dizine göre ayarlandığından emin olun.
# Örn: C:\Users\Mahmut\Desktop\PYTHON\Werhere IT\CRM_V2\CRM_V2\backend
# Data klasörü: C:\Users\Mahmut\Desktop\PYTHON\Werhere IT\CRM_V2\CRM_V2\data
data_base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

def find_latest_vit_folder(base_path):
    """
    Belirtilen temel yolda (base_path) 'VIT' ile başlayan ve bir sayı içeren
    (örn: VIT7, vit10) en son klasörü bulur.
    En yüksek sayıya sahip klasör tercih edilir.
    """
    vit_folders = []
    if not os.path.isdir(base_path):
        print(f"UYARI: '{base_path}' dizini bulunamadı.")
        return None

    for item in os.listdir(base_path):
        item_path = os.path.join(base_path, item)
        if os.path.isdir(item_path) and item.lower().startswith('vit'):
            match = re.search(r'VIT(\d+)', item, re.IGNORECASE)
            if match:
                try:
                    vit_num = int(match.group(1))
                    vit_folders.append((vit_num, item_path))
                except ValueError:
                    # Sayıya çevrilemezse yoksay
                    continue
    
    if not vit_folders:
        return None
    
    # En yüksek VIT numarasına göre sırala ve en yenisini döndür
    vit_folders.sort(key=lambda x: x[0], reverse=True)
    return vit_folders[0][1]

latest_vit_path = find_latest_vit_folder(data_base_path)
print(f"Bilgi: Bulunan en son VIT klasörü: {latest_vit_path if latest_vit_path else 'Bulunamadı'}")

def insert_or_update(table_name_db, data_dict, unique_columns_db=None):
    """
    Veritabanına veri ekler veya günceller (UPSERT).
    unique_columns_db belirtilmezse sadece INSERT yapar.
    :param table_name_db: Hedef tablo adı (string, DB'deki haliyle, küçük harf).
    :param data_dict: Sütun adları (DB'deki haliyle, küçük harf) ve değerlerini içeren sözlük.
    :param unique_columns_db: Çakışma kontrolü için kullanılan benzersiz sütun adlarının listesi (DB'deki haliyle, küçük harf).
                            Tek sütun için string, birden fazla sütun için liste.
    """
    with get_db_cursor() as cursor:
        columns_db = list(data_dict.keys()) # Sözlük anahtarlarını liste olarak al
        values = [data_dict[col] for col in columns_db]

        # Sütun adlarını ve yer tutucuları SQL için hazırla
        columns_sql_str = ", ".join(columns_db) # Sütunları tırnak içine almadan kullanıyoruz (PostgreSQL otomatik küçük harf)
        placeholders = ", ".join(["%s"] * len(values))

        sql_query = ""
        if unique_columns_db:
            # unique_columns_db string veya liste olabilir
            if isinstance(unique_columns_db, str):
                unique_cols_for_conflict_str = unique_columns_db
                unique_cols_list = [unique_columns_db]
            elif isinstance(unique_columns_db, list):
                unique_cols_for_conflict_str = ", ".join(unique_columns_db)
                unique_cols_list = unique_columns_db
            else:
                raise ValueError("unique_columns_db string veya liste olmalıdır.")

            # unique_columns_db'de olmayan sütunları güncelleme için seç
            update_cols_db = [col for col in columns_db if col not in unique_cols_list]
            
            # Güncellenecek sütunlar varsa DO UPDATE SET kullan, yoksa DO NOTHING
            if not update_cols_db:
                sql_query = f"""
                INSERT INTO {table_name_db} ({columns_sql_str}) VALUES ({placeholders})
                ON CONFLICT ({unique_cols_for_conflict_str}) DO NOTHING;
                """
            else:
                update_set_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in update_cols_db])
                sql_query = f"""
                INSERT INTO {table_name_db} ({columns_sql_str}) VALUES ({placeholders})
                ON CONFLICT ({unique_cols_for_conflict_str}) DO UPDATE SET {update_set_clause};
                """
        else: # unique_columns_db belirtilmezse sadece INSERT
            sql_query = f"INSERT INTO {table_name_db} ({columns_sql_str}) VALUES ({placeholders});"
        
        cursor.execute(sql_query, values)

def get_kursiyer_id_by_email(email):
    """Veritabanından e-posta adresine göre kursiyerid'yi bulur."""
    if not email or pd.isna(email) or str(email).strip() == '':
        return None
    email_clean = str(email).strip().lower() # E-postayı küçük harfe çevir
    with get_db_cursor() as cursor:
        if cursor: # Cursor'ın None olmadığından emin ol
            cursor.execute("SELECT kursiyerid FROM kursiyerler WHERE mailadresi = %s", (email_clean,))
            result = cursor.fetchone()
            return result[0] if result else None
    return None

def get_kursiyer_id_by_name(ad_soyad):
    """Veritabanından adsoyad'a göre kursiyerid'yi bulur.
    Bu yöntem e-posta kadar güvenilir olmayabilir, çünkü isimler benzersiz olmayabilir.
    """
    if not ad_soyad or pd.isna(ad_soyad) or str(ad_soyad).strip() == '':
        return None
    ad_soyad_clean = str(ad_soyad).strip() # Ad soyadı doğrudan kullan
    with get_db_cursor() as cursor:
        if cursor: # Cursor'ın None olmadığından emin ol
            cursor.execute("SELECT kursiyerid FROM kursiyerler WHERE adsoyad = %s", (ad_soyad_clean,))
            result = cursor.fetchone()
            return result[0] if result else None
    return None

def get_first_kullanici_id():
    """Kullanicilar tablosundaki ilk KullaniciID'yi çeker."""
    with get_db_cursor() as cursor:
        if cursor:
            try:
                cursor.execute("SELECT kullaniciid FROM kullanicilar ORDER BY kullaniciid ASC LIMIT 1;")
                result = cursor.fetchone()
                return result[0] if result else None
            except Exception as e:
                print(f"UYARI: İlk kullanıcı ID çekilirken hata oluştu: {e}")
                return None
    return None

def convert_excel_date_to_db_date(value):
    """Excel'den gelen tarih değerlerini PostgreSQL DATE objesine çevirir.
    Boş, NaT veya geçersiz tarihleri None olarak döndürür.
    """
    if pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date() # Eğer zaten datetime objesiyse sadece tarih kısmını al
    try:
        # pd.to_datetime daha esnek tarih parsing'i sağlar
        # errors='coerce' geçersiz tarihleri NaT (Not a Time) olarak döndürür
        dt_obj = pd.to_datetime(value, errors='coerce')
        if pd.isnat(dt_obj): # Eğer dönüşüm başarısız olursa
            return None
        return dt_obj.date()
    except (ValueError, TypeError) as e:
        print(f"UYARI: Tarih dönüştürme hatası '{value}': {e}")
        return None

def process_kursiyerler_from_basvurular():
    """Basvurular.xlsx dosyasından kursiyerler tablosuna temel ad/mail/telefon/posta kodu/eyalet bilgilerini aktarır."""
    if not latest_vit_path:
        print("HATA: En son VIT klasörü bulunamadı, 'kursiyerler' tablosu işlenemiyor.")
        return 0
    
    file_path = os.path.join(latest_vit_path, "Basvurular.xlsx") 
    
    if not os.path.isfile(file_path):
        print(f"HATA: 'Basvurular.xlsx' dosyası bulunamadı: {file_path}")
        return 0
    print("\nADIM: 'Basvurular.xlsx' dosyasından 'kursiyerler' tablosuna veri aktarılıyor...")
    
    df = pd.read_excel(file_path) 

    inserted_or_updated = 0
    for row_idx, row in df.iterrows():
        mail_adresi_excel = row.get("Mail adresiniz", None)
        ad_soyad_excel = row.get("Adınız Soyadınız", None)
        
        telefon_excel = row.get("Telefon Numaranız", None)
        posta_kodu_excel = row.get("Posta Kodunuz", None)
        eyalet_excel = row.get("Yaşadığınız Eyalet", None)

        if not mail_adresi_excel or pd.isna(mail_adresi_excel) or str(mail_adresi_excel).strip() == '':
            print(f"UYARI: Satır {row_idx + 2}: 'kursiyerler' tablosu için zorunlu 'Mail adresiniz' alanı boş. Satır atlanıyor.")
            continue

        data_to_insert = {
            "mailadresi": str(mail_adresi_excel).strip().lower(),
            "adsoyad": str(ad_soyad_excel).strip() if pd.notna(ad_soyad_excel) else 'Bilinmiyor',
            "telefonnumarasi": str(telefon_excel).strip() if pd.notna(telefon_excel) else None,
            "postakodu": str(posta_kodu_excel).strip() if pd.notna(posta_kodu_excel) else None,
            "yasadiginizeyalet": str(eyalet_excel).strip() if pd.notna(eyalet_excel) else None
        }

        try:
            insert_or_update("kursiyerler", data_to_insert, unique_columns_db="mailadresi")
            inserted_or_updated += 1
        except Exception as e:
            print(f"HATA: Satır {row_idx + 2} için 'kursiyerler' tablosuna veri aktarılırken hata oluştu (Mail: '{mail_adresi_excel}'): {e}")
            
    print(f"Bilgi: 'kursiyerler' tablosuna {inserted_or_updated} kayıt başarıyla aktarıldı/güncellendi (toplam {df.shape[0]} satır işlendi).")
    return inserted_or_updated

def get_kursiyer_id_by_mail_or_create_internal(mail_adresi, ad_soyad=None):
    """
    Veritabanından mail adresine göre kursiyerid'yi bulur, yoksa yeni bir kursiyer ekler veya günceller.
    Bu fonksiyon, UPSERT (ON CONFLICT) kullanarak mevcut kursiyeri güncellemeyi de dener.
    """
    if not mail_adresi or pd.isna(mail_adresi) or str(mail_adresi).strip().lower() in ['', 'none']:
        return None

    mail_adresi_clean = str(mail_adresi).strip().lower()
    ad_soyad_clean = ad_soyad if ad_soyad and pd.notna(ad_soyad) and str(ad_soyad).strip().lower() not in ['', 'none'] else 'Bilinmiyor'

    with get_db_cursor() as cursor:
        if not cursor:
            print("HATA: Veritabanı imleci mevcut değil, kursiyer ID alınamıyor/oluşturulamıyor.")
            return None
        
        try:
            # UPSERT işlemi: INSERT etmeye çalış, MailAdresi çakışırsa AdSoyad'ı güncelle
            insert_query = """
                INSERT INTO kursiyerler (mailadresi, adsoyad)
                VALUES (%s, %s) ON CONFLICT (mailadresi) DO UPDATE SET adsoyad = EXCLUDED.adsoyad RETURNING kursiyerid;
            """
            cursor.execute(insert_query, (mail_adresi_clean, ad_soyad_clean))
            new_id_result = cursor.fetchone() # RETURNING ile gelen ID'yi al
            if new_id_result:
                return new_id_result[0] # Yeni veya mevcut ID'yi döndür
            else:
                print(f"HATA: '{mail_adresi_clean}' mail adresine sahip kursiyer eklenirken/güncellenirken ID geri alınamadı.")
                return None
        except Error as e:
            # psycopg2 spesifik bir hata kodu yakalama: 23505 (unique_violation)
            # Normalde ON CONFLICT ile yakalanmalı, ama yine de olası bir senaryo için bırakıldı.
            if e.pgcode == '23505': 
                print(f"UYARI: '{mail_adresi_clean}' mail adresi zaten mevcut. Mevcut ID tekrar çekiliyor.")
                try:
                    cursor.execute("SELECT kursiyerid FROM kursiyerler WHERE mailadresi = %s", (mail_adresi_clean,))
                    result_again = cursor.fetchone()
                    if result_again:
                        return result_again[0]
                    else:
                        print(f"HATA: '{mail_adresi_clean}' mevcutken ID tekrar çekilemedi. Veri tutarsızlığı olabilir.")
                        return None
                except Exception as inner_e:
                    print(f"HATA: Mevcut ID tekrar çekilirken beklenmedik hata oluştu: {inner_e}")
                    return None
            else:
                # Diğer veritabanı hataları
                print(f"HATA: Yeni kursiyer eklenirken veritabanı hatası (SQLCODE: {e.pgcode}): {e}")
                return None
        except Exception as e:
            # Genel Python hataları
            print(f"HATA: Yeni kursiyer eklenirken beklenmedik genel hata: {e}")
            return None

def process_kullanicilar():
    """Kullanicilar.xlsx dosyasından Kullanicilar tablosuna veri aktarır."""
    file_path = os.path.join(data_base_path, "Kullanicilar.xlsx")
    if not os.path.isfile(file_path):
        print(f"HATA: 'Kullanicilar.xlsx' dosyası bulunamadı: {file_path}")
        return 0
    print("\nADIM: 'Kullanicilar.xlsx' dosyasından 'kullanicilar' tablosuna veri aktarılıyor...")
    df = pd.read_excel(file_path)

    # Excel sütunları -> DB sütunları eşlemesi (DB sütunları küçük harf)
    column_map = {
        "KullaniciAdi": "kullaniciadi",
        "Parola": "parola",
        "Yetki": "yetki",
    }

    inserted = 0
    for row_idx, row in df.iterrows():
        data = {}
        row_ok = True
        for excel_col, db_col in column_map.items():
            if excel_col in df.columns: # Excel'de bu sütun gerçekten var mı kontrol et
                val = row.get(excel_col, None)
                data[db_col] = str(val).strip() if pd.notna(val) else None
            else:
                print(f"UYARI: Satır {row_idx + 2}: Excel'de '{excel_col}' sütunu bulunamadı. Bu sütun atlanacak.")
                data[db_col] = None # Sütun yoksa None ata

        # KullaniciAdi ve Parola boş olamaz (DB kısıtlamasına göre)
        if not data.get("kullaniciadi") or not data.get("parola"):
            print(f"UYARI: Satır {row_idx + 2}: Boş 'KullaniciAdi' veya 'Parola' nedeniyle satır atlanıyor.")
            continue
            
        try:
            # KullaniciAdi UNIQUE olduğu için UPSERT mantığı ile çalışacak
            insert_or_update("kullanicilar", data, unique_columns_db="kullaniciadi")
            inserted += 1
        except Exception as e:
            print(f"HATA (kullanicilar insert/update - Satır {row_idx + 2}): {e}")
    print(f"Bilgi: 'kullanicilar' tablosuna {inserted} kayıt başarıyla aktarıldı/güncellendi (toplam {df.shape[0]} satır işlendi).")
    return inserted

def process_basvurular():
    """Basvurular.xlsx dosyasından Basvurular tablosuna veri aktarır."""
    if not latest_vit_path:
        print("HATA: En son VIT klasörü bulunamadı, 'Basvurular.xlsx' işlenemiyor.")
        return 0
    file_path = os.path.join(latest_vit_path, "Basvurular.xlsx")
    if not os.path.isfile(file_path):
        print(f"HATA: 'Basvurular.xlsx' dosyası bulunamadı: {file_path}")
        return 0
    print("\nADIM: 'Basvurular.xlsx' dosyasından 'basvurular' tablosuna veri aktarılıyor...")
    df = pd.read_excel(file_path)

    # Excel sütunları -> DB sütunları eşlemesi (DB sütunları küçük harf)
    column_map = {
        "Zaman damgası": "zamandamgasi",
        "Mail adresiniz": "mailadresi_lookup", # Bu sadece lookup için, doğrudan DB'ye gitmeyecek
        "Şu anki durumunuz": "suankidurum",
        "Yakın zamanda başlayacak ITPH Cybersecurity veya Powerplatform Eğitimlerine Katılmak istemisiniz": "itphegitimkatilmak",
        "Ekonomik Durumunuz": "ekonomikdurum",
        "Şu anda bir dil kursuna devam ediyor musunuz?": "dilkursunadevam",
        "Yabancı dil Seviyeniz [İngilizce]": "ingilizceseviye",
        "Yabancı dil Seviyeniz [Hollandaca]": "hollandacaseviye",
        "Belediyenizden çalışma ile ilgili baskı görüyor musunuz?": "baskigoruyor",
        "Başka bir IT kursu (Bootcamp) bitirdiniz mi?": "bootcampbitirdi",
        "İnternetten herhangi bir IT kursu takip ettiniz mi (Coursera, Udemy gibi)": "onlineitkursu",
        "Daha önce herhangi bir IT iş tecrübeniz var mı?": "ittecrube",
        "Şu anda herhangi bir projeye dahil misiniz? (Öğretmenlik projesi veya Leerwerktraject v.s)": "projedahil",
        "IT sektöründe hangi bölüm veya bölümlerde çalışmak istiyorsunuz (bir den fazla seçenek seçebilirsiniz)": "calismakistegi",
        "Neden VIT projesine katılmak istiyorsunuz? (birden fazla seçenek işaretleyebilirsiniz)": "nedenkatilmakistiyor", 
        "Aşağıya bu projeye katılmak veya IT sektöründe kariyer yapmak için sizi harekete geçiren motivasyondan bahseder misiniz?": "motivasyon",
        "Başvuru Dönemi": "basvurudonemi",
        "Mentor gorusmesi": "mentor_gorusmesi_yapildi", # Yeni eklenen sütun, tipi TEXT olarak işlenecek
    }
    
    inserted = 0
    for row_idx, row in df.iterrows():
        # KursiyerID'yi mail adresine göre bul
        mail_adresi_excel = row.get("Mail adresiniz", None)
        kursiyer_id = get_kursiyer_id_by_email(mail_adresi_excel)

        if kursiyer_id is None:
            print(f"UYARI: Satır {row_idx + 2}: Mail adresi '{mail_adresi_excel}' için KursiyerID bulunamadı. Bu başvuru satırı atlanıyor.")
            continue

        data = {"kursiyerid": kursiyer_id}
        for excel_col, db_col in column_map.items():
            if db_col == "mailadresi_lookup": # Zaten lookup için kullanıldı, tabloya eklemeyeceğiz
                continue
            
            if excel_col in df.columns: # Excel'de bu sütun gerçekten var mı kontrol et
                val = row.get(excel_col, None)
                if db_col == "zamandamgasi":
                    # ZamanDamgasi için uygun tarih formatına dönüştür
                    data[db_col] = convert_excel_date_to_db_date(val)
                # Mentor görüşmesi sütunu artık doğrudan TEXT olarak saklanacak
                # Boolean dönüşümünü kaldırdık, Excel'den gelen string değeri direkt alıyoruz.
                elif db_col == "mentor_gorusmesi_yapildi": 
                    data[db_col] = str(val).strip() if pd.notna(val) else None
                else:
                    # Diğer TEXT sütunları için string'e çevir ve boşlukları temizle
                    data[db_col] = str(val).strip() if pd.notna(val) else None
            else:
                print(f"UYARI: Satır {row_idx + 2}: Basvurular.xlsx'te '{excel_col}' sütunu bulunamadı. Bu sütun atlanıyor.")
                data[db_col] = None # Sütun yoksa None ata
        
        # ZamanDamgasi DB'de NOT NULL değil ama yine de kontrol edelim, boşsa atlayabiliriz
        # Eğer ZamanDamgasi TEXT ise ve boş string olarak kabul ediliyorsa:
        if not data.get("zamandamgasi"):
            print(f"UYARI: Satır {row_idx + 2}: Boş 'Zaman damgası' nedeniyle satır atlanıyor (KursiyerID: {kursiyer_id}).")
            continue

        try:
            insert_or_update("basvurular", data) 
            inserted += 1
        except Exception as e:
            print(f"HATA (basvurular insert - Satır {row_idx + 2}): {e}")
    print(f"Bilgi: 'basvurular' tablosuna {inserted} kayıt başarıyla aktarıldı (toplam {df.shape[0]} satır işlendi).")
    return inserted

def process_mentor():
    """Mentor.xlsx dosyasından Mentortablosu tablosuna veri aktarır."""
    if not latest_vit_path:
        print("HATA: En son VIT klasörü bulunamadı, 'Mentor.xlsx' işlenemiyor.")
        return 0
    file_path = os.path.join(latest_vit_path, "Mentor.xlsx")
    if not os.path.isfile(file_path):
        print(f"HATA: 'Mentor.xlsx' dosyası bulunamadı: {file_path}")
        return 0
    print("\nADIM: 'Mentor.xlsx' dosyasından 'mentortablosu' tablosuna veri aktarılıyor...")
    df = pd.read_excel(file_path)

    # Excel sütunları -> DB sütunları eşlemesi (DB sütunları küçük harf)
    column_map = {
        "Gorusme tarihi": "gorusmetarihi",
        "Mentinin adi soyadi": "kursiyer_adsoyad_lookup", # Bu sütun sadece lookup için kullanılacak
        "Mentorün adı-soyadı": "mentoradsoyad",
        "Katılımcı IT sektörü hakkında bilgi sahibi mi?": "bilgisahibimi",
        "VIT projesinin tamamına katılması uygun olur": "vitprojesinekatilabilirmi",
        "Katılımcı hakkında ne düşünüyorsunuz": "dusunce",
        "Katilimcinin yogunluk durumu": "yogunlukdurumu",
        "Katilimci hakkinda yorumlar": "yorumlar",
    }

    inserted = 0
    for row_idx, row in df.iterrows():
        # KursiyerID'yi "Mentinin adi soyadi"na göre bul
        kursiyer_ad_soyad_excel = row.get("Mentinin adi soyadi", None)
        kursiyer_id = get_kursiyer_id_by_name(kursiyer_ad_soyad_excel)

        if kursiyer_id is None:
            print(f"UYARI: Satır {row_idx + 2}: Ad Soyad '{kursiyer_ad_soyad_excel}' için KursiyerID bulunamadı. Bu mentor görüşmesi satırı atlanıyor.")
            continue

        data = {"kursiyerid": kursiyer_id}
        for excel_col, db_col in column_map.items():
            if db_col == "kursiyer_adsoyad_lookup": # Zaten lookup için kullanıldı
                continue
            if excel_col in df.columns: # Excel'de bu sütun gerçekten var mı kontrol et
                val = row.get(excel_col, None)
                if db_col == "gorusmetarihi":
                    data[db_col] = convert_excel_date_to_db_date(val)
                else:
                    data[db_col] = str(val).strip() if pd.notna(val) else None
            else:
                print(f"UYARI: Satır {row_idx + 2}: 'Mentor.xlsx'te '{excel_col}' sütunu bulunamadı. Bu sütun atlanıyor.")
                data[db_col] = None
        
        # GorusmeTarihi DB'de NOT NULL olarak tanımlanmıştı, kontrol edelim
        if not data.get("gorusmetarihi"):
            print(f"UYARI: Satır {row_idx + 2}: Boş 'Gorusme tarihi' nedeniyle mentor görüşmesi satırı atlanıyor (KursiyerID: {kursiyer_id}).")
            continue

        try:
            insert_or_update("mentortablosu", data) 
            inserted += 1
        except Exception as e:
            print(f"HATA (mentortablosu insert - Satır {row_idx + 2}): {e}")
    print(f"Bilgi: 'mentortablosu' tablosuna {inserted} kayıt başarıyla aktarıldı (toplam {df.shape[0]} satır işlendi).")
    return inserted

def process_projetakiptablosu(): 
    """Mulakatlar.xlsx dosyasından ProjeTakipTablosu tablosuna veri aktarır."""
    if not latest_vit_path:
        print("HATA: En son VIT klasörü bulunamadı, 'Mulakatlar.xlsx' işlenemiyor.")
        return 0
    file_path = os.path.join(latest_vit_path, "Mulakatlar.xlsx")
    if not os.path.isfile(file_path):
        print(f"HATA: 'Mulakatlar.xlsx' dosyası bulunamadı: {file_path}")
        return 0
    print("\nADIM: 'Mulakatlar.xlsx' dosyasından 'projetakiptablosu' tablosuna veri aktarılıyor...")
    df = pd.read_excel(file_path)

    # Excel sütunları -> DB sütunları eşlemesi (DB sütunları küçük harf)
    column_map = {
        "Adınız Soyadınız": "kursiyer_adsoyad_lookup", # Bu sütun sadece lookup için kullanılacak
        "Proje gonderilis tarihi": "projegonderilistarihi",
        "Projenin gelis tarihi": "projeningelistarihi",
        "Projesi Gönderilmiş": "proje_gonderildi_mi", # Bu sütun artık doğrudan DB'ye aktarılacak
    }

    # ProjeTakipTablosu için varsayılan KullaniciID'yi al
    default_kullanici_id = get_first_kullanici_id()
    if default_kullanici_id is None:
        print("HATA: ProjeTakipTablosu için varsayılan KullaniciID bulunamadı. En az bir kullanıcı eklenmeli.")
        return 0

    inserted = 0
    for row_idx, row in df.iterrows():
        # KursiyerID'yi "Adınız Soyadınız"a göre bul
        kursiyer_ad_soyad_excel = row.get("Adınız Soyadınız", None)
        kursiyer_id = get_kursiyer_id_by_name(kursiyer_ad_soyad_excel)

        if kursiyer_id is None:
            print(f"UYARI: Satır {row_idx + 2}: Ad Soyad '{kursiyer_ad_soyad_excel}' için KursiyerID bulunamadı. Bu proje takip satırı atlanıyor.")
            continue

        data = {
            "kursiyerid": kursiyer_id,
            "kullaniciid": default_kullanici_id # Varsayılan kullanıcı ID'sini ata
        }
        for excel_col, db_col in column_map.items():
            if db_col == "kursiyer_adsoyad_lookup": # Bu sütunlar doğrudan DB'ye gitmeyecek
                continue
            
            if excel_col in df.columns: # Excel'de bu sütun gerçekten var mı kontrol et
                val = row.get(excel_col, None)
                if db_col in ["projegonderilistarihi", "projeningelistarihi"]:
                    data[db_col] = convert_excel_date_to_db_date(val)
                # Projesi Gönderilmiş sütunu artık doğrudan TEXT olarak saklanacak
                # Boolean dönüşümünü kaldırdık, Excel'den gelen string değeri direkt alıyoruz.
                elif db_col == "proje_gonderildi_mi": 
                    data[db_col] = str(val).strip() if pd.notna(val) else None
                else:
                    data[db_col] = str(val).strip() if pd.notna(val) else None
            else:
                print(f"UYARI: Satır {row_idx + 2}: 'Mulakatlar.xlsx'te '{excel_col}' sütunu bulunamadı. Bu sütun atlanıyor.")
                data[db_col] = None
        
        # ProjeGonderilisTarihi DB'de NOT NULL değil ama boşsa atlayabiliriz veya None olarak kalır
        # Eğer NOT NULL olsaydı:
        # if not data.get("projegonderilistarihi"):
        #     print(f"UYARI: Satır {row_idx + 2}: Boş 'Proje gonderilis tarihi' nedeniyle satır atlanıyor (KursiyerID: {kursiyer_id}).")
        #     continue

        try:
            insert_or_update("projetakiptablosu", data) 
            inserted += 1
        except Exception as e:
            print(f"HATA (projetakiptablosu insert - Satır {row_idx + 2}): {e}")
    print(f"Bilgi: 'projetakiptablosu' tablosuna {inserted} kayıt başarıyla aktarıldı (toplam {df.shape[0]} satır işlendi).")
    return inserted

def main():
    """Tüm Excel dosyalarını sırayla işler ve veritabanına aktarır."""
    print("ADIM 1: Ana içe aktarma betiği başlatılıyor...")
    total_records_processed = 0

    # ÖNEMLİ: Kursiyerler tablosu diğer tablolar için FK olduğu için ilk bu tablo doldurulmalı.
    # Kullanicilar tablosu da ProjeTakipTablosu için FK olduğu için erken doldurulmalı.
    
    total_records_processed += process_kursiyerler_from_basvurular() 
    total_records_processed += process_kullanicilar() 
    total_records_processed += process_basvurular()
    total_records_processed += process_mentor()
    total_records_processed += process_projetakiptablosu() 

    print(f"\nADIM SONUÇ: TÜM VERİ AKTARIMI TAMAMLANDI. Toplam {total_records_processed} kayıt veritabanına işlendi.")

if __name__ == "__main__":
    main()
