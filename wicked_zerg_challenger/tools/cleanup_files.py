# -*- coding: utf-8 -*-
"""
File cleanup script to reduce total file count below 1000
"""

import shutil
from pathlib import Path

def main():
    project_root = Path(__file__).parent.parent
    docs_archive = project_root / "docs" / "archive"
    docs_archive.mkdir(parents=True, exist_ok=True)
    
    # Count initial files
    initial_count = sum(1 for _ in project_root.rglob("*") if _.is_file())
    print(f"Initial file count: {initial_count}")
    
    moved_count = 0
    
    # 1. Move root-level .md files (except essential ones)
    essential_md = {
        "README.md", "README_BOT.md", "README_ko.md", 
        "README_GITHUB_UPLOAD.md", "SETUP_GUIDE.md", "LICENSE"
    }
    
    root_md_files = [f for f in project_root.glob("*.md") if f.name not in essential_md]
    for md_file in root_md_files:
        try:
            dest = docs_archive / md_file.name
            if not dest.exists():
                shutil.move(str(md_file), str(dest))
                moved_count += 1
                print(f"Moved: {md_file.name}")
        except Exception as e:
            print(f"Failed to move {md_file.name}: {e}")
    
    # 2. Move old log files (keep recent ones)
    logs_dir = project_root / "logs"
    if logs_dir.exists():
        log_files = list(logs_dir.glob("*.log"))
        if len(log_files) > 10:
            log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            for old_log in log_files[10:]:
                try:
                    old_log.unlink()
                    moved_count += 1
                except Exception:
                    pass
    
    # 3. Move telemetry files to archive
    for tel_file in project_root.glob("telemetry_*.json"):
        try:
            dest = docs_archive / tel_file.name
            if not dest.exists():
                shutil.move(str(tel_file), str(dest))
                moved_count += 1
        except Exception:
            pass
    
    for tel_file in project_root.glob("telemetry_*.csv"):
        try:
            dest = docs_archive / tel_file.name
            if not dest.exists():
                shutil.move(str(tel_file), str(dest))
                moved_count += 1
        except Exception:
            pass
    
    # 4. Move Android build files (can be regenerated)
    android_build = project_root / "monitoring" / "mobile_app_android" / "app" / "build"
    if android_build.exists():
        # Move build intermediates (can be regenerated)
        for build_file in android_build.rglob("*.flat"):
            try:
                build_file.unlink()
                moved_count += 1
            except Exception:
                pass
        
        for build_file in android_build.rglob("*.dex"):
            try:
                build_file.unlink()
                moved_count += 1
            except Exception:
                pass
        
        for build_file in android_build.rglob("*.class"):
            try:
                build_file.unlink()
                moved_count += 1
            except Exception:
                pass
    
    # 5. Move IDE configuration files (.idea)
    idea_dir = project_root / "monitoring" / ".idea"
    if idea_dir.exists():
        for xml_file in idea_dir.rglob("*.xml"):
            try:
                xml_file.unlink()
                moved_count += 1
            except Exception:
                pass
    
    # 6. Move more documentation files from subdirectories
    # Move docs from monitoring/mobile_app_android (many .md files)
    android_docs = project_root / "monitoring" / "mobile_app_android"
    if android_docs.exists():
        md_files = list(android_docs.rglob("*.md"))
        for md_file in md_files:
            try:
                rel_path = md_file.relative_to(android_docs)
                dest = docs_archive / "android_docs" / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    shutil.move(str(md_file), str(dest))
                    moved_count += 1
            except Exception:
                pass
    
    # 7. Move old comparison reports
    comparison_dir = project_root / "local_training" / "comparison_reports"
    if comparison_dir.exists():
        for report_file in comparison_dir.glob("*.md"):
            try:
                dest = docs_archive / "comparison_reports" / report_file.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    shutil.move(str(report_file), str(dest))
                    moved_count += 1
            except Exception:
                pass
    
    # 8. Move docs from docs/ subdirectory (keep only essential, skip archive)
    docs_dir = project_root / "docs"
    if docs_dir.exists():
        essential_docs = {
            "README.md", "API_DOCUMENTATION.md", "DESIGN_DOCUMENTS_INDEX.md"
        }
        # Skip archive directory to avoid recursion
        for item in docs_dir.iterdir():
            if item.is_dir() and item.name == "archive":
                continue
            if item.is_file() and item.suffix == ".md" and item.name not in essential_docs:
                try:
                    dest = docs_archive / "docs_backup" / item.name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if not dest.exists():
                        shutil.move(str(item), str(dest))
                        moved_count += 1
                except Exception:
                    pass
            elif item.is_dir():
                # Process subdirectories (but not archive)
                for doc_file in item.rglob("*.md"):
                    if doc_file.name not in essential_docs:
                        try:
                            rel_path = doc_file.relative_to(docs_dir)
                            dest = docs_archive / "docs_backup" / rel_path
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            if not dest.exists():
                                shutil.move(str(doc_file), str(dest))
                                moved_count += 1
                        except Exception:
                            pass
    
    # 9. Delete Android build directories entirely (can be regenerated)
    android_build_dirs = [
        project_root / "monitoring" / "mobile_app_android" / "app" / "build",
        project_root / "monitoring" / "mobile_app_android" / ".gradle",
    ]
    for build_dir in android_build_dirs:
        if build_dir.exists():
            try:
                import shutil
                shutil.rmtree(str(build_dir))
                print(f"Deleted build directory: {build_dir.relative_to(project_root)}")
            except Exception as e:
                print(f"Failed to delete {build_dir}: {e}")
    
    # 10. Count final files
    final_count = sum(1 for _ in project_root.rglob("*") if _.is_file())
    
    print(f"\n{'='*70}")
    print(f"Cleanup Summary:")
    print(f"  Initial files: {initial_count}")
    print(f"  Files moved/deleted: {moved_count}")
    print(f"  Final files: {final_count}")
    print(f"  Target: < 1000 files")
    print(f"{'='*70}")
    
    if final_count < 1000:
        print("SUCCESS: File count is below 1000!")
    else:
        print(f"Still need to reduce {final_count - 1000} more files")

if __name__ == "__main__":
    main()
