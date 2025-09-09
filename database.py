# database.py
import sqlite3
from flask_login import current_user

def get_user_city():
    """Obtém a cidade do usuário logado"""
    if not current_user.is_authenticated:
        return 'Canindé de São Francisco'  # Fallback
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT city FROM users WHERE id = ?", (current_user.id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 'Canindé de São Francisco'