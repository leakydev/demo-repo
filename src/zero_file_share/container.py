import tarfile
import tempfile
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
import base64
from military_crypto_lib.military_crypto import MilitaryCrypto
import traceback

class SecureContainer:
    def __init__(self, container_path: str):
        self.container_path = Path(container_path)
        self.crypto = MilitaryCrypto()
        self.temp_dir: Optional[Path] = None
        self.is_mounted = False
        
    def create_empty(self, key: str) -> None:
        with tempfile.NamedTemporaryFile() as temp_tar:
            with tarfile.open(temp_tar.name, 'w') as tar:
                pass
            
            with open(temp_tar.name, 'rb') as f:
                tar_data = f.read()
            
            encrypted_data = self.crypto.encrypt(tar_data, key)
            
            with open(self.container_path, 'w') as f:
                f.write(encrypted_data)
    
    def mount(self, key: str) -> Path:
        if self.is_mounted:
            raise RuntimeError("Container is already mounted")
        
        try:
            with open(self.container_path, 'r') as f:
                encrypted_data = f.read()
            
            tar_data = self.crypto.decrypt(encrypted_data, key)
            
            self.temp_dir = Path(tempfile.mkdtemp(prefix="zero_file_share_"))
            
            with tempfile.NamedTemporaryFile() as temp_tar:
                temp_tar.write(tar_data)
                temp_tar.flush()
                
                with tarfile.open(temp_tar.name, 'r') as tar:
                    tar.extractall(self.temp_dir)
            
            self.is_mounted = True
            return self.temp_dir
            
        except Exception as e:
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            print(traceback.format_exc())
            raise RuntimeError(f"Failed to mount container: {e}")
    
    def save(self, key: str) -> None:
        if not self.is_mounted:
            raise RuntimeError("Container is not mounted")
        
        with tempfile.NamedTemporaryFile() as temp_tar:
            with tarfile.open(temp_tar.name, 'w') as tar:
                for root, dirs, files in os.walk(self.temp_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(self.temp_dir)
                        tar.add(file_path, arcname=arcname)
            
            with open(temp_tar.name, 'rb') as f:
                tar_data = f.read()
            
            encrypted_data = self.crypto.encrypt(tar_data, key)
            
            with open(self.container_path, 'w') as f:
                f.write(encrypted_data)
    
    def unmount(self) -> None:
        if not self.is_mounted:
            return
        
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        
        self.temp_dir = None
        self.is_mounted = False
    
    def add_file(self, file_path: str, key: str, target_path: Optional[str] = None) -> None:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        was_mounted = self.is_mounted
        if not was_mounted:
            self.mount(key)
        
        try:
            if target_path:
                dest_path = self.temp_dir / target_path
            else:
                dest_path = self.temp_dir / file_path.name
            
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, dest_path)
            
            self.save(key)
            
        finally:
            if not was_mounted:
                self.unmount()
    
    def list_files(self) -> list:
        if not self.is_mounted:
            raise RuntimeError("Container is not mounted")
        
        files = []
        for root, dirs, filenames in os.walk(self.temp_dir):
            for filename in filenames:
                file_path = Path(root) / filename
                rel_path = file_path.relative_to(self.temp_dir)
                files.append(str(rel_path))
        
        return sorted(files)
    
    def get_mount_path(self) -> Optional[Path]:
        return self.temp_dir if self.is_mounted else None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unmount()