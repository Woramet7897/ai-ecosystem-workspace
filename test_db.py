import psycopg2

try:
    # 1. เชื่อมต่อไปยัง PostgreSQL Server ในเครื่อง
    connection = psycopg2.connect(
        host="localhost",
        database="postgres",
        user="postgres",
        password="131205", 
        port="5432"
    )

    cursor = connection.cursor()
    
    # 2. ทดสอบยิงคำสั่ง SQL เพื่อเช็คเวอร์ชัน
    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()
    
    print(" เชื่อมต่อฐานข้อมูลสำเร็จแล้ว!")
    print(f"เวอร์ชันฐานข้อมูลของคุณคือ: {db_version}")

except Exception as error:
    print(f" เชื่อมต่อล้มเหลวเนื่องจาก: {error}")

finally:
    # 3. ปิดการเชื่อมต่อเสมอเมื่อทำงานเสร็จ
    if 'connection' in locals() and connection:
        cursor.close()
        connection.close()
        print("ปิดการเชื่อมต่อเรียบร้อย")
