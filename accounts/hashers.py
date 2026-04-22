import bcrypt
from django.contrib.auth.hashers import BasePasswordHasher
from django.utils.crypto import constant_time_compare

class LegacyPHPPasswordHasher(BasePasswordHasher):
    """
    Legacy PHP Password Hasher for Spilbloo.
    Logic: Spilbloo + password -> Bcrypt
    Format in DB: Standard PHP Bcrypt ($2y$...)
    """
    algorithm = "legacy_php"

    def salt(self):
        return "" # Bcrypt handles its own salt

    def encode(self, password, salt):
        # We use Spilbloo as a fixed prefix (pepper) as per legacy logic
        salted_password = f"Spilbloo{password}"
        # We use bcrypt library directly to match PHP behavior
        hash = bcrypt.hashpw(salted_password.encode('utf-8'), bcrypt.gensalt())
        return f"{self.algorithm}${hash.decode('utf-8')}"

    def verify(self, password, encoded):
        # Salted password
        salted_password = f"Spilbloo{password}"
        
        # Strip the algorithm prefix if it exists (for Django-wrapped hashes)
        # But legacy hashes won't have it.
        if encoded.startswith(f"{self.algorithm}$"):
            encoded = encoded[len(self.algorithm) + 1:]
            
        # Standard PHP hashes begin with $2y$, $2a$, etc.
        try:
            return bcrypt.checkpw(salted_password.encode('utf-8'), encoded.encode('utf-8'))
        except Exception:
            return False

    def safe_summary(self, encoded):
        return {
            'algorithm': self.algorithm,
            'hash': encoded,
        }

    def must_update(self, encoded):
        # Always return True to force Django to upgrade the hash to the preferred hasher upon successful login
        return True
