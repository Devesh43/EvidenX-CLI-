#!/usr/bin/env python3
"""
WhatsApp Data Extractor - VS Code Only Version with Media Extraction
Extracts WhatsApp data and creates JSON files + media folder in your workspace
No web interface required - pure JSON output + media files
"""

import os
import sqlite3
import tempfile
import shutil
from datetime import datetime
import pyzipper
import subprocess
import traceback
import json
from pathlib import Path

class WhatsAppDataExtractor:
    def __init__(self, root_folder_path):
        self.root_folder_path = root_folder_path
        self.output_dir = Path("whatsapp_data_output")
        self.media_dir = Path("media")
        self.media_paths_dir = Path("media_paths")
        self.contacts_map = {}
        self.group_participants = {}
        self.chat_data = {}
        self.chat_list = []
        self.call_logs = []
        self.media_index = {}
        self.extracted_media = []
        self.media_path_mapping = {}
        
        # Media file extensions (from Flask version)
        self.MEDIA_EXTENSIONS = [
            ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
            ".mp4", ".webm", ".ogg", ".3gp", ".mov", ".avi", ".mkv",
            ".mp3", ".wav", ".m4a", ".aac", ".opus", ".amr", ".oga", ".ptt",
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
            ".vcf", ".zip", ".rar", ".7z", ".txt", ".csv", ".apk"
        ]
        
        # Create output directories
        self.output_dir.mkdir(exist_ok=True)
        self.media_dir.mkdir(exist_ok=True)
        self.media_paths_dir.mkdir(exist_ok=True)
        
        print(f" Output directory: {self.output_dir.absolute()}")
        print(f" Media directory: {self.media_dir.absolute()}")
        print(f" Media paths directory: {self.media_paths_dir.absolute()}")

    def find_zip_file(self):
        """Find the WhatsApp backup ZIP file"""
        print("Searching for WhatsApp backup ZIP file...")
        
        for root, dirs, files in os.walk(self.root_folder_path):
            for file in files:
                if file.lower().endswith('.zip'):
                    zip_path = os.path.join(root, file)
                    print(f" Found the ZIP file: {zip_path}")
                    return zip_path
        
        raise FileNotFoundError(" No .zip file found in the provided folder")

    def find_in_zip(self, zipf, name_contains):
        """Find file in ZIP archive by name pattern"""
        for info in zipf.infolist():
            if name_contains.lower() in info.filename.lower():
                return info
        return None

    def extract_file_from_zip(self, zipf, info, temp_dir):
        """Extract a file from ZIP to temporary directory"""
        out_path = os.path.join(temp_dir, os.path.basename(info.filename))
        with zipf.open(info) as src, open(out_path, 'wb') as dst:
            shutil.copyfileobj(src, dst)
        return out_path

    def build_media_index(self, zipf):
        """Build index of all media files in ZIP (from Flask version)"""
        print(" Building media index from ZIP file...")
        
        index = {}
        for info in zipf.infolist():
            base = os.path.basename(info.filename)
            if base and base not in index:
                index[base] = info.filename
        
        print(f" Built media index with {len(index)} files")
        return index

    def get_media_files_from_zip(self, zipf):
        """Extract all media files information from the ZIP (from Flask version)"""
        print(" Scanning for media files in ZIP...")
        
        media_files = []
        
        for info in zipf.infolist():
            if info.is_dir():
                continue
                
            filename = os.path.basename(info.filename)
            if not filename:
                continue
                
            # Check if it's a media file
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in self.MEDIA_EXTENSIONS:
                # Get file size
                file_size = info.file_size
                
                # Get modification date
                try:
                    mod_date = datetime(*info.date_time)
                except:
                    mod_date = datetime.now()
                
                # Determine media type
                media_type = "Unknown"
                if file_ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]:
                    media_type = "Image"
                elif file_ext in [".mp4", ".webm", ".ogg", ".3gp", ".mov", ".avi", ".mkv"]:
                    media_type = "Video"
                elif file_ext in [".mp3", ".wav", ".m4a", ".aac", ".opus", ".amr", ".oga", ".ptt"]:
                    media_type = "Audio"
                elif file_ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"]:
                    media_type = "Document"
                elif file_ext in [".zip", ".rar", ".7z"]:
                    media_type = "Archive"
                elif file_ext in [".txt", ".csv"]:
                    media_type = "Text"
                elif file_ext == ".vcf":
                    media_type = "Contact"
                elif file_ext == ".apk":
                    media_type = "App"
                
                media_files.append({
                    'filename': filename,
                    'path_in_zip': info.filename,
                    'size': file_size,
                    'size_formatted': self.format_file_size(file_size),
                    'date': mod_date.isoformat(),
                    'date_formatted': mod_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'type': media_type,
                    'extension': file_ext
                })
        
        # Sort by date (newest first)
        media_files.sort(key=lambda x: x['date'], reverse=True)
        print(f"Found {len(media_files)} media files")
        return media_files

    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"

    def extract_media_from_zip(self, zipf, media_files):
        """Extract all media files from ZIP to local media folder"""
        print(" Extracting media files to local folder...")
        
        extracted_count = 0
        failed_count = 0
        
        for media_file in media_files:
            try:
                # Create safe filename
                safe_filename = media_file['filename'].replace(":", "_").replace("/", "_").replace("\\", "_")
                dest_path = self.media_dir / safe_filename
                
                # Skip if already exists
                if dest_path.exists():
                    print(f" Skipping existing file: {safe_filename}")
                    continue
                
                # Extract file from ZIP
                with zipf.open(media_file['path_in_zip']) as src:
                    with open(dest_path, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                
                # Store path mapping
                self.media_path_mapping[media_file['filename']] = {
                    'original_path_in_zip': media_file['path_in_zip'],
                    'extracted_path': str(dest_path),
                    'safe_filename': safe_filename,
                    'size': media_file['size'],
                    'type': media_file['type'],
                    'date': media_file['date']
                }
                
                extracted_count += 1
                
                if extracted_count % 50 == 0:
                    print(f" Extracted {extracted_count} files...")
                
            except Exception as e:
                print(f" Failed to extract {media_file['filename']}: {e}")
                failed_count += 1
                continue
        
        print(f" Media extraction complete: {extracted_count} extracted, {failed_count} failed")
        return extracted_count

    def find_media_in_row(self, row, colnames):
        """Find media files referenced in database row"""
        for col, val in zip(colnames, row):
            if not isinstance(val, str):
                continue
            val_strip = val.strip()
            for ext in self.MEDIA_EXTENSIONS:
                if val_strip.lower().endswith(ext):
                    media_basename = os.path.basename(val_strip)
                    if media_basename in self.media_index:
                        return media_basename
        return None

    def save_media_path_mappings(self):
        """Save media path mappings to separate files"""
        print(" Saving media path mappings...")
        
        # 1. Complete media mapping file
        media_mapping_file = self.media_paths_dir / "media_path_mapping.json"
        mapping_data = {
            "export_date": datetime.now().isoformat(),
            "total_media_files": len(self.media_path_mapping),
            "media_directory": str(self.media_dir.absolute()),
            "mappings": self.media_path_mapping
        }
        
        with open(media_mapping_file, 'w', encoding='utf-8') as f:
            json.dump(mapping_data, f, indent=2, ensure_ascii=False)
        print(f" Media mapping saved: {media_mapping_file}")
        
        # 2. Simple path list file - UPDATED to show full original paths
        path_list_file = self.media_paths_dir / "extracted_media_paths.txt"
        with open(path_list_file, 'w', encoding='utf-8') as f:
            f.write(f"WhatsApp Media Files - Extracted on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            for original_name, info in self.media_path_mapping.items():
                # Show the full original path from ZIP (like in the image)
                full_original_path = info['original_path_in_zip']
                
                f.write(f"Original ZIP Path: {full_original_path}\n")
                f.write(f"Filename: {original_name}\n")
                f.write(f"Local Path: {info['extracted_path']}\n")
                f.write(f"Size: {self.format_file_size(info['size'])}\n")
                f.write(f"Type: {info['type']}\n")
                f.write(f"Date: {info['date']}\n")
                f.write("-" * 60 + "\n")
        
        print(f" Path list saved: {path_list_file}")
        
        # 3. Media by type files - UPDATED to include full original paths
        media_by_type = {}
        for filename, info in self.media_path_mapping.items():
            media_type = info['type']
            if media_type not in media_by_type:
                media_by_type[media_type] = []
            media_by_type[media_type].append({
                'filename': filename,
                'original_zip_path': info['original_path_in_zip'],  # ADD full original path
                'local_path': info['extracted_path'],
                'size': info['size'],
                'date': info['date']
            })

        for media_type, files in media_by_type.items():
            type_file = self.media_paths_dir / f"{media_type.lower()}_files.json"
            type_data = {
                "media_type": media_type,
                "total_files": len(files),
                "files": files,
                "export_date": datetime.now().isoformat()
            }
            
            with open(type_file, 'w', encoding='utf-8') as f:
                json.dump(type_data, f, indent=2, ensure_ascii=False)
        
        print(f" Media type files saved in: {self.media_paths_dir}")

        # 4. NEW: Full directory structure file showing original ZIP paths
        directory_structure_file = self.media_paths_dir / "original_directory_structure.txt"
        with open(directory_structure_file, 'w', encoding='utf-8') as f:
            f.write(f"WhatsApp Backup - Original Directory Structure\n")
            f.write(f"Extracted on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            # Group files by their directory structure
            directory_tree = {}
            for filename, info in self.media_path_mapping.items():
                full_path = info['original_path_in_zip']
                directory = os.path.dirname(full_path)
                
                if directory not in directory_tree:
                    directory_tree[directory] = []
                directory_tree[directory].append({
                    'filename': os.path.basename(full_path),
                    'size': self.format_file_size(info['size']),
                    'type': info['type']
                })
            
            # Sort directories and display tree structure
            for directory in sorted(directory_tree.keys()):
                f.write(f" {directory}/\n")
                for file_info in sorted(directory_tree[directory], key=lambda x: x['filename']):
                    f.write(f"    {file_info['filename']} ({file_info['size']}) [{file_info['type']}]\n")
                f.write("\n")

        print(f" Directory structure saved: {directory_structure_file}")

    def decrypt_database(self, key_file, encrypted_db, output_db='msgstore.db'):
        """Decrypt WhatsApp database using wadecrypt"""
        cmd = ['wadecrypt', key_file, encrypted_db, output_db]
        print(f" Decrypting database: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f" Decryption failed: {result.stderr}")
        
        print(" Database decrypted successfully")
        return output_db

    def parse_contacts_db(self, contacts_db_path):
        """Extract contacts from contacts database"""
        print(" Parsing contacts database...")
        
        contacts = {}
        try:
            conn = sqlite3.connect(contacts_db_path)
            cursor = conn.cursor()
            
            # Try different table structures
            queries = [
                """SELECT data1, display_name FROM view_data 
                   WHERE mimetype_id = (SELECT _id FROM mimetype WHERE mimetype = 'vnd.android.cursor.item/phone_v2')""",
                """SELECT data1, display_name FROM data 
                   JOIN raw_contacts ON data.raw_contact_id = raw_contacts._id 
                   WHERE data.mimetype_id = (SELECT _id FROM mimetype WHERE mimetype = 'vnd.android.cursor.item/phone_v2')""",
                """SELECT data1, display_name FROM data 
                   LEFT JOIN raw_contacts ON data.raw_contact_id = raw_contacts._id 
                   WHERE data1 IS NOT NULL AND display_name IS NOT NULL"""
            ]
            
            for query in queries:
                try:
                    cursor.execute(query)
                    for number, name in cursor.fetchall():
                        if number:
                            norm = ''.join(filter(str.isdigit, number))
                            if len(norm) > 8:
                                contacts[norm[-10:]] = name or number
                    break
                except Exception as e:
                    continue
            
            conn.close()
            print(f" Loaded {len(contacts)} contacts")
            
        except Exception as e:
            print(f" Error parsing contacts: {e}")
        
        return contacts

    def get_jid_map(self, conn):
        """Get JID mappings from database"""
        cursor = conn.cursor()
        cursor.execute("SELECT _id, raw_string FROM jid")
        return {row[0]: row[1] for row in cursor.fetchall()}

    def get_chat_info(self, conn, jid_map):
        """Get chat information"""
        cursor = conn.cursor()
        cursor.execute("SELECT _id, jid_row_id, subject FROM chat")
        chat_map = {}
        
        for chat_id, jid_row_id, subject in cursor.fetchall():
            jid_str = jid_map.get(jid_row_id, None)
            name = subject or jid_str or f"Chat {chat_id}"
            chat_map[chat_id] = name
        
        return chat_map

    def extract_group_participants(self, db_path, jid_map):
        """Extract group participants"""
        print(" Extracting group participants...")
        
        group_participants = {}
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get all group chats
            cursor.execute("SELECT _id, jid_row_id, subject FROM chat")
            all_chats = cursor.fetchall()
            
            group_chats = []
            for chat_id, jid_row_id, subject in all_chats:
                jid_str = jid_map.get(jid_row_id, "")
                if jid_str and '@g.us' in jid_str:
                    group_name = subject or jid_str
                    group_chats.append((chat_id, jid_row_id, group_name, jid_str))
            
            print(f" Found {len(group_chats)} groups")
            
            # Extract participants from messages
            cursor.execute("PRAGMA table_info(message)")
            msg_columns = [row[1] for row in cursor.fetchall()]
            
            chat_col = next((col for col in msg_columns if 'chat' in col.lower() and 'id' in col.lower()), None)
            sender_col = next((col for col in msg_columns if 'sender' in col.lower() and 'jid' in col.lower()), None)
            
            if chat_col and sender_col:
                for chat_id, jid_row_id, group_name, group_jid in group_chats:
                    try:
                        query = f"SELECT DISTINCT {sender_col} FROM message WHERE {chat_col} = ? AND {sender_col} IS NOT NULL"
                        cursor.execute(query, (chat_id,))
                        sender_rows = cursor.fetchall()
                        
                        participants = []
                        seen_numbers = set()
                        
                        for (sender_jid_row_id,) in sender_rows:
                            if sender_jid_row_id:
                                sender_jid = jid_map.get(sender_jid_row_id, "")
                                if sender_jid and '@s.whatsapp.net' in sender_jid:
                                    number = sender_jid.split('@')[0]
                                    if number not in seen_numbers:
                                        seen_numbers.add(number)
                                        contact_name = self.contacts_map.get(number[-10:], "") if len(number) >= 10 else ""
                                        
                                        participants.append({
                                            "number": number,
                                            "name": contact_name or number,
                                            "jid": sender_jid
                                        })
                        
                        if participants:
                            group_participants[group_name] = participants
                    
                    except Exception as e:
                        print(f" Error extracting participants for {group_name}: {e}")
            
            conn.close()
            print(f" Extracted participants for {len(group_participants)} groups")
            
        except Exception as e:
            print(f" Error in group participant extraction: {e}")
        
        return group_participants

    def extract_call_logs(self, db_path, jid_map):
        """Extract call logs from database"""
        print(" Extracting call logs...")
        
        call_logs = []
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if call_log table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='call_log'")
            if not cursor.fetchone():
                print(" No call_log table found in database")
                conn.close()
                return call_logs
        
            # Get call_log table structure
            cursor.execute("PRAGMA table_info(call_log)")
            columns = [row[1] for row in cursor.fetchall()]
            print(f" Call log columns: {columns}")
            
            # Find relevant columns
            def find_col(*names):
                for name in names:
                    if name in columns:
                        return name
                return None
            
            jid_col = find_col('jid_row_id', 'remote_jid', 'jid')
            timestamp_col = find_col('timestamp', 'call_timestamp', 'time')
            duration_col = find_col('duration', 'call_duration')
            call_type_col = find_col('call_result', 'call_type', 'type')
            video_call_col = find_col('video_call', 'is_video', 'video')
            from_me_col = find_col('from_me', 'outgoing')
            
            # Build query based on available columns
            select_cols = []
            if jid_col: select_cols.append(jid_col)
            if timestamp_col: select_cols.append(timestamp_col)
            if duration_col: select_cols.append(duration_col)
            if call_type_col: select_cols.append(call_type_col)
            if video_call_col: select_cols.append(video_call_col)
            if from_me_col: select_cols.append(from_me_col)
            
            if not select_cols:
                print(" Could not identify call log columns")
                conn.close()
                return call_logs
            
            query = f"SELECT {', '.join(select_cols)} FROM call_log ORDER BY {timestamp_col or 'ROWID'} DESC"
            cursor.execute(query)
            rows = cursor.fetchall()
            
            print(f"📊 Found {len(rows)} call log entries")
            
            for row in rows:
                try:
                    call_data = {}
                    col_idx = 0
                    
                    # Extract JID and resolve contact
                    if jid_col:
                        jid_row_id = row[col_idx]
                        jid_str = jid_map.get(jid_row_id, "Unknown")
                        
                        # Extract phone number and get contact name
                        phone_number = self.extract_number_from_jid(jid_str)
                        contact_name = ""
                        if phone_number and phone_number in self.contacts_map:
                            contact_name = self.contacts_map[phone_number]
                        
                        call_data['contact'] = contact_name or jid_str
                        call_data['phone_number'] = phone_number or jid_str
                        call_data['jid'] = jid_str
                        col_idx += 1
                    
                    # Extract timestamp
                    if timestamp_col:
                        timestamp = row[col_idx]
                        try:
                            # Handle different timestamp formats
                            if timestamp > 1000000000000:  # Milliseconds
                                timestamp = timestamp / 1000
                            
                            dt = datetime.fromtimestamp(timestamp)
                            call_data['timestamp'] = int(timestamp)
                            call_data['date'] = dt.strftime('%Y-%m-%d')
                            call_data['time'] = dt.strftime('%H:%M:%S')
                            call_data['datetime'] = dt.isoformat()
                        except:
                            call_data['timestamp'] = timestamp
                            call_data['date'] = "Unknown"
                            call_data['time'] = "Unknown"
                    col_idx += 1
                
                    # Extract duration
                    if duration_col:
                        duration = row[col_idx]
                        call_data['duration_seconds'] = duration or 0
                        
                        # Format duration as MM:SS
                        if duration and duration > 0:
                            minutes = duration // 60
                            seconds = duration % 60
                            call_data['duration_formatted'] = f"{minutes:02d}:{seconds:02d}"
                        else:
                            call_data['duration_formatted'] = "00:00"
                    col_idx += 1
                
                    # Extract call type/result
                    if call_type_col:
                        call_type = row[col_idx]
                        # Map call result codes to readable names
                        call_type_map = {
                            0: "missed",
                            1: "answered",
                            2: "rejected",
                            3: "cancelled",
                            4: "unavailable",
                            5: "busy"
                        }
                        call_data['call_result'] = call_type_map.get(call_type, f"unknown_{call_type}")
                    col_idx += 1
                
                    # Extract video call flag
                    if video_call_col:
                        is_video = row[col_idx]
                        call_data['is_video_call'] = bool(is_video)
                        call_data['call_type'] = "video" if is_video else "voice"
                        col_idx += 1
                    else:
                        call_data['is_video_call'] = False
                        call_data['call_type'] = "voice"
                
                    # Extract direction (incoming/outgoing)
                    if from_me_col:
                        from_me = row[col_idx]
                        call_data['direction'] = "outgoing" if from_me else "incoming"
                        col_idx += 1
                    else:
                        call_data['direction'] = "unknown"
                
                    call_logs.append(call_data)
                    
                except Exception as e:
                    print(f"⚠️ Error processing call log entry: {e}")
                    continue
            
            conn.close()
            print(f"✅ Extracted {len(call_logs)} call logs")
            
        except Exception as e:
            print(f"❌ Error extracting call logs: {e}")
        
        return call_logs

    def parse_messages(self, db_path, jid_map, chat_map, zipf):
        """Parse all messages from database with media support"""
        print("💬 Parsing messages with media support...")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get message table structure
        cursor.execute("PRAGMA table_info(message)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Find relevant columns
        def find_col(*names):
            for name in names:
                if name in columns:
                    return columns.index(name)
            return None

        jid_idx = find_col('chat_row_id', 'key_remote_jid', 'jid')
        text_idx = find_col('text_data', 'data', 'message_text')
        ts_idx = find_col('timestamp')
        dir_idx = find_col('key_from_me', 'from_me')
        sender_idx = find_col('sender_jid_row_id', 'remote_resource', 'sender_jid')
        
        # Get all messages
        cursor.execute(f"SELECT * FROM message ORDER BY ROWID ASC")
        rows = cursor.fetchall()
        conn.close()
        
        # Process messages
        chat_messages = {}
        chat_list = []
        messages_with_media = 0
        
        for row in rows:
            chat_id = row[jid_idx] if jid_idx is not None else None
            text = row[text_idx] if text_idx is not None else ""
            ts = row[ts_idx] if ts_idx is not None else None
            direction = row[dir_idx] if dir_idx is not None else 0
            sender_id = row[sender_idx] if sender_idx is not None else None
            
            if ts is None or chat_id not in chat_map:
                continue
                
            try:
                date_str = datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d')
            except:
                continue
            
            chat_display = chat_map[chat_id]
            
            # Determine sender name
            if sender_id is None or sender_id == '':
                sender_name = "You" if direction == 1 else chat_display
            else:
                resolved = jid_map.get(sender_id)
                sender_name = "You" if direction == 1 else (resolved if resolved else chat_display)
            
            # Check for media in this message
            media_filename = self.find_media_in_row(row, columns)
            media_info = None
            
            if media_filename and media_filename in self.media_path_mapping:
                media_info = {
                    'filename': media_filename,
                    'local_path': self.media_path_mapping[media_filename]['extracted_path'],
                    'type': self.media_path_mapping[media_filename]['type'],
                    'size': self.media_path_mapping[media_filename]['size'],
                    'size_formatted': self.format_file_size(self.media_path_mapping[media_filename]['size'])
                }
                messages_with_media += 1
            
            # Process text content
            text_content = ""
            if text:
                try:
                    if isinstance(text, bytes):
                        text_content = text.decode('utf-8', errors='replace')
                    else:
                        text_content = str(text)
                except:
                    text_content = str(text)
            
            # Organize messages by chat and date
            if chat_display not in chat_messages:
                chat_messages[chat_display] = {}
            if date_str not in chat_messages[chat_display]:
                chat_messages[chat_display][date_str] = []
            
            message_data = {
                "timestamp": ts // 1000,
                "text": text_content,
                "direction": "sent" if direction == 1 else "received",
                "sender": sender_name,
                "date": date_str,
                "time": datetime.fromtimestamp(ts // 1000).strftime('%H:%M:%S')
            }
            
            # Add media info if present
            if media_info:
                message_data["media"] = media_info
            
            chat_messages[chat_display][date_str].append(message_data)
        
        # Create chat list
        for chat_id, chat_name in chat_map.items():
            if chat_name in chat_messages:
                chat_type = "group" if "@g.us" in chat_name else "contact"
                phone_number = self.extract_number_from_jid(chat_name)
                
                display_name = chat_name
                if phone_number and phone_number in self.contacts_map:
                    display_name = f"{self.contacts_map[phone_number]} ({chat_name})"
                
                chat_list.append({
                    "name": display_name,
                    "original_name": chat_name,
                    "type": chat_type,
                    "message_count": sum(len(msgs) for msgs in chat_messages[chat_name].values())
                })
        
        print(f"✅ Parsed {len(chat_list)} chats with messages")
        print(f"📎 Found {messages_with_media} messages with media attachments")
        return chat_messages, chat_list

    def extract_number_from_jid(self, jid):
        """Extract phone number from JID"""
        if jid and '@' in jid and jid.split('@')[0].isdigit():
            return jid.split('@')[0][-10:]
        return None

    def save_json_files(self):
        """Save all data to JSON files with media information"""
        print("💾 Saving JSON files with media information...")
        
        # 1. Master JSON file with all information including media
        master_data = {
            "export_info": {
                "export_date": datetime.now().isoformat(),
                "total_chats": len(self.chat_list),
                "total_contacts": len(self.contacts_map),
                "total_groups": len(self.group_participants),
                "total_call_logs": len(self.call_logs),
                "total_media_files": len(self.media_path_mapping),
                "media_directory": str(self.media_dir.absolute()),
                "description": "Complete WhatsApp data export with media files"
            },
            "chats": {
                "messages": self.chat_data,
                "chat_list": self.chat_list
            },
            "contacts": self.contacts_map,
            "groups": self.group_participants,
            "call_logs": self.call_logs,
            "media_info": {
                "total_files": len(self.media_path_mapping),
                "media_directory": str(self.media_dir.absolute()),
                "media_by_type": self.get_media_statistics()
            }
        }
        
        master_file = self.output_dir / "whatsapp_master_data.json"
        with open(master_file, 'w', encoding='utf-8') as f:
            json.dump(master_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Master file saved: {master_file}")
        
        # 2. Separate chats file
        chats_file = self.output_dir / "whatsapp_chats.json"
        chats_data = {
            "export_date": datetime.now().isoformat(),
            "total_chats": len(self.chat_list),
            "chat_list": self.chat_list,
            "messages": self.chat_data
        }
        with open(chats_file, 'w', encoding='utf-8') as f:
            json.dump(chats_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Chats file saved: {chats_file}")
        
        # 3. Separate contacts file
        contacts_file = self.output_dir / "whatsapp_contacts.json"
        contacts_data = {
            "export_date": datetime.now().isoformat(),
            "total_contacts": len(self.contacts_map),
            "contacts": [
                {"number": number, "name": name} 
                for number, name in self.contacts_map.items()
            ]
        }
        with open(contacts_file, 'w', encoding='utf-8') as f:
            json.dump(contacts_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Contacts file saved: {contacts_file}")
        
        # 4. Separate groups file
        groups_file = self.output_dir / "whatsapp_groups.json"
        groups_data = {
            "export_date": datetime.now().isoformat(),
            "total_groups": len(self.group_participants),
            "groups": self.group_participants
        }
        with open(groups_file, 'w', encoding='utf-8') as f:
            json.dump(groups_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Groups file saved: {groups_file}")
        
        # 5. Separate call logs file
        call_logs_file = self.output_dir / "whatsapp_call_logs.json"
        call_logs_data = {
            "export_date": datetime.now().isoformat(),
            "total_call_logs": len(self.call_logs),
            "call_logs": self.call_logs,
            "statistics": {
                "total_calls": len(self.call_logs),
                "incoming_calls": len([c for c in self.call_logs if c.get('direction') == 'incoming']),
                "outgoing_calls": len([c for c in self.call_logs if c.get('direction') == 'outgoing']),
                "video_calls": len([c for c in self.call_logs if c.get('is_video_call', False)]),
                "voice_calls": len([c for c in self.call_logs if not c.get('is_video_call', False)]),
                "missed_calls": len([c for c in self.call_logs if c.get('call_result') == 'missed']),
                "answered_calls": len([c for c in self.call_logs if c.get('call_result') == 'answered'])
            }
        }
        with open(call_logs_file, 'w', encoding='utf-8') as f:
            json.dump(call_logs_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Call logs file saved: {call_logs_file}")
        
        # 6. Media summary file
        media_summary_file = self.output_dir / "whatsapp_media_summary.json"
        media_summary_data = {
            "export_date": datetime.now().isoformat(),
            "total_media_files": len(self.media_path_mapping),
            "media_directory": str(self.media_dir.absolute()),
            "media_paths_directory": str(self.media_paths_dir.absolute()),
            "statistics": self.get_media_statistics(),
            "sample_files": list(self.media_path_mapping.items())[:10]  # First 10 as sample
        }
        with open(media_summary_file, 'w', encoding='utf-8') as f:
            json.dump(media_summary_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Media summary file saved: {media_summary_file}")
        
        # 7. Individual chat files (optional, for large datasets)
        individual_chats_dir = self.output_dir / "individual_chats"
        individual_chats_dir.mkdir(exist_ok=True)
        
        for chat_name, messages in self.chat_data.items():
            safe_name = "".join(c for c in chat_name if c.isalnum() or c in " -_").strip()[:50]
            chat_file = individual_chats_dir / f"{safe_name}.json"
            
            chat_info = next((c for c in self.chat_list if c['original_name'] == chat_name), {})
            individual_chat_data = {
                "chat_info": chat_info,
                "messages": messages,
                "export_date": datetime.now().isoformat()
            }
            
            with open(chat_file, 'w', encoding='utf-8') as f:
                json.dump(individual_chat_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Individual chat files saved in: {individual_chats_dir}")

    def get_media_statistics(self):
        """Get media statistics by type"""
        stats = {}
        total_size = 0
        
        for filename, info in self.media_path_mapping.items():
            media_type = info['type']
            if media_type not in stats:
                stats[media_type] = {'count': 0, 'total_size': 0}
            
            stats[media_type]['count'] += 1
            stats[media_type]['total_size'] += info['size']
            total_size += info['size']
        
        # Add formatted sizes
        for media_type in stats:
            stats[media_type]['total_size_formatted'] = self.format_file_size(stats[media_type]['total_size'])
        
        stats['_total'] = {
            'count': len(self.media_path_mapping),
            'total_size': total_size,
            'total_size_formatted': self.format_file_size(total_size)
        }
        
        return stats

    def process_whatsapp_data(self):
        """Main processing function with media extraction"""
        try:
            print("🚀 Starting WhatsApp data extraction with media support...")
            
            # Find ZIP file
            zip_path = self.find_zip_file()
            
            with pyzipper.AESZipFile(zip_path, 'r') as zipf:
                # Find required files
                db_info = self.find_in_zip(zipf, "msgstore.db.crypt")
                key_info = self.find_in_zip(zipf, "com.whatsapp/files/key")
                contacts_info = self.find_in_zip(zipf, "contacts2.db") or self.find_in_zip(zipf, "contacts.db")
                
                if not db_info or not key_info:
                    raise ValueError("❌ Could not find WhatsApp database or key in ZIP file")
                
                print("✅ Found required files in ZIP")
                
                # Build media index and extract media files
                self.media_index = self.build_media_index(zipf)
                media_files = self.get_media_files_from_zip(zipf)
                extracted_count = self.extract_media_from_zip(zipf, media_files)
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Extract files
                    db_file = self.extract_file_from_zip(zipf, db_info, temp_dir)
                    key_file = self.extract_file_from_zip(zipf, key_info, temp_dir)
                    
                    # Parse contacts if available
                    if contacts_info:
                        contacts_db_file = self.extract_file_from_zip(zipf, contacts_info, temp_dir)
                        self.contacts_map = self.parse_contacts_db(contacts_db_file)
                    
                    # Decrypt database
                    decrypted_db = self.decrypt_database(key_file, db_file)
                    
                    # Process database
                    conn = sqlite3.connect(decrypted_db)
                    jid_map = self.get_jid_map(conn)
                    chat_map = self.get_chat_info(conn, jid_map)
                    conn.close()
                    
                    print(f"📊 Loaded {len(jid_map)} JID mappings")
                    print(f"📊 Found {len(chat_map)} chats")
                    
                    # Extract group participants
                    self.group_participants = self.extract_group_participants(decrypted_db, jid_map)
                    
                    # Extract call logs
                    self.call_logs = self.extract_call_logs(decrypted_db, jid_map)
                    
                    # Parse messages with media support
                    self.chat_data, self.chat_list = self.parse_messages(decrypted_db, jid_map, chat_map, zipf)
                    
                    # Clean up decrypted database
                    if os.path.exists(decrypted_db):
                        os.remove(decrypted_db)
                    
                    # Save all JSON files
                    self.save_json_files()
                    
                    # Save media path mappings
                    self.save_media_path_mappings()
                    
                    print("\n🎉 Extraction completed successfully!")
                    print(f"📁 JSON files saved in: {self.output_dir.absolute()}")
                    print(f"📁 Media files saved in: {self.media_dir.absolute()}")
                    print(f"📁 Media paths saved in: {self.media_paths_dir.absolute()}")
                    print(f"📊 Summary:")
                    print(f"   - Chats: {len(self.chat_list)}")
                    print(f"   - Contacts: {len(self.contacts_map)}")
                    print(f"   - Groups: {len(self.group_participants)}")
                    print(f"   - Call Logs: {len(self.call_logs)}")
                    print(f"   - Media Files: {len(self.media_path_mapping)}")
                    
        except Exception as e:
            print(f"❌ Error during extraction: {e}")
            print(traceback.format_exc())
            raise


def main():
    print("=" * 60)
    print("🔍 WhatsApp Data Extractor - VS Code Edition with Media")
    print("=" * 60)
    
    # Get folder path from user
    folder_path = input("📂 Enter the path to your WhatsApp backup folder: ").strip().strip('"')
    
    if not folder_path:
        print("❌ No folder path provided!")
        return
    
    if not os.path.exists(folder_path):
        print(f"❌ Folder does not exist: {folder_path}")
        return
    
    try:
        # Create extractor and process data
        extractor = WhatsAppDataExtractor(folder_path)
        extractor.process_whatsapp_data()
        
        print("\n✨ All done! Check your folders:")
        print("   📄 'whatsapp_data_output' - JSON files")
        print("   📎 'media' - Extracted media files")
        print("   📋 'media_paths' - Media path mappings")
        
    except Exception as e:
        print(f"❌ Failed to extract WhatsApp data: {e}")


if __name__ == "__main__":
    main()
