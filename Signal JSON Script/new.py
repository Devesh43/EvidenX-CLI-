#!/usr/bin/env python3
"""
Comprehensive Signal Data Extractor - Fixes All Issues
Handles empty messages, base64 decoding, media linking, phone numbers, and more
Creates: individual_chats.json, group_chats.json, call_logs.json, contacts.json, media.json, master.json
"""

import os
import sqlite3
import tempfile
from datetime import datetime
import json
import xml.etree.ElementTree as ET
from pathlib import Path
import traceback
import base64
import binascii
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
import re

try:
    import zipfile
    ZIPFILE_AVAILABLE = True
except ImportError:
    ZIPFILE_AVAILABLE = False

class ComprehensiveSignalExtractor:
    def __init__(self):
        self.output_dir = Path("signal_export_comprehensive")
        self.output_dir.mkdir(exist_ok=True)
        
        # Data containers
        self.individual_chats = []
        self.group_chats = []
        self.call_logs = []
        self.contacts = []
        self.media = []
        
        # Helper mappings
        self.recipients = {}
        self.threads = {}
        self.attachments = {}  # attachment_id -> attachment_info
        self.message_attachments = {}  # message_id -> [attachment_ids]
        
        # Signal message type mappings
        self.message_types = {
            # Text messages
            10485780: "text_message",
            10485783: "text_message_edited", 
            
            # Media messages
            10486292: "image_message",
            10486804: "video_message",
            10487316: "audio_message",
            10487828: "document_message",
            10488340: "sticker_message",
            
            # Call messages
            11: "incoming_call",
            12: "outgoing_call",
            1: "missed_call",
            
            # Group messages
            11075607: "group_creation",
            11076119: "group_member_added",
            11076631: "group_member_removed",
            11077143: "group_name_changed",
            
            # System messages
            0: "system_message",
            1: "key_exchange",
            2: "identity_update"
        }
        
        print(f" Output directory: {self.output_dir.absolute()}")

    def find_signal_files(self, search_path):
        """Find Signal database files with priority for decrypted ones"""
        print(f" Searching for Signal files in: {search_path}")
        
        found_files = {
            'databases': [],
            'decrypted_databases': [],
            'preferences': [],
            'keystore': []
        }
        
        # Handle ZIP files
        if str(search_path).lower().endswith('.zip') and os.path.isfile(search_path):
            if ZIPFILE_AVAILABLE:
                try:
                    with zipfile.ZipFile(search_path, 'r') as zip_ref:
                        temp_dir = tempfile.mkdtemp()
                        
                        for file_path in zip_ref.namelist():
                            # Signal databases
                            if ('signal.db' in file_path.lower() and 
                                'thoughtcrime.securesms' in file_path):
                                
                                extracted_path = zip_ref.extract(file_path, temp_dir)
                                
                                if 'decrypted' in file_path.lower():
                                    found_files['decrypted_databases'].append(extracted_path)
                                    print(f" Found DECRYPTED database: {file_path}")
                                else:
                                    found_files['databases'].append(extracted_path)
                                    print(f" Found encrypted database: {file_path}")
                            
                            # Preferences
                            elif ('thoughtcrime.securesms_preferences.xml' in file_path):
                                extracted_path = zip_ref.extract(file_path, temp_dir)
                                found_files['preferences'].append(extracted_path)
                                print(f" Found preferences: {file_path}")
                            
                            # Keystore
                            elif ('SignalSecret' in file_path and 'keystore' in file_path):
                                extracted_path = zip_ref.extract(file_path, temp_dir)
                                found_files['keystore'].append(extracted_path)
                                print(f" Found keystore: {file_path}")
                                
                except Exception as e:
                    print(f" Error reading ZIP: {e}")
        
        # Handle directories
        elif os.path.isdir(search_path):
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # Signal databases
                    if ('signal.db' in file.lower() and 
                        'thoughtcrime.securesms' in root):
                        
                        if 'decrypted' in file.lower():
                            found_files['decrypted_databases'].append(file_path)
                            print(f" Found DECRYPTED database: {os.path.relpath(file_path, search_path)}")
                        else:
                            found_files['databases'].append(file_path)
                            print(f" Found encrypted database: {os.path.relpath(file_path, search_path)}")
                    
                    # Preferences
                    elif 'thoughtcrime.securesms_preferences.xml' in file:
                        found_files['preferences'].append(file_path)
                        print(f" Found preferences: {os.path.relpath(file_path, search_path)}")
                    
                    # Keystore
                    elif 'SignalSecret' in file and 'keystore' in root:
                        found_files['keystore'].append(file_path)
                        print(f" Found keystore: {os.path.relpath(file_path, search_path)}")
        
        return found_files

    def get_best_database(self, found_files):
        """Get the best database to use (prioritize decrypted)"""
        # First priority: decrypted databases
        if found_files['decrypted_databases']:
            db_path = found_files['decrypted_databases'][0]
            print(f" Using DECRYPTED database: {os.path.basename(db_path)}")
            return db_path, 'decrypted'
        
        # Second priority: try to decrypt encrypted database
        if found_files['databases'] and found_files['keystore'] and found_files['preferences']:
            print("Found encrypted database with keys - attempting decryption...")
            decrypted_path = self.decrypt_signal_database(
                found_files['databases'][0],
                found_files['keystore'][0], 
                found_files['preferences'][0]
            )
            if decrypted_path:
                return decrypted_path, 'decrypted'
        
        # Last resort: try encrypted database directly (usually fails)
        if found_files['databases']:
            db_path = found_files['databases'][0]
            print(f" Using encrypted database (may not work): {os.path.basename(db_path)}")
            return db_path, 'encrypted'
        
        return None, None

    def decrypt_signal_database(self, db_path, keystore_path, preferences_path):
        """Decrypt Signal database using keystore and preferences"""
        try:
            print(" Attempting to decrypt Signal database...")
            
            # Extract keystore key (16 bytes from offset 0x2D to 0x3C)
            with open(keystore_path, 'rb') as f:
                keystore_data = f.read()
            
            if len(keystore_data) < 0x3D:
                print(" Keystore file too small")
                return None
            
            userkey = keystore_data[0x2D:0x3D]  # 16 bytes
            print(f" Extracted {len(userkey)} byte key from keystore")
            
            # Extract encrypted secret from preferences
            tree = ET.parse(preferences_path)
            root = tree.getroot()
            
            encrypted_secret = None
            for string_elem in root.findall(".//string[@name='pref_database_encrypted_secret']"):
                encrypted_secret = string_elem.text
                break
            
            if not encrypted_secret:
                print(" Could not find encrypted secret in preferences")
                return None
            
            print(" Found encrypted secret in preferences")
            
            # Decode and decrypt
            encrypted_data = base64.b64decode(encrypted_secret)
            
            # For AES-GCM: IV (12 bytes) + ciphertext + auth_tag (16 bytes)
            if len(encrypted_data) < 28:
                print(" Encrypted data too short")
                return None
            
            iv = encrypted_data[:12]
            auth_tag = encrypted_data[-16:]
            ciphertext = encrypted_data[12:-16]
            
            # Decrypt using AES-GCM
            aesgcm = AESGCM(userkey)
            database_key = aesgcm.decrypt(iv, ciphertext + auth_tag, None)
            
            print(" Successfully decrypted database key")
            
            # Create decrypted database copy
            decrypted_path = db_path + ".decrypted_temp"
            
            # Copy and decrypt using SQLCipher parameters
            import shutil
            shutil.copy2(db_path, decrypted_path)
            
            # Try to open with the decrypted key
            try:
                conn = sqlite3.connect(decrypted_path)
                # Set SQLCipher parameters as per Signal source code
                key_hex = database_key.hex()
                conn.execute(f"PRAGMA key = \"x'{key_hex}'\"")
                conn.execute("PRAGMA cipher_default_kdf_iter = 1")
                conn.execute("PRAGMA cipher_default_page_size = 4096")
                
                # Test the connection
                cursor = conn.cursor()
                cursor.execute("SELECT count(*) FROM sqlite_master")
                result = cursor.fetchone()
                conn.close()
                
                if result and result[0] > 0:
                    print(f" Successfully decrypted database ({result[0]} tables)")
                    return decrypted_path
                else:
                    print(" Decryption failed - no tables found")
                    os.remove(decrypted_path)
                    return None
                    
            except Exception as e:
                print(f" Failed to open decrypted database: {e}")
                if os.path.exists(decrypted_path):
                    os.remove(decrypted_path)
                return None
            
        except Exception as e:
            print(f" Error during decryption: {e}")
            return None

    def test_database_connection(self, db_path):
        """Test if database can be opened and read"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Try to read sqlite_master table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 5")
            tables = cursor.fetchall()
            conn.close()
            
            if tables:
                print(f" Database connection successful - found {len(tables)} tables")
                return True
            else:
                print(" Database appears empty")
                return False
                
        except Exception as e:
            print(f" Database connection failed: {e}")
            return False

    def decode_base64_message(self, text):
        """Try to decode base64 encoded messages"""
        if not text or text == "[Empty Message]":
            return text
        
        # Check if it looks like base64
        if len(text) > 20 and re.match(r'^[A-Za-z0-9+/=]+$', text):
            try:
                decoded_bytes = base64.b64decode(text)
                # Try to decode as UTF-8
                decoded_text = decoded_bytes.decode('utf-8', errors='ignore')
                
                # If it contains readable text, return it
                if any(c.isalpha() for c in decoded_text):
                    return f"[Decoded]: {decoded_text}"
                else:
                    return f"[Binary Data]: {len(decoded_bytes)} bytes"
            except:
                pass
        
        return text

    def get_message_type_description(self, msg_type):
        """Get human-readable message type"""
        return self.message_types.get(msg_type, f"unknown_type_{msg_type}")

    def extract_recipients(self, cursor):
        """Extract all recipients/contacts with better phone number extraction"""
        print(" Extracting recipients...")
        
        try:
            # Check if recipient table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='recipient'")
            if not cursor.fetchone():
                print(" No recipient table found")
                return
            
            # Get table structure
            cursor.execute("PRAGMA table_info(recipient)")
            columns = [row[1] for row in cursor.fetchall()]
            print(f" Recipient columns: {columns}")
            
            # Get all recipients
            cursor.execute("SELECT * FROM recipient")
            rows = cursor.fetchall()
            
            print(f" Processing {len(rows)} recipients...")
            
            for row in rows:
                try:
                    recipient_data = dict(zip(columns, row))
                    recipient_id = recipient_data.get('_id')
                    
                    if recipient_id:
                        # Extract contact info with multiple fallbacks
                        name = (recipient_data.get('profile_name') or 
                               recipient_data.get('system_display_name') or 
                               recipient_data.get('profile_given_name') or
                               recipient_data.get('profile_family_name') or
                               recipient_data.get('username') or 
                               recipient_data.get('phone') or 
                               recipient_data.get('e164') or
                               f"Contact {recipient_id}")
                        
                        # Better phone number extraction
                        phone = None
                        for phone_field in ['e164', 'phone', 'number']:
                            if recipient_data.get(phone_field):
                                phone_raw = str(recipient_data[phone_field])
                                # Clean phone number
                                phone_clean = re.sub(r'[^\d+]', '', phone_raw)
                                if len(phone_clean) >= 10:
                                    phone = phone_clean
                                    break
                        
                        # Better group detection
                        is_group = bool(
                            recipient_data.get('group_id') or 
                            recipient_data.get('group_type') or
                            (recipient_data.get('registered') == 2) or
                            ('__signal_group__' in str(recipient_data.get('group_id', '')))
                        )
                        
                        # Extract group ID properly
                        group_id = recipient_data.get('group_id')
                        if group_id and isinstance(group_id, str) and '__signal_group__' in group_id:
                            is_group = True
                        
                        contact_info = {
                            'id': recipient_id,
                            'name': str(name).strip() if name else f"Contact {recipient_id}",
                            'phone': phone,
                            'is_group': is_group,
                            'group_id': group_id,
                            'profile_key': recipient_data.get('profile_key'),
                            'signal_profile_name': recipient_data.get('signal_profile_name'),
                            'raw_data': recipient_data
                        }
                        
                        self.recipients[recipient_id] = contact_info
                        
                        # Add to contacts list
                        self.contacts.append({
                            'id': recipient_id,
                            'name': contact_info['name'],
                            'phone_number': contact_info['phone'],
                            'is_group': contact_info['is_group'],
                            'group_id': contact_info['group_id'],
                            'profile_key': contact_info['profile_key']
                        })
                        
                except Exception as e:
                    print(f" Error processing recipient: {e}")
                    continue
            
            print(f" Extracted {len(self.recipients)} recipients")
            
        except Exception as e:
            print(f" Error extracting recipients: {e}")
            print(traceback.format_exc())

    def extract_attachments(self, cursor):
        """Extract attachment information and link to messages"""
        print("📎 Extracting attachments...")
        
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attachment'")
            if not cursor.fetchone():
                print(" No attachment table found")
                return
            
            cursor.execute("PRAGMA table_info(attachment)")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"📋 Attachment columns: {columns}")
            
            # Get all attachments
            cursor.execute("SELECT * FROM attachment")
            rows = cursor.fetchall()
            
            print(f" Processing {len(rows)} attachments...")
            
            for row in rows:
                try:
                    attachment_data = dict(zip(columns, row))
                    attachment_id = attachment_data.get('_id')
                    
                    if attachment_id:
                        # Extract attachment info
                        filename = (attachment_data.get('file_name') or 
                                   attachment_data.get('data_file') or
                                   attachment_data.get('thumbnail_file') or
                                   f"attachment_{attachment_id}")
                        
                        content_type = (attachment_data.get('content_type') or 
                                       attachment_data.get('ct') or 
                                       'unknown')
                        
                        size = (attachment_data.get('data_size') or 
                               attachment_data.get('size') or 0)
                        
                        # Get message ID if available
                        message_id = attachment_data.get('mid') or attachment_data.get('message_id')
                        
                        attachment_info = {
                            'id': attachment_id,
                            'filename': str(filename),
                            'content_type': str(content_type),
                            'size_bytes': int(size) if size else 0,
                            'message_id': message_id,
                            'width': attachment_data.get('width'),
                            'height': attachment_data.get('height'),
                            'duration': attachment_data.get('duration'),
                            'raw_data': attachment_data
                        }
                        
                        self.attachments[attachment_id] = attachment_info
                        
                        # Link to message
                        if message_id:
                            if message_id not in self.message_attachments:
                                self.message_attachments[message_id] = []
                            self.message_attachments[message_id].append(attachment_id)
                        
                        # Add to media list
                        self.media.append({
                            'id': attachment_id,
                            'filename': attachment_info['filename'],
                            'type': attachment_info['content_type'],
                            'size_bytes': attachment_info['size_bytes'],
                            'message_id': message_id,
                            'dimensions': f"{attachment_info['width']}x{attachment_info['height']}" if attachment_info['width'] and attachment_info['height'] else None,
                            'duration_seconds': attachment_info['duration'],
                            'table_source': 'attachment'
                        })
                        
                except Exception as e:
                    print(f"⚠️ Error processing attachment: {e}")
                    continue
            
            print(f"✅ Extracted {len(self.attachments)} attachments")
            
        except Exception as e:
            print(f" Error extracting attachments: {e}")

    def extract_threads(self, cursor):
        """Extract thread information"""
        print("🧵 Extracting threads...")
        
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='thread'")
            if not cursor.fetchone():
                print("⚠️ No thread table found")
                return
            
            cursor.execute("SELECT _id, recipient_id FROM thread")
            for thread_id, recipient_id in cursor.fetchall():
                if thread_id and recipient_id:
                    self.threads[thread_id] = recipient_id
            
            print(f"✅ Mapped {len(self.threads)} threads")
            
        except Exception as e:
            print(f" Error extracting threads: {e}")

    def extract_messages(self, cursor):
        """Extract and organize messages with proper content handling"""
        print("💬 Extracting messages...")
        
        try:
            # Find message table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            all_tables = [row[0] for row in cursor.fetchall()]
            print(f"📋 Available tables: {all_tables}")
            
            # Look for message tables
            message_tables = [t for t in all_tables if t.lower() in ['sms', 'message', 'messages']]
            if not message_tables:
                print(" No message table found")
                return
            
            message_table = message_tables[0]
            print(f"📋 Using message table: {message_table}")
            
            # Get table structure
            cursor.execute(f"PRAGMA table_info({message_table})")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"📋 Message columns: {columns}")
            
            # Find required columns with multiple options
            body_col = None
            for col in columns:
                if col.lower() in ['body', 'text', 'message']:
                    body_col = col
                    break
            
            time_col = None
            for col in columns:
                if any(term in col.lower() for term in ['date', 'time', 'timestamp']):
                    time_col = col
                    break
            
            thread_col = None
            for col in columns:
                if 'thread' in col.lower():
                    thread_col = col
                    break
            
            type_col = None
            for col in columns:
                if col.lower() == 'type':
                    type_col = col
                    break
            
            id_col = None
            for col in columns:
                if col.lower() == '_id':
                    id_col = col
                    break
            
            if not body_col or not time_col:
                print(f"❌ Missing required columns. Body: {body_col}, Time: {time_col}")
                return
            
            print(f"📋 Using columns - Body: {body_col}, Time: {time_col}, Thread: {thread_col}, Type: {type_col}, ID: {id_col}")
            
            # Build query
            select_cols = [body_col, time_col]
            if thread_col:
                select_cols.append(thread_col)
            if type_col:
                select_cols.append(type_col)
            if id_col:
                select_cols.append(id_col)
            
            query = f"SELECT {', '.join(select_cols)} FROM {message_table} ORDER BY {time_col} ASC"
            print(f"📋 Query: {query}")
            
            cursor.execute(query)
            rows = cursor.fetchall()
            print(f"📊 Found {len(rows)} messages")
            
            # Process messages
            chat_messages = {}  # thread_id -> messages
            
            for i, row in enumerate(rows):
                try:
                    body = row[0] if row[0] else "[Empty Message]"
                    timestamp = row[1]
                    thread_id = row[2] if len(row) > 2 else f"unknown_{i}"
                    msg_type = row[3] if len(row) > 3 else 0
                    message_id = row[4] if len(row) > 4 else None
                    
                    # Convert timestamp
                    if timestamp and timestamp > 0:
                        try:
                            if timestamp > 1000000000000:  # Milliseconds
                                dt = datetime.fromtimestamp(timestamp / 1000)
                                ts_seconds = int(timestamp / 1000)
                            else:  # Seconds
                                dt = datetime.fromtimestamp(timestamp)
                                ts_seconds = int(timestamp)
                        except:
                            continue
                    else:
                        continue
                    
                    # Determine direction (Signal: 20+ = sent, others = received)
                    direction = "sent" if msg_type >= 20 else "received"
                    
                    # Get recipient info
                    recipient_id = self.threads.get(thread_id)
                    recipient_info = self.recipients.get(recipient_id, {})
                    
                    chat_name = recipient_info.get('name', f"Unknown Chat {thread_id}")
                    is_group = recipient_info.get('is_group', False)
                    
                    # Decode message content
                    decoded_body = self.decode_base64_message(str(body))
                    
                    # Get message type description
                    type_description = self.get_message_type_description(msg_type)
                    
                    # Check for attachments
                    attachments = []
                    if message_id and message_id in self.message_attachments:
                        for attachment_id in self.message_attachments[message_id]:
                            attachment_info = self.attachments.get(attachment_id, {})
                            attachments.append({
                                'id': attachment_id,
                                'filename': attachment_info.get('filename', 'unknown'),
                                'type': attachment_info.get('content_type', 'unknown'),
                                'size_bytes': attachment_info.get('size_bytes', 0)
                            })
                    
                    # Handle empty messages with attachments
                    if decoded_body == "[Empty Message]" and attachments:
                        if attachments[0]['type'].startswith('image/'):
                            decoded_body = f"[Image: {attachments[0]['filename']}]"
                        elif attachments[0]['type'].startswith('video/'):
                            decoded_body = f"[Video: {attachments[0]['filename']}]"
                        elif attachments[0]['type'].startswith('audio/'):
                            decoded_body = f"[Audio: {attachments[0]['filename']}]"
                        else:
                            decoded_body = f"[File: {attachments[0]['filename']}]"
                    
                    # Handle call messages
                    if type_description.endswith('_call'):
                        if type_description == 'incoming_call':
                            decoded_body = "📞 Incoming call"
                        elif type_description == 'outgoing_call':
                            decoded_body = "📞 Outgoing call"
                        else:
                            decoded_body = "📞 Missed call"
                    
                    message_data = {
                        'message_id': message_id,
                        'timestamp': ts_seconds,
                        'date': dt.strftime('%Y-%m-%d'),
                        'time': dt.strftime('%H:%M:%S'),
                        'text': decoded_body,
                        'original_text': str(body) if body != decoded_body else None,
                        'direction': direction,
                        'sender': "You" if direction == "sent" else chat_name,
                        'message_type': msg_type,
                        'message_type_description': type_description,
                        'attachments': attachments
                    }
                    
                    # Organize by thread
                    if thread_id not in chat_messages:
                        chat_messages[thread_id] = {
                            'chat_info': {
                                'thread_id': thread_id,
                                'name': chat_name,
                                'is_group': is_group,
                                'recipient_id': recipient_id,
                                'phone_number': recipient_info.get('phone'),
                                'group_id': recipient_info.get('group_id')
                            },
                            'messages': {}
                        }
                    
                    date_str = message_data['date']
                    if date_str not in chat_messages[thread_id]['messages']:
                        chat_messages[thread_id]['messages'][date_str] = []
                    
                    chat_messages[thread_id]['messages'][date_str].append(message_data)
                    
                except Exception as e:
                    print(f" Error processing message {i}: {e}")
                    continue
            
            # Separate individual and group chats
            for thread_id, chat_data in chat_messages.items():
                chat_info = chat_data['chat_info']
                messages = chat_data['messages']
                
                # Calculate statistics
                total_messages = sum(len(msgs) for msgs in messages.values())
                sent_count = sum(
                    len([m for m in msgs if m['direction'] == 'sent']) 
                    for msgs in messages.values()
                )
                received_count = total_messages - sent_count
                
                # Count attachments
                total_attachments = sum(
                    len(m.get('attachments', [])) 
                    for msgs in messages.values() 
                    for m in msgs
                )
                
                chat_export = {
                    'chat_info': {
                        'name': chat_info['name'],
                        'thread_id': chat_info['thread_id'],
                        'recipient_id': chat_info['recipient_id'],
                        'phone_number': chat_info['phone_number'],
                        'group_id': chat_info['group_id'],
                        'message_count': total_messages,
                        'sent_count': sent_count,
                        'received_count': received_count,
                        'attachment_count': total_attachments
                    },
                    'messages': messages
                }
                
                if chat_info['is_group']:
                    self.group_chats.append(chat_export)
                else:
                    self.individual_chats.append(chat_export)
            
            print(f"✅ Extracted {len(self.individual_chats)} individual chats")
            print(f"✅ Extracted {len(self.group_chats)} group chats")
            
        except Exception as e:
            print(f"❌ Error extracting messages: {e}")
            print(traceback.format_exc())

    def extract_call_logs(self, cursor):
        """Extract call logs with better duration and type detection"""
        print("📞 Extracting call logs...")
        
        try:
            # Find call tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            all_tables = [row[0] for row in cursor.fetchall()]
            call_tables = [table for table in all_tables if 'call' in table.lower()]
            
            if not call_tables:
                print("⚠️ No call tables found - extracting from messages")
                # Extract calls from message table
                self.extract_calls_from_messages(cursor)
                return
            
            print(f"📋 Found call tables: {call_tables}")
            
            for table in call_tables:
                try:
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = [row[1] for row in cursor.fetchall()]
                    print(f"📋 {table} columns: {columns}")
                    
                    # Find relevant columns
                    time_col = next((col for col in columns if any(term in col.lower() 
                                   for term in ['time', 'date', 'timestamp'])), None)
                    peer_col = next((col for col in columns if any(term in col.lower() 
                                   for term in ['peer', 'recipient', 'address'])), None)
                    type_col = next((col for col in columns if 'type' in col.lower()), None)
                    direction_col = next((col for col in columns if 'direction' in col.lower()), None)
                    duration_col = next((col for col in columns if 'duration' in col.lower()), None)
                    
                    if not time_col:
                        print(f"⚠️ No timestamp column found in {table}")
                        continue
                    
                    # Build query
                    query_cols = [time_col]
                    if peer_col:
                        query_cols.append(peer_col)
                    if type_col:
                        query_cols.append(type_col)
                    if direction_col:
                        query_cols.append(direction_col)
                    if duration_col:
                        query_cols.append(duration_col)
                    
                    cursor.execute(f"SELECT {', '.join(query_cols)} FROM {table}")
                    rows = cursor.fetchall()
                    
                    print(f"📊 Processing {len(rows)} calls from {table}")
                    
                    for row in rows:
                        try:
                            timestamp = row[0]
                            peer_id = row[1] if len(row) > 1 else None
                            call_type = row[2] if len(row) > 2 else 0
                            direction = row[3] if len(row) > 3 else 0
                            duration = row[4] if len(row) > 4 else 0
                            
                            if not timestamp or timestamp <= 0:
                                continue
                            
                            # Convert timestamp
                            if timestamp > 1000000000000:
                                dt = datetime.fromtimestamp(timestamp / 1000)
                                ts_seconds = int(timestamp / 1000)
                            else:
                                dt = datetime.fromtimestamp(timestamp)
                                ts_seconds = int(timestamp)
                            
                            # Get contact info
                            recipient_info = self.recipients.get(peer_id, {})
                            contact_name = recipient_info.get('name', 'Unknown')
                            phone_number = recipient_info.get('phone', 'Unknown')
                            
                            call_data = {
                                'timestamp': ts_seconds,
                                'date': dt.strftime('%Y-%m-%d'),
                                'time': dt.strftime('%H:%M:%S'),
                                'contact_name': contact_name,
                                'phone_number': phone_number,
                                'call_type': 'video' if call_type == 1 else 'voice',
                                'direction': 'outgoing' if direction == 1 else 'incoming',
                                'duration_seconds': duration or 0,
                                'recipient_id': peer_id
                            }
                            
                            self.call_logs.append(call_data)
                            
                        except Exception as e:
                            continue
                            
                except Exception as e:
                    print(f"⚠️ Error processing call table {table}: {e}")
            
            print(f"✅ Extracted {len(self.call_logs)} call logs")
            
        except Exception as e:
            print(f"❌ Error extracting call logs: {e}")

    def extract_calls_from_messages(self, cursor):
        """Extract call information from message table"""
        print("📞 Extracting calls from messages...")
        
        try:
            # Look for call-related message types
            call_types = [11, 12, 1]  # incoming, outgoing, missed
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            all_tables = [row[0] for row in cursor.fetchall()]
            message_tables = [t for t in all_tables if t.lower() in ['sms', 'message', 'messages']]
            
            if not message_tables:
                return
            
            message_table = message_tables[0]
            
            # Get call messages
            cursor.execute(f"SELECT date_sent, thread_id, type FROM {message_table} WHERE type IN ({','.join(map(str, call_types))})")
            
            for timestamp, thread_id, msg_type in cursor.fetchall():
                try:
                    if timestamp > 1000000000000:
                        dt = datetime.fromtimestamp(timestamp / 1000)
                        ts_seconds = int(timestamp / 1000)
                    else:
                        dt = datetime.fromtimestamp(timestamp)
                        ts_seconds = int(timestamp)
                    
                    recipient_id = self.threads.get(thread_id)
                    recipient_info = self.recipients.get(recipient_id, {})
                    
                    call_data = {
                        'timestamp': ts_seconds,
                        'date': dt.strftime('%Y-%m-%d'),
                        'time': dt.strftime('%H:%M:%S'),
                        'contact_name': recipient_info.get('name', 'Unknown'),
                        'phone_number': recipient_info.get('phone'),
                        'call_type': 'video' if msg_type == 11 else 'voice',
                        'direction': 'outgoing' if msg_type == 12 else 'incoming',
                        'duration_seconds': 0,  # Duration not available in messages
                        'recipient_id': recipient_id
                    }
                    
                    self.call_logs.append(call_data)
                    
                except Exception as e:
                    continue
            
            print(f"✅ Extracted {len(self.call_logs)} calls from messages")
            
        except Exception as e:
            print(f"❌ Error extracting calls from messages: {e}")

    def save_json_files(self):
        """Save all data to the 6 required JSON files"""
        print("💾 Saving JSON files...")
        
        # 1. Individual Chats
        individual_file = self.output_dir / "individual_chats.json"
        with open(individual_file, 'w', encoding='utf-8') as f:
            json.dump({
                'export_date': datetime.now().isoformat(),
                'total_individual_chats': len(self.individual_chats),
                'chats': self.individual_chats
            }, f, indent=2, ensure_ascii=False)
        print(f"✅ individual_chats.json ({len(self.individual_chats)} chats)")
        
        # 2. Group Chats
        group_file = self.output_dir / "group_chats.json"
        with open(group_file, 'w', encoding='utf-8') as f:
            json.dump({
                'export_date': datetime.now().isoformat(),
                'total_group_chats': len(self.group_chats),
                'chats': self.group_chats
            }, f, indent=2, ensure_ascii=False)
        print(f"✅ group_chats.json ({len(self.group_chats)} groups)")
        
        # 3. Call Logs
        calls_file = self.output_dir / "call_logs.json"
        with open(calls_file, 'w', encoding='utf-8') as f:
            json.dump({
                'export_date': datetime.now().isoformat(),
                'total_calls': len(self.call_logs),
                'statistics': {
                    'voice_calls': len([c for c in self.call_logs if c['call_type'] == 'voice']),
                    'video_calls': len([c for c in self.call_logs if c['call_type'] == 'video']),
                    'incoming_calls': len([c for c in self.call_logs if c['direction'] == 'incoming']),
                    'outgoing_calls': len([c for c in self.call_logs if c['direction'] == 'outgoing']),
                    'total_duration': sum(c.get('duration_seconds', 0) for c in self.call_logs)
                },
                'calls': self.call_logs
            }, f, indent=2, ensure_ascii=False)
        print(f"✅ call_logs.json ({len(self.call_logs)} calls)")
        
        # 4. Contacts
        contacts_file = self.output_dir / "contacts.json"
        with open(contacts_file, 'w', encoding='utf-8') as f:
            json.dump({
                'export_date': datetime.now().isoformat(),
                'total_contacts': len(self.contacts),
                'contacts': self.contacts
            }, f, indent=2, ensure_ascii=False)
        print(f"✅ contacts.json ({len(self.contacts)} contacts)")
        
        # 5. Media
        media_file = self.output_dir / "media.json"
        media_stats = {}
        for media_item in self.media:
            media_type = media_item['type'].split('/')[0] if '/' in media_item['type'] else media_item['type']
            media_stats[media_type] = media_stats.get(media_type, 0) + 1
        
        with open(media_file, 'w', encoding='utf-8') as f:
            json.dump({
                'export_date': datetime.now().isoformat(),
                'total_media': len(self.media),
                'statistics': {
                    'by_type': media_stats,
                    'total_size_bytes': sum(m.get('size_bytes', 0) for m in self.media)
                },
                'media': self.media
            }, f, indent=2, ensure_ascii=False)
        print(f"✅ media.json ({len(self.media)} items)")
        
        # 6. Master File
        master_file = self.output_dir / "master.json"
        master_data = {
            'export_info': {
                'export_date': datetime.now().isoformat(),
                'extractor_version': 'Comprehensive Signal Extractor v2.0',
                'description': 'Complete Signal data export with enhanced content decoding'
            },
            'summary': {
                'individual_chats': len(self.individual_chats),
                'group_chats': len(self.group_chats),
                'call_logs': len(self.call_logs),
                'contacts': len(self.contacts),
                'media': len(self.media),
                'total_messages': sum(
                    chat['chat_info']['message_count'] 
                    for chat in self.individual_chats + self.group_chats
                ),
                'total_attachments': sum(
                    chat['chat_info'].get('attachment_count', 0)
                    for chat in self.individual_chats + self.group_chats
                )
            },
            'data': {
                'individual_chats': self.individual_chats,
                'group_chats': self.group_chats,
                'call_logs': self.call_logs,
                'contacts': self.contacts,
                'media': self.media
            }
        }
        
        with open(master_file, 'w', encoding='utf-8') as f:
            json.dump(master_data, f, indent=2, ensure_ascii=False)
        print(f"✅ master.json (complete dataset)")

    def process_signal_data(self, search_path):
        """Main processing function"""
        try:
            print("🚀 Starting COMPREHENSIVE Signal data extraction...")
            
            # Find all Signal files
            found_files = self.find_signal_files(search_path)
            
            # Get the best database to use
            db_path, db_type = self.get_best_database(found_files)
            
            if not db_path:
                print("❌ No usable Signal database found!")
                return
            
            # Test database connection
            if not self.test_database_connection(db_path):
                print("❌ Cannot connect to database!")
                return
            
            print(f"🗄️ Processing database: {os.path.basename(db_path)} ({db_type})")
            
            # Connect and extract data
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Extract data in order
            self.extract_recipients(cursor)
            self.extract_threads(cursor)
            self.extract_attachments(cursor)  # Extract attachments before messages
            self.extract_messages(cursor)
            self.extract_call_logs(cursor)
            
            conn.close()
            
            # Clean up temporary files
            if db_path.endswith('.decrypted_temp'):
                os.remove(db_path)
            
            # Save all JSON files
            self.save_json_files()
            
            print("\n🎉 COMPREHENSIVE extraction completed successfully!")
            print(f"📁 Output folder: {self.output_dir.absolute()}")
            print(f"📊 Results:")
            print(f"   ✅ individual_chats.json - {len(self.individual_chats)} chats")
            print(f"   ✅ group_chats.json - {len(self.group_chats)} groups")
            print(f"   ✅ call_logs.json - {len(self.call_logs)} calls")
            print(f"   ✅ contacts.json - {len(self.contacts)} contacts")
            print(f"   ✅ media.json - {len(self.media)} items")
            print(f"   ✅ master.json - complete dataset")
            
            # Show improvement summary
            total_messages = sum(
                chat['chat_info']['message_count'] 
                for chat in self.individual_chats + self.group_chats
            )
            total_attachments = sum(
                chat['chat_info'].get('attachment_count', 0)
                for chat in self.individual_chats + self.group_chats
            )
            
            print(f"\n📈 Extraction Summary:")
            print(f"   📱 Total Messages: {total_messages}")
            print(f"   📎 Total Attachments: {total_attachments}")
            print(f"   📞 Total Calls: {len(self.call_logs)}")
            print(f"   👥 Total Contacts: {len(self.contacts)}")
            
        except Exception as e:
            print(f"❌ Error during extraction: {e}")
            print(traceback.format_exc())


def main():
    print("=" * 80)
    print("🔧 COMPREHENSIVE Signal Data Extractor")
    print("=" * 80)
    print("✅ Fixes empty messages and base64 decoding")
    print("✅ Links media files to messages properly") 
    print("✅ Extracts phone numbers correctly")
    print("✅ Handles call logs with duration")
    print("✅ Better group chat detection")
    print("✅ Comprehensive message type handling")
    print()
    
    search_path = input("📂 Enter path to your Android dump: ").strip().strip('"')
    
    if not search_path:
        print("❌ No path provided!")
        return
    
    if not os.path.exists(search_path):
        print(f"❌ Path not found: {search_path}")
        return
    
    try:
        extractor = ComprehensiveSignalExtractor()
        extractor.process_signal_data(search_path)
        
        print("\n✨ COMPREHENSIVE extraction complete!")
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")


if __name__ == "__main__":
    main()
