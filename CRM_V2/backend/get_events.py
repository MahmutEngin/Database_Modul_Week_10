import datetime
import os.path
import logging # Loglama için ekledik

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# auth.py modülünden kimlik doğrulama fonksiyonu
# Bu, Calendar API ve Drive API gibi tüm gerekli kapsamları içermelidir.
from auth import auth 
from database_manager import DatabaseManager, DB_CONFIG
from psycopg2 import sql, Error

# Loglama yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SCOPES burada tekrar tanımlanmamalı, auth.py'den gelmeli.
# Eğer auth.py'de calendar.readonly ve drive.readonly yoksa, oraya ekleyin.
# Bu dosyadaki SCOPES tanımını kaldırın veya yorum satırı yapın:
# SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"] 

def sync_calendar_events(): # Fonksiyon adını daha açıklayıcı yaptık
    """Shows basic usage of the Google Calendar API and saves events to PostgreSQL.
    Returns: List of events fetched from Google Calendar.
    """
    # Kimlik doğrulama için auth.py'deki auth() fonksiyonunu kullanın
    creds = auth() 
    if not creds:
        logger.error("Kimlik doğrulama başarısız oldu. Takvim etkinlikleri senkronize edilemiyor.")
        return []

    db_manager = None
    try:
        db_manager = DatabaseManager(DB_CONFIG)
        db_manager.connect()
        logger.info("Veritabanına başarıyla bağlanıldı.")
    except Exception as e:
        logger.error(f"Veritabanına bağlanırken hata oluştu: {e}")
        return []

    events = []

    try:
        service = build("calendar", "v3", credentials=creds)

        now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
        logger.info("Yaklaşan 10 etkinlik getiriliyor ve kaydediliyor...")
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            logger.info("Yaklaşan etkinlik bulunamadı.")
            return []

        for event in events:
            event_id = event.get('id')
            summary = event.get('summary', 'Başlıksız Etkinlik')
            description = event.get('description', '')
            location = event.get('location', '')
            
            start_info = event.get('start', {})
            end_info = event.get('end', {})

            start_datetime_str = start_info.get('dateTime', start_info.get('date'))
            end_datetime_str = end_info.get('dateTime', end_info.get('date'))

            # Zaman damgalarını standardize etme
            start_datetime = None
            end_datetime = None

            if start_datetime_str:
                try:
                    # ISO formatından direkt çeviri, zaman dilimini korur veya otomatik olarak ekler
                    start_datetime = datetime.datetime.fromisoformat(start_datetime_str)
                    if start_datetime.tzinfo is None: # Eğer zamandilimi bilgisi yoksa UTC olarak kabul et
                        start_datetime = start_datetime.replace(tzinfo=datetime.timezone.utc)
                except ValueError:
                    logger.warning(f"Başlangıç zamanı '{start_datetime_str}' geçersiz format. Atlanıyor.")
                    start_datetime = None 
            
            if end_datetime_str:
                try:
                    end_datetime = datetime.datetime.fromisoformat(end_datetime_str)
                    if end_datetime.tzinfo is None: # Eğer zamandilimi bilgisi yoksa UTC olarak kabul et
                        end_datetime = end_datetime.replace(tzinfo=datetime.timezone.utc)
                except ValueError:
                    logger.warning(f"Bitiş zamanı '{end_datetime_str}' geçersiz format. Atlanıyor.")
                    end_datetime = None 

            organizer_email = event.get('organizer', {}).get('email', '')
            organizer_display_name = event.get('organizer', {}).get('displayName', '')

            attendees = event.get('attendees', [])
            attendee_emails = ','.join([a['email'] for a in attendees if 'email' in a])

            html_link = event.get('htmlLink', '')

            if not event_id:
                logger.warning(f"Event ID bulunamadı, bu etkinlik atlanıyor: {summary}")
                continue 

            insert_or_update_query = sql.SQL("""
                INSERT INTO etkinlikler_tablosu (
                    event_id, summary, description, location, 
                    start_datetime, end_datetime, organizer_email, 
                    organizer_display_name, attendee_emails, html_link
                ) VALUES (
                    %s, %s, %s, %s, 
                    %s, %s, %s, 
                    %s, %s, %s
                )
                ON CONFLICT (event_id) DO UPDATE SET
                    summary = EXCLUDED.summary,
                    description = EXCLUDED.description,
                    location = EXCLUDED.location,
                    start_datetime = EXCLUDED.start_datetime,
                    end_datetime = EXCLUDED.end_datetime,
                    organizer_email = EXCLUDED.organizer_email,
                    organizer_display_name = EXCLUDED.organizer_display_name,
                    attendee_emails = EXCLUDED.attendee_emails,
                    html_link = EXCLUDED.html_link,
                    updated_at = NOW(); -- updated_at sütununun tabloda var olduğundan emin olun
            """)

            try:
                db_manager.execute_query(
                    insert_or_update_query,
                    (event_id, summary, description, location, 
                     start_datetime, end_datetime, organizer_email, 
                     organizer_display_name, attendee_emails, html_link)
                )
                db_manager.conn.commit()
                logger.info(f"Etkinlik '{summary}' ({event_id}) veritabanına kaydedildi/güncellendi.")
            except Error as db_error:
                db_manager.conn.rollback()
                logger.error(f"Veritabanına kaydederken hata oluştu: {db_error} for event {summary}")
            except Exception as generic_error:
                db_manager.conn.rollback()
                logger.error(f"Beklenmeyen bir hata oluştu: {generic_error} for event {summary}")

    except HttpError as error:
        logger.error(f"Google Calendar API hatası: {error}")
    except Exception as e:
        logger.error(f"Beklenmeyen bir hata oluştu: {e}")
    finally:
        if db_manager:
            db_manager.close()
            logger.info("Veritabanı bağlantısı kapatıldı.")
            
    return events


if __name__ == "__main__":
    sync_calendar_events()