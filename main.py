from fastapi import FastAPI, File, UploadFile
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from rembg import remove, new_session
import cv2
import numpy as np

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- INIT MODEL RINGAN (ANTI OOM) ---
# Menggunakan model 'silueta' yang ukurannya kecil dan sangat hemat RAM
my_session = new_session("silueta")

@app.post("/remove-bg/")
async def remove_background(file: UploadFile = File(...)):
    input_image = await file.read()
    
    # Memasukkan session ke dalam proses remove
    output_image = remove(input_image, session=my_session)
    
    return Response(content=output_image, media_type="image/png")

@app.post("/remove-object-auto/")
async def remove_object_auto(file: UploadFile = File(...)):
    input_image = await file.read()
    
    # Memasukkan session ke dalam proses pembentukan mask
    mask_bytes = remove(input_image, only_mask=True, session=my_session)
    
    nparr_img = np.frombuffer(input_image, np.uint8)
    img = cv2.imdecode(nparr_img, cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA) 
    
    nparr_mask = np.frombuffer(mask_bytes, np.uint8)
    mask = cv2.imdecode(nparr_mask, cv2.IMREAD_GRAYSCALE)
    mask = cv2.resize(mask, (img.shape[1], img.shape[0]))
    
    img[mask > 127, 3] = 0
    
    _, buffer = cv2.imencode('.png', img)
    return Response(content=buffer.tobytes(), media_type="image/png")

@app.post("/magic-eraser/")
async def magic_eraser(image: UploadFile = File(...), mask: UploadFile = File(...)):
    # Fungsi ini murni pakai OpenCV, tidak pakai rembg, jadi tidak perlu diubah
    img_bytes = await image.read()
    mask_bytes = await mask.read()

    nparr_img = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr_img, cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)

    nparr_mask = np.frombuffer(mask_bytes, np.uint8)
    mask_cv = cv2.imdecode(nparr_mask, cv2.IMREAD_GRAYSCALE) 
    mask_cv = cv2.resize(mask_cv, (img.shape[1], img.shape[0]))

    img[mask_cv > 0, 3] = 0

    _, buffer = cv2.imencode('.png', img)
    return Response(content=buffer.tobytes(), media_type="image/png")