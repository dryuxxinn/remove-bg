import os
import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from rembg import remove, new_session

app = FastAPI(
    title="Background and Object Remover API",
    description="API untuk menghapus background, object masking, dan Magic Eraser berbasis rembg dan OpenCV",
    version="1.2.0"
)

# Konfigurasi CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Batas ukuran file (20 MB)
MAX_FILE_SIZE = 20 * 1024 * 1024

# --- INIT MODEL RINGAN (ANTI OOM) ---
# Menggunakan model 'silueta' yang ukurannya kecil dan sangat hemat RAM (~43MB)
my_session = new_session("silueta")


def validate_file_size(file_bytes: bytes):
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Ukuran file terlalu besar! Maksimal {MAX_FILE_SIZE // (1024 * 1024)}MB."
        )


def decode_image_to_bgra(image_bytes: bytes) -> np.ndarray:
    """Decode byte gambar ke format BGRA dengan mempertahankan channel alpha jika sudah ada."""
    validate_file_size(image_bytes)
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
    
    if img is None:
        raise HTTPException(status_code=400, detail="File gambar rusak atau format tidak didukung.")
    
    if len(img.shape) == 2:  # Grayscale
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
    elif img.shape[2] == 3:  # BGR
        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    elif img.shape[2] == 4:
        pass  # Sudah BGRA
    else:
        raise HTTPException(status_code=400, detail="Format channel citra tidak didukung.")
        
    return img


@app.get("/")
def serve_index():
    """Melayani antarmuka web index.html langsung dari backend."""
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="File index.html tidak ditemukan.")


@app.post("/remove-bg/")
def remove_background(file: UploadFile = File(...)):
    """Menghapus background subjek utama secara otomatis menggunakan rembg."""
    input_image = file.file.read()
    validate_file_size(input_image)
    
    try:
        output_image = remove(input_image, session=my_session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memproses gambar: {str(e)}")
        
    return Response(content=output_image, media_type="image/png")


@app.post("/remove-object-auto/")
def remove_object_auto(file: UploadFile = File(...)):
    """Membuang subjek objek utama dan mengekstrak latar/background saja."""
    input_image = file.file.read()
    img = decode_image_to_bgra(input_image)

    try:
        mask_bytes = remove(input_image, only_mask=True, session=my_session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mendeteksi mask objek: {str(e)}")

    nparr_mask = np.frombuffer(mask_bytes, np.uint8)
    mask = cv2.imdecode(nparr_mask, cv2.IMREAD_GRAYSCALE)
    if mask is None:
        raise HTTPException(status_code=500, detail="Gagal mengurai mask hasil segmentasi.")

    mask = cv2.resize(mask, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
    img[mask > 127, 3] = 0

    success, buffer = cv2.imencode('.png', img)
    if not success:
        raise HTTPException(status_code=500, detail="Gagal mengonversi hasil ke format PNG.")

    return Response(content=buffer.tobytes(), media_type="image/png")


@app.post("/magic-eraser/")
def magic_eraser(image: UploadFile = File(...), mask: UploadFile = File(...)):
    """Melubangi area bertopeng (mask shape) menjadi transparan murni."""
    img_bytes = image.file.read()
    mask_bytes = mask.file.read()

    img = decode_image_to_bgra(img_bytes)
    validate_file_size(mask_bytes)

    nparr_mask = np.frombuffer(mask_bytes, np.uint8)
    mask_cv = cv2.imdecode(nparr_mask, cv2.IMREAD_GRAYSCALE)
    if mask_cv is None:
        raise HTTPException(status_code=400, detail="Format mask tidak valid.")

    mask_cv = cv2.resize(mask_cv, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
    img[mask_cv > 127, 3] = 0

    success, buffer = cv2.imencode('.png', img)
    if not success:
        raise HTTPException(status_code=500, detail="Gagal mengonversi hasil ke format PNG.")

    return Response(content=buffer.tobytes(), media_type="image/png")


@app.post("/magic-color-eraser/")
def magic_color_eraser(
    image: UploadFile = File(...),
    x: int = Form(...),
    y: int = Form(...),
    tolerance: int = Form(32),
    contiguous: bool = Form(True)
):
    """
    Magic Eraser ala Photoshop (Color Tolerance + Flood Fill):
    Menghapus area warna tertentu berdasarkan titik klik (x, y) dan toleransi menjadi transparan.
    - contiguous=True : Hanya menghapus warna serupa yang terhubung langsung dari titik klik.
    - contiguous=False: Menghapus semua warna serupa di seluruh gambar.
    """
    img_bytes = image.file.read()
    img = decode_image_to_bgra(img_bytes)

    h, w = img.shape[:2]
    if x < 0 or x >= w or y < 0 or y >= h:
        raise HTTPException(status_code=400, detail=f"Koordinat ({x}, {y}) di luar batas gambar ({w}x{h}).")

    # Jika titik yang diklik sudah transparan (alpha = 0), tidak perlu diproses
    if img[y, x, 3] == 0:
        success, buffer = cv2.imencode('.png', img)
        return Response(content=buffer.tobytes(), media_type="image/png")

    # Batasi toleransi antara 0 s.d 255
    tolerance = max(0, min(255, tolerance))

    if contiguous:
        # Gunakan floodFill pada channel BGR dengan mask
        mask = np.zeros((h + 2, w + 2), dtype=np.uint8)
        bgr = img[:, :, :3].copy()
        
        cv2.floodFill(
            bgr,
            mask,
            seedPoint=(x, y),
            newVal=(0, 0, 0),
            loDiff=(tolerance, tolerance, tolerance),
            upDiff=(tolerance, tolerance, tolerance),
            flags=4 | (255 << 8) | cv2.FLOODFILL_MASK_ONLY
        )
        # Area yang ter-floodfill ditandai 255 pada mask[1:h+1, 1:w+1]
        flooded_region = (mask[1:h + 1, 1:w + 1] == 255)
        img[flooded_region, 3] = 0
    else:
        # Mode Non-Contiguous: cari semua piksel yang selisih warnanya <= tolerance
        target_color = img[y, x, :3].astype(np.int16)
        diff = np.abs(img[:, :, :3].astype(np.int16) - target_color)
        matched_pixels = np.all(diff <= tolerance, axis=2)
        img[matched_pixels, 3] = 0

    success, buffer = cv2.imencode('.png', img)
    if not success:
        raise HTTPException(status_code=500, detail="Gagal mengonversi hasil ke format PNG.")

    return Response(content=buffer.tobytes(), media_type="image/png")
