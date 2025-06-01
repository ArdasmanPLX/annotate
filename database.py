import sqlite3
import logging
import os
import json

class DatabaseManager:
    def __init__(self, db_name='annotations.db'):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS annotations
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      image_path TEXT UNIQUE,
                      annotation TEXT,
                      is_new INTEGER DEFAULT 1,
                      is_approved INTEGER DEFAULT 0)''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_image_path ON annotations(image_path)')
        conn.commit()
        conn.close()

    def execute_query(self, query, params=(), fetch=False):
        try:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            c.execute(query, params)
            if fetch:
                result = c.fetchall()
            else:
                result = None
            conn.commit()
            return result if fetch else True
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            logging.error(f"Query: {query}")
            logging.error(f"Params: {params}")
            return None if fetch else False
        finally:
            conn.close()

    def insert_or_update_annotation(self, image_path, annotation):
        query = """INSERT OR REPLACE INTO annotations 
                   (image_path, annotation, is_new) 
                   VALUES (?, ?, 1)"""
        return self.execute_query(query, (image_path, annotation))

    # Для обратной совместимости, если где-то все еще используется старый метод
    def insert_annotation(self, image_path, annotation):
        return self.insert_or_update_annotation(image_path, annotation)

    def update_annotation(self, image_path, annotation):
        query = """UPDATE annotations 
                   SET annotation = ?, is_new = 0 
                   WHERE image_path = ?"""
        success = self.execute_query(query, (annotation, image_path))
        if success:
            logging.info(f"Annotation updated for {image_path}")
        else:
            logging.error(f"Failed to update annotation for {image_path}")
        return success

    def get_annotation_by_filename(self, filename):
        query = """SELECT annotation, is_approved, image_path 
                   FROM annotations 
                   WHERE image_path LIKE ?"""
        result = self.execute_query(query, ('%' + filename,), fetch=True)
        if result:
            return result[0]
        return None

    def get_annotation(self, image_name):
        query = "SELECT annotation, is_approved, image_path FROM annotations WHERE image_path LIKE ?"
        result = self.execute_query(query, ('%' + image_name,), fetch=True)
        return result[0] if result else None

    def get_image_path(self, image_name):
        query = "SELECT image_path FROM annotations WHERE image_path LIKE ?"
        result = self.execute_query(query, ('%' + image_name,), fetch=True)
        return result[0][0] if result else None

    def update_image_path(self, old_image_name, new_image_path):
        query = "UPDATE annotations SET image_path = ? WHERE image_path LIKE ?"
        return self.execute_query(query, (new_image_path, '%' + old_image_name))

    def get_annotation(self, image_path):
        query = "SELECT annotation, is_approved FROM annotations WHERE image_path = ?"
        result = self.execute_query(query, (image_path,), fetch=True)
        if result:
            return result[0]  # Возвращаем кортеж (annotation, is_approved)
        return None

    def get_approved_annotations(self):
        query = "SELECT image_path, annotation FROM annotations WHERE is_approved = 1"
        return self.execute_query(query, fetch=True)

    def approve_all_annotations(self):
        query = "UPDATE annotations SET is_approved = 1, is_new = 0"
        return self.execute_query(query)

    def get_all_annotations(self):
        query = "SELECT image_path, annotation, is_new, is_approved FROM annotations"
        results = self.execute_query(query, fetch=True)
        return [(os.path.basename(row[0]), row[1], row[2], row[3]) for row in results]

    def update_annotation_status(self, image_path, is_approved):
        query = "UPDATE annotations SET is_approved = ?, is_new = 0 WHERE image_path = ?"
        return self.execute_query(query, (int(is_approved), image_path))

    def delete_annotation(self, image_path):
        query = "DELETE FROM annotations WHERE image_path = ?"
        return self.execute_query(query, (image_path,))

    def clear_database(self):
        query = "DELETE FROM annotations"
        return self.execute_query(query)

    def get_all_annotations(self):
        query = "SELECT image_path, annotation, is_new, is_approved FROM annotations"
        return self.execute_query(query, fetch=True)

    def import_annotations(self, data):
        for item in data:
            image_path, annotation, is_new, is_approved = item
            query = """INSERT OR REPLACE INTO annotations 
                       (image_path, annotation, is_new, is_approved) 
                       VALUES (?, ?, ?, ?)"""
            self.execute_query(query, (image_path, annotation, is_new, is_approved))