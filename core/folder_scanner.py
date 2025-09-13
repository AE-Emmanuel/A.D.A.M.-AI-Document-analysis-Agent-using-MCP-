import asyncio
import os
import time
from pathlib import Path
from typing import Set, Dict, Optional, Callable
from dataclasses import dataclass
import threading
from queue import Queue, Empty


@dataclass
class FolderInfo:
    """Information about a discovered folder"""
    path: Path
    name: str
    file_count: int
    supported_files: list[str]
    last_modified: float
    is_project: bool = False


class AutoFolderScanner:
    """Automatically scans for folders and requests user permission to add them"""
    
    def __init__(self, 
                 scan_interval: int = 30,  # seconds
                 supported_extensions: tuple = ('.py', '.md', '.txt', '.json', '.js', '.html', '.css'),
                 project_markers: tuple = ('package.json', 'pyproject.toml', 'requirements.txt', 'Cargo.toml', 'go.mod', 'pom.xml', 'build.gradle', '.git'),
                 on_folder_discovered: Optional[Callable] = None):
        self.scan_interval = scan_interval
        self.supported_extensions = supported_extensions
        self.project_markers = project_markers
        self.on_folder_discovered = on_folder_discovered
        
        self.known_folders: Set[Path] = set()
        self.scanning = False
        self.scan_thread: Optional[threading.Thread] = None
        self.discovery_queue: Queue = Queue()
        
        # Common directories to scan
        self.scan_paths = [
            Path.home() / "Documents",
            Path.home() / "Desktop", 
            Path.home() / "Projects",
            Path.home() / "Code",
            Path.home() / "Development",
            Path.cwd(),  # Current working directory
        ]
        
        # Add common development directories (simplified - no recursive adding during init)
        # The recursive scanning will happen during the actual scan process
    
    def _add_scan_paths(self, base_path: Path, max_depth: int = 3, current_depth: int = 0):
        """Recursively add paths to scan, up to max_depth"""
        if current_depth >= max_depth:
            return
            
        try:
            for item in base_path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    self.scan_paths.append(item)
                    if current_depth < max_depth - 1:
                        self._add_scan_paths(item, max_depth, current_depth + 1)
        except (PermissionError, OSError):
            pass  # Skip directories we can't access
    
    def _is_project_folder(self, folder_path: Path) -> bool:
        """Check if a folder looks like a project based on markers"""
        for marker in self.project_markers:
            if (folder_path / marker).exists():
                return True
        return False
    
    def _analyze_folder(self, folder_path: Path) -> Optional[FolderInfo]:
        """Analyze a folder and return its information"""
        try:
            if not folder_path.is_dir() or folder_path in self.known_folders:
                return None
                
            # Count files and find supported ones
            supported_files = []
            file_count = 0
            
            for item in folder_path.rglob('*'):
                if item.is_file():
                    file_count += 1
                    if item.suffix.lower() in self.supported_extensions:
                        supported_files.append(item.name)
            
            # Skip if no supported files
            if not supported_files:
                return None
                
            # Get last modified time
            last_modified = max(
                (item.stat().st_mtime for item in folder_path.rglob('*') if item.is_file()),
                default=0
            )
            
            return FolderInfo(
                path=folder_path,
                name=folder_path.name,
                file_count=file_count,
                supported_files=supported_files[:10],  # Limit to first 10
                last_modified=last_modified,
                is_project=self._is_project_folder(folder_path)
            )
            
        except (PermissionError, OSError):
            return None
    
    def _scan_folders(self):
        """Scan for new folders in a separate thread"""
        print("🔍 Folder scanner thread started")
        scan_count = 0
        
        while self.scanning:
            try:
                scan_count += 1
                new_folders = []
                
                # Limit the number of paths to scan to avoid performance issues
                paths_to_scan = self.scan_paths[:10]  # Only scan first 10 paths
                
                for scan_path in paths_to_scan:
                    if not scan_path.exists():
                        continue
                        
                    try:
                        # Look for immediate subdirectories only (no deep recursion)
                        items = list(scan_path.iterdir())
                        for item in items[:20]:  # Limit to first 20 items per directory
                            if item.is_dir() and not item.name.startswith('.'):
                                folder_info = self._analyze_folder(item)
                                if folder_info and folder_info.path not in self.known_folders:
                                    new_folders.append(folder_info)
                                    self.known_folders.add(folder_info.path)
                                    print(f"🎯 Found new folder: {folder_info.name} at {folder_info.path}")
                    except (PermissionError, OSError) as e:
                        continue
                
                # Add discovered folders to queue
                for folder_info in new_folders:
                    self.discovery_queue.put(folder_info)
                
                if scan_count % 4 == 0:  # Print status every 4 scans
                    print(f"🔍 Scan #{scan_count}: {len(self.known_folders)} known folders, {len(new_folders)} new")
                
                time.sleep(self.scan_interval)
                
            except Exception as e:
                print(f"Error in folder scanner: {e}")
                time.sleep(self.scan_interval)
    
    def start_scanning(self):
        """Start the background folder scanning"""
        if self.scanning:
            print("⚠️ Auto folder scanning already running")
            return
            
        self.scanning = True
        self.scan_thread = threading.Thread(target=self._scan_folders, daemon=True)
        self.scan_thread.start()
        print("🔍 Auto folder scanning started...")
        print(f"   📂 Scanning {len(self.scan_paths)} directories")
        print(f"   ⏱️ Scan interval: {self.scan_interval} seconds")
    
    def stop_scanning(self):
        """Stop the background folder scanning"""
        self.scanning = False
        if self.scan_thread:
            self.scan_thread.join(timeout=1)
        print("🛑 Auto folder scanning stopped")
    
    def get_discovered_folders(self) -> list[FolderInfo]:
        """Get all newly discovered folders and clear the queue"""
        folders = []
        try:
            while True:
                folder = self.discovery_queue.get_nowait()
                folders.append(folder)
        except Empty:
            pass
        return folders
    
    def add_scan_path(self, path: Path):
        """Add a new path to scan"""
        if path.exists() and path.is_dir():
            self.scan_paths.append(path)
            # Also scan this path immediately
            for item in path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    folder_info = self._analyze_folder(item)
                    if folder_info and folder_info.path not in self.known_folders:
                        self.discovery_queue.put(folder_info)
                        self.known_folders.add(folder_info.path)
