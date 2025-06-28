import psycopg2
from psycopg2 import sql, Error
from psycopg2.extras import RealDictCursor # Sözlük olarak veri çekmek için eklendi

# Veritabanı bağlantı detayları
# Lütfen bu bilgileri kendi PostgreSQL veritabanı ayarlarınıza göre DÜZELTİNİZ!
DB_CONFIG = {
    "host": "127.0.0.1",
    "database": "dbkursiyer",  # Veritabanı adınız
    "user": "postgres",        # PostgreSQL kullanıcı adınız
    "password": "Mahmut",      # PostgreSQL şifreniz
    "port": "5432"             # PostgreSQL port numaranız (varsayılan 5432)
}

class DatabaseManager:
    """Veritabanı bağlantısını ve işlemlerini yöneten sınıf.
    'with' ifadesiyle kullanıldığında bağlantıyı otomatik olarak açar ve kapatır.
    """

    def __init__(self, config):
        """Veritabanı yöneticisini başlatır."""
        self.config = config
        self.conn = None
        self.cursor = None

    def __enter__(self):
        """'with' ifadesi kullanıldığında veritabanı bağlantısını açar."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """'with' ifadesi tamamlandığında veya bir hata oluştuğunda bağlantıyı kapatır."""
        self.close()
        # Eğer bir hata oluşursa (exc_type None değilse), hatayı yeniden fırlatabiliriz.
        # return False yaparsak hatayı yutarız, True yaparsak hata başarılı bir şekilde işlenmiş sayılır.
        # Burada hatanın dışarıya yayılmasını istediğimiz için None döndürüyoruz (varsayılan davranış).

    def connect(self):
        """PostgreSQL veritabanına bağlanır."""
        try:
            # RealDictCursor, sorgu sonuçlarını sözlük olarak döndürmeyi sağlar.
            # Normal cursor ile tuple olarak döner.
            self.conn = psycopg2.connect(**self.config)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor) 
            print("Veritabanı bağlantısı başarılı.")
        except Error as e:
            print(f"Veritabanı bağlantı hatası: {e}")
            self.conn = None
            self.cursor = None
            raise # Bağlantı hatasını çağrılan yere yeniden fırlat

    def close(self):
        """Veritabanı bağlantısını ve imlecini kapatır."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            print("Veritabanı bağlantısı kapatıldı.")

    def execute_query(self, query, params=None, fetch_result=False):
        """
        Veritabanında bir sorgu çalıştırır.
        Parametreli sorgular için 'params' kullanılmalıdır (SQL Injection önleme).
        Args:
            query (str/sql.SQL): Çalıştırılacak SQL sorgusu.
            params (tuple/list, optional): Sorgu parametreleri. Defaults to None.
            fetch_result (bool, optional): Eğer sorgu bir sonuç döndürüyorsa (örn: INSERT ... RETURNING id), True yapılır. Defaults to False.
        Returns:
            bool/dict/None: Başarılıysa True, hata varsa False. fetch_result True ise, ilk döndürülen satırı sözlük olarak döndürür.
        """
        if not self.conn or not self.cursor:
            print("HATA: Veritabanı bağlantısı mevcut değil veya kapalı.")
            return None

        try:
            self.cursor.execute(query, params)
            if fetch_result:
                # INSERT/UPDATE/DELETE RETURNING ID gibi durumlarda kullanılır.
                # RealDictCursor sayesinde doğrudan sözlük döner
                return self.cursor.fetchone() 
            self.conn.commit() # Değişiklikleri kalıcı hale getir
            return True
        except Error as e:
            self.conn.rollback() # Hata durumunda değişiklikleri geri al
            print(f"Sorgu çalıştırma hatası: {e}")
            return False
        except Exception as e:
            self.conn.rollback()
            print(f"Beklenmeyen sorgu hatası: {e}")
            return False

    def fetch_one(self, query, params=None):
        """Tek bir satır veri çeker ve sözlük olarak döndürür."""
        if not self.conn or not self.cursor:
            print("HATA: Veritabanı bağlantısı mevcut değil.")
            return None
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchone() # RealDictCursor sayesinde sözlük döner
        except Error as e:
            print(f"Veri çekme hatası (tekli): {e}")
            return None

    def fetch_all(self, query, params=None):
        """Tüm satırları veri çeker ve sözlük listesi olarak döndürür."""
        if not self.conn or not self.cursor:
            print("HATA: Veritabanı bağlantısı mevcut değil.")
            return None
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall() # RealDictCursor sayesinde sözlük listesi döner
        except Error as e:
            print(f"Veri çekme hatası (tümü): {e}")
            return None

    def create_tables(self):
        """
        Uygulama için gerekli tabloları oluşturur.
        CREATE TABLE IF NOT EXISTS ifadesi, tablonun zaten var olması durumunda hata vermesini önler.
        """
        create_table_queries = [
            """
            CREATE TABLE IF NOT EXISTS Kursiyerler (
                KursiyerID SERIAL PRIMARY KEY,
                AdSoyad VARCHAR(100) NOT NULL,
                MailAdresi VARCHAR(100) UNIQUE NOT NULL,
                TelefonNumarasi TEXT,
                PostaKodu TEXT,
                YasadiginizEyalet TEXT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Kullanicilar (
                KullaniciID SERIAL PRIMARY KEY,
                KullaniciAdi VARCHAR(50) UNIQUE NOT NULL,
                Parola VARCHAR(255) NOT NULL, -- Şifreler hashlenmiş olarak saklanmalı!
                Yetki VARCHAR(50) NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Basvurular (
                BasvuruID SERIAL PRIMARY KEY,
                KursiyerID INT NOT NULL,
                ZamanDamgasi TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Tarih ve saat için TIMESTAMP
                SuAnkiDurum TEXT NOT NULL,                     -- VARCHAR(50) yerine TEXT
                ITPHEgitimKatilmak TEXT,                       -- BOOLEAN yerine TEXT
                EkonomikDurum TEXT,                            -- Zaten TEXT
                DilKursunaDevam TEXT,                          -- BOOLEAN yerine TEXT
                IngilizceSeviye TEXT,                          -- VARCHAR(20) yerine TEXT
                HollandacaSeviye TEXT,                         -- VARCHAR(20) yerine TEXT
                BaskiGoruyor TEXT,                             -- BOOLEAN yerine TEXT
                BootcampBitirdi TEXT,                          -- BOOLEAN yerine TEXT
                OnlineITKursu TEXT,                            -- BOOLEAN yerine TEXT
                ITTecrube TEXT,                                -- Zaten TEXT
                ProjeDahil TEXT,                               -- BOOLEAN yerine TEXT
                motivasyon TEXT,  
                CalismakIstegi TEXT,                           -- BOOLEAN yerine TEXT
                NedenKatilmakIstiyor TEXT,                     -- Zaten TEXT
                BasvuruDonemi TEXT,                            -- VARCHAR(50) yerine TEXT
                mentor_gorusmesi_yapildi TEXT,
                FOREIGN KEY (KursiyerID) REFERENCES Kursiyerler(KursiyerID)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Mentortablosu (
                MentorID SERIAL PRIMARY KEY,
                GorusmeTarihi DATE NOT NULL,
                MentorAdSoyad VARCHAR(100) NOT NULL,
                KursiyerID INT NOT NULL,
                BilgiSahibiMi TEXT,
                VITProjesineKatilabilirMi TEXT,
                Dusunce TEXT,
                YogunlukDurumu TEXT,
                Yorumlar TEXT,
                FOREIGN KEY (KursiyerID) REFERENCES Kursiyerler(KursiyerID)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS ProjeTakipTablosu (
                ProjeTakipID SERIAL PRIMARY KEY,
                KursiyerID INT NOT NULL,
                ProjeGonderilisTarihi DATE,
                ProjeninGelisTarihi DATE,
                proje_gonderildi_mi TEXT,
                KullaniciID INT NOT NULL, -- Kullanicilar tablosu ile ilişki için eklendi
                FOREIGN KEY (KursiyerID) REFERENCES Kursiyerler(KursiyerID),
                FOREIGN KEY (KullaniciID) REFERENCES Kullanicilar(KullaniciID)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS EtkinliklerTablosu (
                event_id TEXT,
                start_datetime TIMESTAMP NOT NULL,
                attendee_emails TEXT, -- Virgülle ayrılmış e-postalar için
                organizer_email VARCHAR(100),
                summary TEXT
            );
            """
        ]
        
        print("Tablolar oluşturuluyor veya kontrol ediliyor...")
        for query_text in create_table_queries:
            try:
                self.cursor.execute(query_text)
                self.conn.commit()
                print(f"Sorgu başarıyla çalıştırıldı: {query_text.strip().splitlines()[0]}...")
            except Error as e:
                self.conn.rollback()
                print(f"Tablo oluşturma hatası: {e}\nSorgu: {query_text.strip().splitlines()[0]}...")
            except Exception as e:
                self.conn.rollback()
                print(f"Beklenmeyen tablo oluşturma hatası: {e}\nSorgu: {query_text.strip().splitlines()[0]}...")

if __name__ == "__main__":
    try:
        # Uygulama başlatıldığında veya test edilirken tabloları oluşturmak için
        with DatabaseManager(DB_CONFIG) as db:
            db.create_tables()
            print("Veritabanı tabloları başarıyla oluşturuldu veya güncellendi.")
    except Exception as e:
        print(f"Veritabanı başlatılırken hata oluştu: {e}")
    finally:
        print("Betiğin ana kısmı tamamlandı ve çıkılıyor.")

