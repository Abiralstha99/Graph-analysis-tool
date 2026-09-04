from fastapi import FastAPI, UploadFile, File, Form, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List
import os
import zipfile
import tempfile

from .auth import configure_session_middleware, get_current_user_id, router as auth_router
from .database import get_db_connection
from .utils.plotter import generate_and_save, SAVE_DIR
from .graph_analysis import router as analysis_router
from .chatbox import router as chat_router
from .schemas.error import ErrorResponse, ErrorDetail

app = FastAPI(title="MRG Labs Graphing API")

# Include routers for new services
app.include_router(auth_router)
app.include_router(analysis_router)
app.include_router(chat_router)

# CORS (dev: allow localhost frontend)
# IMPORTANT: Cannot use wildcard "*" when allow_credentials=True
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware for simple server-side sessions
configure_session_middleware(app)

# Static mounting for generated graphs
static_root = os.path.join(os.path.dirname(__file__), 'static')
app.mount("/static", StaticFiles(directory=static_root), name="static")


# Global exception handler for HTTPException
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Convert HTTPException to canonical error response format."""
    # Extract code from detail if provided as "CODE:message", else use a default
    detail = exc.detail or "An error occurred"
    code = "INTERNAL_ERROR"
    message = detail
    
    # Try to parse code from detail string (format: "CODE:message")
    if isinstance(detail, str) and ":" in detail:
        parts = detail.split(":", 1)
        code = parts[0].strip()
        message = parts[1].strip()
    
    # Map HTTP status codes to error codes if not explicitly provided
    if code == "INTERNAL_ERROR":
        status_code_to_code = {
            status.HTTP_400_BAD_REQUEST: "VALIDATION_ERROR",
            status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
            status.HTTP_403_FORBIDDEN: "FORBIDDEN",
            status.HTTP_404_NOT_FOUND: "NOT_FOUND",
            status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
            status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_ERROR",
        }
        code = status_code_to_code.get(exc.status_code, "INTERNAL_ERROR")
    
    error_response = ErrorResponse(
        error=ErrorDetail(code=code, message=message, details={})
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
    )


# @app.post("/generate_graphs")
# async def generate_graphs(
#     baseline: UploadFile = File(...),
#     samples: List[UploadFile] = File(...),
#     save_dir: str | None = Form(None),
#     format: str = Form("png"),
#     user_id: int = Depends(get_current_user_id)
# ):
#     try:
#         # Generate the graphs and get their file paths
#         saved_paths = generate_and_save(baseline, samples, save_subdir=save_dir, format=format)
#         # Persist graph metadata for each generated file
#         try:
#             conn = get_db_connection()
#             cur = conn.cursor()
#             for rel_path, sample in zip(saved_paths, samples):
#                 # baseline.filename, sample.filename, generated_path
#                 cur.execute(
#                     "INSERT INTO graphs (user_id, baseline_filename, sample_filename, generated_path) VALUES (%s, %s, %s, %s)",
#                     (int(user_id), getattr(baseline, 'filename', None), getattr(sample, 'filename', None), rel_path)
#                 )
#             conn.commit()
#         except Exception as e:
#             # don't block the response if DB logging fails; include a warning in the response
#             # (could be improved to log)
#             print('Failed to insert graph record:', e)
#         finally:
#             try:
#                 if conn:
#                     conn.close()
#             except Exception:
#                 pass
#         
#         # Create a temporary zip file
#         with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
#             with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
#                 for relative_path in saved_paths:
#                     # Convert relative path to absolute path
#                     if relative_path.startswith('/static/generated_graphs/'):
#                         file_path = os.path.join(SAVE_DIR, relative_path.replace('/static/generated_graphs/', ''))
#                     else:
#                         file_path = os.path.join(SAVE_DIR, os.path.basename(relative_path))
#                     
#                     if os.path.exists(file_path):
#                         # Add file to zip with just the filename (no directories)
#                         zip_file.write(file_path, os.path.basename(file_path))
#             
#             # Return the zip file as a download
#             def cleanup_file():
#                 try:
#                     os.unlink(temp_zip.name)
#                 except:
#                     pass
#             
#             return FileResponse(
#                 path=temp_zip.name,
#                 filename=f"exported_graphs.zip",
#                 media_type='application/zip',
#                 background=cleanup_file
#             )
#     except Exception as e:
#         return JSONResponse(status_code=400, content={"error": str(e)})

@app.post("/generate_graphs")
async def generate_graphs(
    baseline: UploadFile = File(...),
    samples: List[UploadFile] = File(...),
    save_dir: str | None = Form(None),
    format: str = Form("png"),
    zip_filename: str | None = Form(None)
):
    try:
        # Generate the graphs and get their file paths
        saved_paths = generate_and_save(baseline, samples, save_subdir=save_dir, format=format)
        
        # Determine the zip filename
        if zip_filename:
            # Use provided filename, ensure it ends with .zip
            final_filename = zip_filename if zip_filename.endswith('.zip') else f"{zip_filename}.zip"
        else:
            # Default to baseline name without extension
            baseline_name = os.path.splitext(baseline.filename or 'export')[0]
            final_filename = f"{baseline_name}.zip"
        
        # Create a temporary zip file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
            with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for relative_path in saved_paths:
                    # Convert relative path to absolute path
                    if relative_path.startswith('/static/generated_graphs/'):
                        file_path = os.path.join(SAVE_DIR, relative_path.replace('/static/generated_graphs/', ''))
                    else:
                        file_path = os.path.join(SAVE_DIR, os.path.basename(relative_path))
                    
                    if os.path.exists(file_path):
                        # Add file to zip with just the filename (no directories)
                        zip_file.write(file_path, os.path.basename(file_path))
            
            # Return the zip file as a download
            def cleanup_file():
                try:
                    os.unlink(temp_zip.name)
                except:
                    pass
            
            return FileResponse(
                path=temp_zip.name,
                filename=final_filename,
                media_type='application/zip',
                background=cleanup_file
            )
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
@app.get('/api/v1/files')
def list_user_files(user_id: int = Depends(get_current_user_id)):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT graph_id, baseline_filename, sample_filename, generated_path, created_at FROM graphs WHERE user_id = %s ORDER BY created_at DESC",
            (int(user_id),)
        )
        rows = cur.fetchall()
        return {"files": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@app.get("/health")
async def health():
    return {"status": "ok"}

# Run: uvicorn app:app --reload --port 8080
