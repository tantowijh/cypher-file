from fastapi.responses import FileResponse
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from cryptography.fernet import Fernet
import os
import hashlib

router = APIRouter()

# Direktori sementara untuk menyimpan file
temp_dir = "temp"

def ensure_temp_directory():
    """Memastikan direktori sementara (temp) ada"""
    os.makedirs(temp_dir, exist_ok=True)

# Fungsi pembantu untuk cipher Vigenère
def is_alphabetic(char: str) -> bool:
    """Memeriksa apakah karakter adalah alfabet"""
    return char.isalpha()

def get_char_code(char: str) -> int:
    """Mengonversi karakter menjadi kode angka (A=0, B=1, ..., Z=25)"""
    return ord(char.upper()) - 65

def get_char_from_code(code: int) -> str:
    """Mengonversi kode angka menjadi karakter alfabet"""
    return chr((code % 26) + 65)

# Enkripsi menggunakan cipher Vigenère
def encrypt_vigenere(plaintext: str, keyword: str) -> str:
    """Melakukan enkripsi teks menggunakan cipher Vigenère"""
    if not keyword.strip():
        raise ValueError("Kata kunci tidak boleh kosong")
    
    # Memproses kata kunci agar hanya mengandung huruf alfabet
    processed_keyword = ''.join(filter(str.isalpha, keyword.upper()))
    if not processed_keyword:
        raise ValueError("Kata kunci harus mengandung setidaknya satu huruf alfabet")
    
    result = []
    key_index = 0

    for char in plaintext:
        if is_alphabetic(char):
            plain_char_code = get_char_code(char)
            key_char_code = get_char_code(processed_keyword[key_index % len(processed_keyword)])
            encrypted_char_code = (plain_char_code + key_char_code) % 26
            encrypted_char = get_char_from_code(encrypted_char_code)
            result.append(encrypted_char if char.isupper() else encrypted_char.lower())
            key_index += 1
        else:
            result.append(char)
    
    return ''.join(result)

def generate_key(key_path):
    """Menghasilkan kunci baru"""
    ensure_temp_directory()  # Memastikan direktori sementara ada
    # Membuat kunci acak
    key = Fernet.generate_key()
    with open(key_path, "wb") as f:
        f.write(key)
    return key

def load_key(salt_filename):
    """Memuat kunci dari file atau membuat kunci baru jika belum ada"""
    ensure_temp_directory()  # Memastikan direktori sementara ada
    # Nama file kunci
    key_name = f"{salt_filename}.key"
    key_path = os.path.join(temp_dir, key_name)
    if not os.path.exists(key_path):
        key = generate_key(key_path)
        return key
    return open(key_path, "rb").read()

def calculate_hash(file_path):
    """Menghitung hash SHA-256 dari sebuah file"""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(4096):
            sha256.update(chunk)
    return sha256.hexdigest()

@router.post('/api/file/encrypt')
async def encrypt_file(
    file: UploadFile = File(...),
    username: str = Form(...),
    keyword: str = Form(...),
):
    """API untuk mengenkripsi file"""
    try:
        # Membuat kunci pengguna berdasarkan username dan kata kunci
        user_key = encrypt_vigenere(username, keyword)

        # Menyimpan file yang diunggah secara sementara
        ensure_temp_directory()
        filename = file.filename
        file_location = os.path.join(temp_dir, f"{user_key}_{filename}")
        with open(file_location, "wb") as f:
            f.write(await file.read())

        # Memuat atau membuat kunci enkripsi
        key = load_key(f"{user_key}_{filename}")

        fernet = Fernet(key)

        # Mengenkripsi file
        with open(file_location, "rb") as f:
            original = f.read()
        encrypted = fernet.encrypt(original)

        encrypted_path = file_location + ".enc"
        with open(encrypted_path, "wb") as f:
            f.write(encrypted)

        # Menghitung dan menyimpan hash file asli
        hash_value = calculate_hash(file_location)
        hash_path = file_location + ".hash"
        with open(hash_path, "w") as f:
            f.write(hash_value)

        # Mengembalikan file terenkripsi sebagai respons yang dapat diunduh
        return FileResponse(
            path=encrypted_path,
            filename=f"{file.filename}.enc",
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{file.filename}.enc"'}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Enkripsi gagal: {str(e)}")

@router.post('/api/file/decrypt')
async def decrypt_file(
    file: UploadFile = File(...),
    username: str = Form(...),
    keyword: str = Form(...),
):
    """API untuk mendekripsi file"""
    try:
        # Membuat kunci pengguna berdasarkan username dan kata kunci
        user_key = encrypt_vigenere(username, keyword)
        
        # Menyimpan file terenkripsi yang diunggah secara sementara
        ensure_temp_directory()
        filename = file.filename
        file_location = os.path.join(temp_dir, f"{user_key}_{filename}")
        with open(file_location, "wb") as f:
            f.write(await file.read())

        # Memuat kunci dekripsi
        key = load_key(f"{user_key}_{filename.replace('.enc', '')}")

        fernet = Fernet(key)

        # Mendekripsi file
        with open(file_location, "rb") as f:
            encrypted = f.read()
        decrypted = fernet.decrypt(encrypted)

        decrypted_path = file_location.replace(".enc", "")
        with open(decrypted_path, "wb") as f:
            f.write(decrypted)

        # Mengembalikan file yang telah didekripsi sebagai respons yang dapat diunduh
        return FileResponse(
            path=decrypted_path,
            filename=file.filename.replace(".enc", ""),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{file.filename.replace(".enc", "")}"'}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Dekripsi gagal: {str(e)}")

@router.post('/api/file/verify')
async def verify_file(
    file: UploadFile = File(...),
    username: str = Form(...),
    keyword: str = Form(...),
):
    """API untuk memverifikasi integritas file"""
    try:
        # Membuat kunci pengguna berdasarkan username dan kata kunci
        user_key = encrypt_vigenere(username, keyword)

        # Menyimpan file yang diunggah secara sementara
        ensure_temp_directory()
        filename = file.filename
        file_location = os.path.join(temp_dir, f"{user_key}_{filename}")
        with open(file_location, "wb") as f:
            f.write(await file.read())

        # Memeriksa keberadaan file hash
        hash_file = file_location + ".hash"
        if not os.path.exists(hash_file):
            raise HTTPException(
                status_code=400, detail="File hash tidak ditemukan untuk verifikasi")

        # Membaca hash yang tersimpan
        with open(hash_file, "r") as f:
            stored_hash = f.read().strip()

        # Menghitung hash file saat ini
        current_hash = calculate_hash(file_location)

        if stored_hash == current_hash:
            return {"message": "Integritas file berhasil diverifikasi"}
        else:
            return {"message": "Verifikasi integritas file gagal"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Verifikasi gagal: {str(e)}")