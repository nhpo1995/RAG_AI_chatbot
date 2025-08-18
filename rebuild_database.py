#!/usr/bin/env python3
"""
Script để rebuild toàn bộ database từ folder data.
Xóa hết vectors cũ và add lại từ đầu.
"""

import sys
from pathlib import Path
# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

import config
from services.db_service import DBService
import logging
from utils.logger import setup_colored_logger

setup_colored_logger()
logger = logging.getLogger(__name__)

def main():
    """
    Main function để rebuild database.
    """
    db_service = DBService()
    
    # Option 1: Rebuild từ folder (recommended)
    print("🔄 Đang rebuild database từ folder...")
    result = db_service.rebuild_database_from_folder(config.DATA_PATH)
    
    if result:
        total_files = len(result)
        total_chunks = sum(len(docs) for docs in result.values())
        print(f"✅ Rebuild thành công!")
        print(f"📁 Files processed: {total_files}")
        print(f"🔗 Total chunks: {total_chunks}")
        
        # In danh sách files
        print("\n📋 Danh sách files:")
        for file_source, docs in result.items():
            print(f"  - {Path(file_source).name}: {len(docs)} chunks")
    else:
        print("❌ Không có data nào được process")

    # Option 2: Chỉ xóa hết (không recommend trừ khi cần thiết)
    # print("🗑️ Đang xóa toàn bộ database...")
    # db_service.clear_all_database()
    # print("✅ Đã xóa hết vectors!")

if __name__ == "__main__":
    main()
