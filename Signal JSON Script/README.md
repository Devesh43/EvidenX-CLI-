# Signal Database Extractor - Direct Decryption

Extract Signal chat data from Android data dumps by directly decrypting the Signal database. No passphrase required - automatically finds keys and decrypts everything!

## 🚀 Quick Start

1. **Install Dependencies**
   \`\`\`bash
   python setup_dependencies.py
   \`\`\`

2. **Run the Extractor**
   \`\`\`bash
   python extract_signal_db.py
   \`\`\`

3. **Enter your Android data dump folder path when prompted**

## 🔑 How It Works

This extractor implements the Signal Android database decryption method based on security research. It:

1. **Locates Signal Files** in your Android data dump:
   - Database: `data/data/org.thoughtcrime.securesms/databases/signal.db`
   - Keystore: `data/keystore/user_0/*_USRSKEY_SignalSecret`
   - Preferences: `data/data/org.thoughtcrime.securesms/shared_prefs/org.thoughtcrime.securesms_preferences.xml`

2. **Extracts Encryption Key** from Android keystore (16 bytes from offset 0x2D-0x3C)

3. **Decrypts Database Key** using AES-GCM with the keystore key and encrypted secret from preferences

4. **Opens Database** using SQLCipher with Signal's specific parameters:
   - `PRAGMA cipher_default_kdf_iter = 1`
   - `PRAGMA cipher_default_page_size = 4096`

5. **Extracts All Data** and converts to structured JSON

## 📁 Output Files

Creates a `signal_data_output` folder with:

### Master File
- `signal_master_data.json` - Complete dataset with all information

### Category Files
- `signal_chats.json` - All conversations and messages
- `signal_contacts.json` - All contacts with numbers
- `signal_call_logs.json` - Call history with statistics

### Individual Files
- `individual_chats/` - Separate JSON file for each conversation

## 🎯 What Gets Extracted

### 1. Messages & Chats
- All individual conversations
- Message text, timestamps, direction
- Sent/received status with proper Signal type mapping
- Date-organized message history

### 2. Contacts
- Phone numbers and display names
- Automatic contact resolution in messages

### 3. Call Logs
- Call history with timestamps
- Voice/video call detection
- Call duration and direction
- Contact name resolution

## 🔧 Requirements

- Python 3.7+
- SQLCipher support (`pysqlcipher3`)
- Android data dump with Signal data
- Root access was needed to create the original dump

## 📊 Technical Details

### Encryption Process (Reversed)
1. Signal uses SQLCipher to encrypt the database
2. The SQLCipher key is encrypted with AES-GCM
3. The AES-GCM key is stored in Android keystore as `USERKEY_SignalSecret`
4. The encrypted SQLCipher key is stored in preferences as `pref_database_encrypted_secret`

### Decryption Process
1. Extract 16-byte key from keystore (offset 0x2D-0x3C)
2. Decode base64 encrypted secret from preferences XML
3. Use AES-GCM to decrypt: IV + ciphertext + auth_tag (last 16 bytes)
4. Use decrypted key to open SQLCipher database

## 🛠️ Troubleshooting

### Common Issues

1. **"SQLCipher not available"**
   \`\`\`bash
   sudo apt-get install sqlcipher libsqlcipher-dev
   pip install pysqlcipher3
   \`\`\`

2. **"Missing required files"**
   - Ensure your Android dump includes `/data/data/org.thoughtcrime.securesms/`
   - Check for keystore files in `/data/keystore/user_0/`
   - Verify preferences XML exists

3. **"Database query failed - incorrect key"**
   - Keystore extraction may have failed
   - AES-GCM decryption parameters might be wrong
   - Database may be corrupted

4. **"No message table found"**
   - Database structure may be different in newer Signal versions
   - Check if database decrypted correctly

### Debug Tips

- The extractor shows detailed progress for each step
- Check if all three required files are found
- Verify keystore key extraction (should be 16 bytes)
- Confirm preferences XML contains `pref_database_encrypted_secret`

## 🔒 Security & Privacy

- **Local Processing**: All decryption happens on your machine
- **No Network Access**: No data sent to external servers
- **Key Extraction**: Keystore keys are extracted but not stored
- **Temporary Files**: Automatically cleaned up
- **Original Files**: Never modified

## ⚡ Android Data Dump Requirements

To use this extractor, you need an Android data dump that includes:

1. **Full `/data/data/org.thoughtcrime.securesms/` directory**
2. **Keystore files from `/data/keystore/user_0/`**
3. **Root access** was required to create the original dump

Common dump methods:
- `adb pull /data/data/org.thoughtcrime.securesms/`
- `dd` command with root access
- Custom recovery tools
- Forensic imaging tools

## 📋 Supported Signal Versions

This method works with Signal for Android versions that use:
- SQLCipher database encryption
- Android Keystore for key management
- Preferences-based configuration storage

Tested with Signal versions up to early 2024. Newer versions may require updates to the extraction logic.

---

**Made for forensic analysis and data recovery - Use responsibly!**

**Disclaimer**: This tool is for legitimate data recovery and analysis purposes only. Ensure you have proper authorization before analyzing any device or data.
