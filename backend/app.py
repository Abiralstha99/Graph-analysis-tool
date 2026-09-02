from fastapi import FastAPI, UploadFile, File, Form, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List
import os
import zipfile
import tempfile
import shutil
import secrets
import bcrypt
from mysql.connector import IntegrityError

from .config import Settings
from .database import get_db_connection
from .utils.plotter import generate_and_save, SAVE_DIR
from .graph_analysis import router as analysis_router
from .chatbox import router as chat_router

app = FastAPI(title="MRG Labs Graphing API")

# Include routers for new services
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
from starlette.middleware.sessions import SessionMiddleware

SESSION_SECRET = Settings.from_environment().session_secret or secrets.token_urlsafe(32)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

# Static mounting for generated graphs
static_root = os.path.join(os.path.dirname(__file__), 'static')
app.mount("/static", StaticFiles(directory=static_root), name="static")


def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


async def get_current_user_id(request: Request) -> int:
    user_id = request.session.get('user_id')
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')
    return int(user_id)


from pydantic import BaseModel


class UserAuth(BaseModel):
    username: str
    password: str


@app.post('/register')
def register(payload: UserAuth):
    username = payload.username.strip()
    password = payload.password
    if not username or not password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='username and password required')

    hashed = hash_password(password)
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, hashed)
        )
        conn.commit()
        return {"status": "ok", "username": username}
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='username already exists')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


@app.post('/login')
def login(payload: UserAuth, request: Request):
    username = payload.username.strip()
    password = payload.password
    if not username or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='username and password required')

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, password FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='invalid credentials')

        if not verify_password(password, row['password']):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='invalid credentials')

        # Set session
        request.session['user_id'] = int(row['id'])
        return {"status": "ok", "user_id": row['id']}
    finally:
        if conn:
            conn.close()


@app.post('/logout')
def logout(request: Request):
    request.session.clear()
    return {"status": "ok"}


class ChangePasswordPayload(BaseModel):
    current_password: str
    new_password: str


@app.post('/change_password')
def change_password(payload: ChangePasswordPayload, user_id: int = Depends(get_current_user_id)):
    current_password = payload.current_password
    new_password = payload.new_password
    
    if not current_password or not new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Both current and new passwords are required')
    
    if len(new_password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='New password must be at least 6 characters')
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Get current user's password hash
        cur.execute("SELECT password FROM users WHERE id = %s", (int(user_id),))
        row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
        
        # Verify current password
        if not verify_password(current_password, row['password']):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Current password is incorrect')
        
        # Hash new password and update
        new_hashed = hash_password(new_password)
        cur.execute("UPDATE users SET password = %s WHERE id = %s", (new_hashed, int(user_id)))
        conn.commit()
        
        return {"status": "ok", "message": "Password updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

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
        
#         # Create a temporary zip file
#         with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
#             with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
#                 for relative_path in saved_paths:
#                     # Convert relative path to absolute path
#                     if relative_path.startswith('/static/generated_graphs/'):
#                         file_path = os.path.join(SAVE_DIR, relative_path.replace('/static/generated_graphs/', ''))
#                     else:
#                         file_path = os.path.join(SAVE_DIR, os.path.basename(relative_path))
                    
#                     if os.path.exists(file_path):
#                         # Add file to zip with just the filename (no directories)
#                         zip_file.write(file_path, os.path.basename(file_path))
            
#             # Return the zip file as a download
#             def cleanup_file():
#                 try:
#                     os.unlink(temp_zip.name)
#                 except:
#                     pass
            
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
