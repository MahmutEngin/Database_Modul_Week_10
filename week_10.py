import psycopg2
from psycopg2 import Error
from datetime import date # Tarih nesnelerini işlemek için

# Veritabanı bağlantı parametreleri - KENDİ BİLGİLERİNİZLE DEĞİŞTİRİN
DB_NAME = "week_10" # Örnek: "my_task_db"
DB_USER = "postgres"     # Örnek: "postgres"
DB_PASSWORD = "Mahmut" # Kendi PostgreSQL şifreniz
DB_HOST = "127.0.0.1"         # Veritabanı sunucunuzun adresi (genellikle localhost)
DB_PORT = "5432"              # PostgreSQL varsayılan portu

def create_connection():
    """PostgreSQL veritabanına bağlantı kurar."""
    connection = None
    try:
        connection = psycopg2.connect(
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        print("PostgreSQL veritabanına bağlantı başarılı.")
    except Error as e:
        print(f"Hata oluştu: '{e}'")
    return connection

def execute_query(connection, query, fetch=False):
    """Veritabanında bir sorgu çalıştırır."""
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        if fetch:
            result = cursor.fetchall()
            return result
        connection.commit()
        print("Sorgu başarıyla çalıştırıldı.")
    except Error as e:
        print(f"Sorgu çalıştırılırken hata oluştu: '{e}'")
        connection.rollback() # Hata durumunda geri al
    finally:
        cursor.close()
    return None

# --- Ana Betik Başlangıcı ---
if __name__ == "__main__":
    conn = create_connection()

    if conn:
        # 1. Tabloları Oluşturma
        # Mevcut tabloları sil (betiği tekrar çalıştırmak için kullanışlıdır)
        drop_tables_query = """
        DROP TABLE IF EXISTS departments_assignment;
        DROP TABLE IF EXISTS employees;
        """
        execute_query(conn, drop_tables_query)
        print("Mevcut tablolar silindi (varsa).")

        # 'employees' tablosunu oluşturma
        create_employees_table_query = """
        CREATE TABLE employees (
            emp_id INT PRIMARY KEY,
            first_name VARCHAR(50),
            last_name VARCHAR(50),
            salary INT,
            job_title VARCHAR(100),
            gender VARCHAR(10),
            hire_date DATE
        );
        """
        execute_query(conn, create_employees_table_query)
        print(" 'employees' tablosu oluşturuldu.")

        # 'departments_assignment' tablosunu oluşturma
        # Bu tablo, görseldeki 'departments table'ın yapısını yansıtır.
        # emp_id'nin employees tablosuna referans veren bir dış anahtar olarak tanımlanmıştır.
        create_departments_assignment_table_query = """
        CREATE TABLE departments_assignment (
            emp_id INT,
            department_name VARCHAR(100),
            dept_id INT,
            FOREIGN KEY (emp_id) REFERENCES employees (emp_id)
        );
        """
        execute_query(conn, create_departments_assignment_table_query)
        print(" 'departments_assignment' tablosu oluşturuldu.")

        # 2. Tablolara Veri Ekleme
        # Employees verileri
        employees_data = [
            (17679, 'Robert', 'Gilmore', 110000, 'Operations Director', 'Male', date(2018, 9, 4)),
            (26650, 'Elvis', 'Ritter', 86000, 'Sales Manager', 'Male', date(2017, 11, 24)),
            (30840, 'David', 'Forrester', 85000, 'Data Analyst', 'Male', date(2019, 12, 2)),
            (49714, 'Hugo', 'Forrester', 55000, 'IT Support Specialist', 'Male', date(2019, 11, 22)),
            (51821, 'Linda', 'Foster', 95000, 'Data Scientist', 'Female', date(2019, 4, 29)),
            (67323, 'Lisa', 'Wiener', 75000, 'Business Analyst', 'Female', date(2019, 8, 9)),
            (70950, 'Rodney', 'Weaver', 87000, 'Project Manager', 'Male', date(2018, 12, 20)),
            (71329, 'Gayle', 'Meyer', 77000, 'HR Manager', 'Female', date(2019, 6, 28)),
            (76589, 'Jason', 'Christian', 99000, 'Project Manager', 'Male', date(2019, 1, 21)),
            (97927, 'Bille', 'Lanning', 67000, 'Web Developer', 'Female', date(2018, 6, 25))
        ]

        insert_employee_query = """
        INSERT INTO employees (emp_id, first_name, last_name, salary, job_title, gender, hire_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (emp_id) DO NOTHING; -- emp_id çakışırsa eklemeyi atla
        """
        cursor = conn.cursor()
        try:
            cursor.executemany(insert_employee_query, employees_data)
            conn.commit()
            print("Çalışan verileri başarıyla eklendi.")
        except Error as e:
            print(f"Çalışan verileri eklenirken hata oluştu: {e}")
            conn.rollback()
        finally:
            cursor.close()

        # Departments Assignment verileri (görseldeki 'departments table'dan)
        # NOT: emp_id 49823 yerine 49714 kullanılmıştır (yukarıdaki açıklamalara bakınız)
        departments_assignment_data = [
            (17679, 'Operations', 13),
            (26650, 'Marketing', 14),
            (30840, 'Operations', 13),
            (49714, 'Technology', 12), # BURAYI KONTROL EDİN - 49823 yerine 49714 olmalı
            (51821, 'Operations', 13),
            (67323, 'Marketing', 14),
            (71119, 'Administrative', 11),
            (76589, 'Operations', 13),
            (97927, 'Technology', 12)
        ]
        insert_department_assignment_query = """
        INSERT INTO departments_assignment (emp_id, department_name, dept_id)
        VALUES (%s, %s, %s);
        """
        cursor = conn.cursor()
        try:
            cursor.executemany(insert_department_assignment_query, departments_assignment_data)
            conn.commit()
            print("Departman atama verileri başarıyla eklendi.")
        except Error as e:
            print(f"Departman atama verileri eklenirken hata oluştu: {e}")
            conn.rollback()
        finally:
            cursor.close()

        print("\n--- TASK_1 Sorularının Çözümü ---")

        # 1. Rodney Weaver'dan daha fazla maaş alan çalışanları bulun.
        print("\n1. Rodney Weaver'dan daha fazla maaş alan çalışanlar:")
        query_1 = """
        SELECT first_name, last_name, salary
        FROM employees
        WHERE salary > (SELECT salary FROM employees WHERE first_name = 'Rodney' AND last_name = 'Weaver');
        """
        results_1 = execute_query(conn, query_1, fetch=True)
        if results_1:
            for row in results_1:
                print(f"  {row[0]} {row[1]}, Maaş: {row[2]}")

        # 2. Ortalama, en düşük ve en yüksek maaşları bulun.
        print("\n2. Ortalama, En Düşük, En Yüksek Maaşlar:")
        query_2 = """
        SELECT AVG(salary) AS average_salary, MIN(salary) AS min_salary, MAX(salary) AS max_salary
        FROM employees;
        """
        results_2 = execute_query(conn, query_2, fetch=True)
        if results_2:
            for row in results_2:
                print(f"  Ortalama Maaş: {row[0]:.2f}, En Düşük Maaş: {row[1]}, En Yüksek Maaş: {row[2]}")

        # 3. Maaşı 87000'den fazla olan çalışanları bulun. Sorgumuz çalışanların adını, soyadını ve maaş bilgilerini döndürmelidir.
        print("\n3. Maaşı 87000'den fazla olan çalışanlar:")
        query_3 = """
        SELECT first_name, last_name, salary
        FROM employees
        WHERE salary > 87000;
        """
        results_3 = execute_query(conn, query_3, fetch=True)
        if results_3:
            for row in results_3:
                print(f"  {row[0]} {row[1]}, Maaş: {row[2]}")

        # 4. Operasyon departmanında (departments tablosu) çalışan çalışanların (employees tablosundan ad, soyad) adını ve soyadını döndürün.
        print("\n4. Operasyon departmanında çalışanlar:")
        query_4 = """
        SELECT e.first_name, e.last_name
        FROM employees e
        JOIN departments_assignment da ON e.emp_id = da.emp_id
        WHERE da.department_name = 'Operations';
        """
        results_4 = execute_query(conn, query_4, fetch=True)
        if results_4:
            for row in results_4:
                print(f"  {row[0]} {row[1]}")

        # 5. Teknoloji departmanında (departments tablosu) çalışan çalışanların (employees tablosundan ad, soyad) adını ve soyadını döndürün.
        print("\n5. Teknoloji departmanında çalışanlar:")
        query_5 = """
        SELECT e.first_name, e.last_name
        FROM employees e
        JOIN departments_assignment da ON e.emp_id = da.emp_id
        WHERE da.department_name = 'Technology';
        """
        results_5 = execute_query(conn, query_5, fetch=True)
        if results_5:
            for row in results_5:
                print(f"  {row[0]} {row[1]}")

        # 6. Kadın çalışanların ortalama maaşını bulun.
        print("\n6. Kadın çalışanların ortalama maaşı:")
        query_6 = """
        SELECT AVG(salary) AS average_female_salary
        FROM employees
        WHERE gender = 'Female';
        """
        results_6 = execute_query(conn, query_6, fetch=True)
        if results_6:
            for row in results_6:
                print(f"  Ortalama Kadın Maaşı: {row[0]:.2f}")

        # 7. Her departmanın ortalama maaşını bulun.
        print("\n7. Her departmanın ortalama maaşı:")
        query_7 = """
        SELECT da.department_name, AVG(e.salary) AS average_department_salary
        FROM employees e
        JOIN departments_assignment da ON e.emp_id = da.emp_id
        GROUP BY da.department_name;
        """
        results_7 = execute_query(conn, query_7, fetch=True)
        if results_7:
            for row in results_7:
                print(f"  Departman: {row[0]}, Ortalama Maaş: {row[1]:.2f}")

        # 8. En eski ve en yeni çalışanları bulun.
        print("\n8. En eski ve en yeni çalışanlar (işe alım tarihine göre):")
        query_8_oldest = """
        SELECT first_name, last_name, hire_date
        FROM employees
        ORDER BY hire_date ASC
        LIMIT 1;
        """
        print("  En Eski Çalışan:")
        results_8_oldest = execute_query(conn, query_8_oldest, fetch=True)
        if results_8_oldest:
            for row in results_8_oldest:
                print(f"    {row[0]} {row[1]}, İşe Alım Tarihi: {row[2]}")

        query_8_newest = """
        SELECT first_name, last_name, hire_date
        FROM employees
        ORDER BY hire_date DESC
        LIMIT 1;
        """
        print("  En Yeni Çalışan:")
        results_8_newest = execute_query(conn, query_8_newest, fetch=True)
        if results_8_newest:
            for row in results_8_newest:
                print(f"    {row[0]} {row[1]}, İşe Alım Tarihi: {row[2]}")

        # 9. En yüksek maaşlı çalışanın işe alım tarihini ve departmanını bulun.
        print("\n9. En yüksek maaşlı çalışanın işe alım tarihi ve departmanı:")
        query_9 = """
        SELECT e.first_name, e.last_name, e.hire_date, da.department_name
        FROM employees e
        LEFT JOIN departments_assignment da ON e.emp_id = da.emp_id
        ORDER BY e.salary DESC
        LIMIT 1;
        """
        results_9 = execute_query(conn, query_9, fetch=True)
        if results_9:
            for row in results_9:
                # Eğer bir çalışanın departmanı yoksa (departments_assignment tablosunda yoksa), None olarak gelecektir.
                dept_name = row[3] if row[3] else "Atanmamış"
                print(f"  {row[0]} {row[1]}, İşe Alım Tarihi: {row[2]}, Departman: {dept_name}")

        # 10. En düşük maaşlı çalışanın işe alım tarihini ve departmanını bulun.
        print("\n10. En düşük maaşlı çalışanın işe alım tarihi ve departmanı:")
        query_10 = """
        SELECT e.first_name, e.last_name, e.hire_date, da.department_name
        FROM employees e
        LEFT JOIN departments_assignment da ON e.emp_id = da.emp_id
        ORDER BY e.salary ASC
        LIMIT 1;
        """
        results_10 = execute_query(conn, query_10, fetch=True)
        if results_10:
            for row in results_10:
                dept_name = row[3] if row[3] else "Atanmamış"
                print(f"  {row[0]} {row[1]}, İşe Alım Tarihi: {row[2]}, Departman: {dept_name}")

        # Bağlantıyı kapatma
        conn.close()
        print("\nPostgreSQL veritabanı bağlantısı kapatıldı.")