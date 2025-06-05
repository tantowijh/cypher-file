from fastapi.responses import FileResponse
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from cryptography.fernet import Fernet
import os
import hashlib

router = APIRouter()

# Direktori untuk menyimpan file kunci dan hash
storage_dir = "storage"

def ensure_storage_directory():
    """Memastikan direktori storage ada"""
    os.makedirs(storage_dir, exist_ok=True)

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
    ensure_storage_directory()
    # Membuat kunci acak
    key = Fernet.generate_key()
    with open(key_path, "wb") as f:
        f.write(key)
    return key

def load_key(salt_filename, mode: str = 'encrypt'):
    """Memuat kunci dari file atau membuat kunci baru jika belum ada"""
    ensure_storage_directory()
    # Nama file kunci
    key_name = f"{salt_filename}.key"
    key_path = os.path.join(storage_dir, key_name)
    if not os.path.exists(key_path):
        if mode == 'encrypt':
            # Jika mode encrypt, buat kunci baru
            key = generate_key(key_path)
            return key
        elif mode == 'decrypt':
            # Jika mode decrypt, kunci harus sudah ada
            raise HTTPException(status_code=404, detail="Kunci tidak ditemukan. Pastikan file telah dienkripsi terlebih dahulu.")
        else:
            raise HTTPException(status_code=400, detail="Mode tidak dikenali. Gunakan 'encrypt' atau 'decrypt'.")
    return open(key_path, "rb").read()

def calculate_hash(file_path):
    """Menghitung hash SHA-256 dari sebuah file"""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(4096):
            sha256.update(chunk)
    return sha256.hexdigest()

def validate_file(file: UploadFile, mode: str):
    """
    mode: 'encrypt' or 'verify' -> tidak boleh .enc
          'decrypt'             -> hanya boleh .enc
    """
    filename = file.filename.lower()
    if mode in ('encrypt', 'verify'):
        if filename.endswith('.enc'):
            raise HTTPException(status_code=400, detail=f"File dengan ekstensi .enc tidak diperbolehkan untuk proses {mode}")
    elif mode == 'decrypt':
        if not filename.endswith('.enc'):
            raise HTTPException(status_code=400, detail="Hanya file dengan ekstensi .enc yang diperbolehkan untuk decrypt")
    else:
        raise HTTPException(status_code=400, detail="Mode validasi file tidak dikenali")

@router.post('/api/file/encrypt')
async def encrypt_file(
    file: UploadFile = File(...),
    username: str = Form(...),
    keyword: str = Form(...),
    background_tasks: BackgroundTasks = None,
):
    validate_file(file, mode='encrypt')
    """API untuk mengenkripsi file"""
    file_location = None
    encrypted_path = None
    try:
        # Membuat kunci pengguna berdasarkan username dan kata kunci
        user_key = encrypt_vigenere(username, keyword)

        # Menyimpan file yang diunggah secara sementara
        ensure_storage_directory()
        filename = file.filename
        file_location = os.path.join(storage_dir, f"{user_key}_{filename}")
        with open(file_location, "wb") as f:
            f.write(await file.read())

        # Membuat kunci enkripsi
        key = load_key(f"{user_key}_{filename}", mode='encrypt')

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

        # Menambahkan tugas latar belakang untuk menghapus file sementara
        background_tasks.add_task(os.remove, file_location)
        background_tasks.add_task(os.remove, encrypted_path)

        # Mengembalikan file terenkripsi sebagai respons yang dapat diunduh
        return FileResponse(
            path=encrypted_path,
            filename=f"{file.filename}.enc",
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{file.filename}.enc"'},
            background=background_tasks
        )
    except Exception as e:
        if file_location and os.path.exists(file_location):
            os.remove(file_location)
        if encrypted_path and os.path.exists(encrypted_path):
            os.remove(encrypted_path)
        raise HTTPException(
            status_code=500, detail=f"Enkripsi gagal: {str(e)}")

@router.post('/api/file/decrypt')
async def decrypt_file(
    file: UploadFile = File(...),
    username: str = Form(...),
    keyword: str = Form(...),
    background_tasks: BackgroundTasks = None,
):
    validate_file(file, mode='decrypt')
    """API untuk mendekripsi file"""
    file_location = None
    decrypted_path = None
    try:
        # Membuat kunci pengguna berdasarkan username dan kata kunci
        user_key = encrypt_vigenere(username, keyword)
        
        # Menyimpan file terenkripsi yang diunggah secara sementara
        ensure_storage_directory()
        filename = file.filename
        file_location = os.path.join(storage_dir, f"{user_key}_{filename}")
        with open(file_location, "wb") as f:
            f.write(await file.read())

        # Memuat kunci dekripsi
        key = load_key(f"{user_key}_{filename.replace('.enc', '')}", mode='decrypt')

        fernet = Fernet(key)

        # Mendekripsi file
        with open(file_location, "rb") as f:
            encrypted = f.read()
        decrypted = fernet.decrypt(encrypted)

        decrypted_path = file_location.replace(".enc", "")
        with open(decrypted_path, "wb") as f:
            f.write(decrypted)

        # Menambahkan tugas latar belakang untuk menghapus file sementara
        background_tasks.add_task(os.remove, file_location)
        background_tasks.add_task(os.remove, decrypted_path)

        # Mengembalikan file yang telah didekripsi sebagai respons yang dapat diunduh
        return FileResponse(
            path=decrypted_path,
            filename=file.filename.replace(".enc", ""),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{file.filename.replace(".enc", "")}"'},
            background=background_tasks
        )
    except Exception as e:
        if file_location and os.path.exists(file_location):
            os.remove(file_location)
        if decrypted_path and os.path.exists(decrypted_path):
            os.remove(decrypted_path)
        raise HTTPException(
            status_code=500, detail=f"Dekripsi gagal: {str(e)}")

@router.post('/api/file/verify')
async def verify_file(
    file: UploadFile = File(...),
    username: str = Form(...),
    keyword: str = Form(...),
    background_tasks: BackgroundTasks = None,
):
    validate_file(file, mode='verify')
    """API untuk memverifikasi integritas file"""
    file_location = None
    try:
        # Membuat kunci pengguna berdasarkan username dan kata kunci
        user_key = encrypt_vigenere(username, keyword)

        # Menyimpan file yang diunggah secara sementara
        ensure_storage_directory()
        filename = file.filename
        file_location = os.path.join(storage_dir, f"{user_key}_{filename}")
        with open(file_location, "wb") as f:
            f.write(await file.read())

        # Memeriksa keberadaan file hash
        hash_file = file_location + ".hash"
        if not os.path.exists(hash_file):
            if file_location and os.path.exists(file_location):
                os.remove(file_location)
            raise HTTPException(
                status_code=400, detail="File hash tidak ditemukan untuk verifikasi")

        # Membaca hash yang tersimpan
        with open(hash_file, "r") as f:
            stored_hash = f.read().strip()

        # Menghitung hash file saat ini
        current_hash = calculate_hash(file_location)

        # Menambahkan tugas latar belakang untuk menghapus file sementara
        background_tasks.add_task(os.remove, file_location)

        # Membandingkan hash yang tersimpan dengan hash saat ini
        if stored_hash == current_hash:
            return {"message": "Integritas file berhasil diverifikasi"}
        else:
            return {"message": "Verifikasi integritas file gagal"}
    except Exception as e:
        if file_location and os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(
            status_code=500, detail=f"Verifikasi gagal: {str(e)}")