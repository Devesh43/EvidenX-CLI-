# WhatsApp Data & Media Extractor - Complete Edition

Extract WhatsApp chat data AND all media files directly to your VS Code workspace. This enhanced version creates a comprehensive media folder with every piece of media from your WhatsApp backup!

## 🎬 New Media Features

### What Gets Extracted
- **All Images**: JPG, PNG, GIF, WebP, etc.
- **All Videos**: MP4, AVI, MOV, WebM, etc.
- **All Audio**: MP3, WAV, AAC, etc.
- **Voice Notes**: Opus, AMR files
- **Documents**: PDF, DOC, XLS, PPT, etc.
- **Other Files**: Any other media type

### Media Organization
\`\`\`
whatsapp_media/
├── images/          # All image files
├── videos/          # All video files  
├── audio/           # Music and audio files
├── voice_notes/     # WhatsApp voice messages
├── documents/       # PDF, Office docs, etc.
└── other/           # Other file types
\`\`\`

## 🚀 Quick Start

1. **Install Dependencies**
   \`\`\`bash
   python setup_dependencies.py
   \`\`\`

2. **Run the Enhanced Extractor**
   \`\`\`bash
   python extract_whatsapp_data_with_media.py
   \`\`\`

3. **Enter your WhatsApp backup folder path when prompted**

## 📁 Complete Output Structure

### Data Files (JSON)
\`\`\`
whatsapp_data_output/
├── whatsapp_master_data.json           # Complete dataset
├── whatsapp_chats.json                 # All messages
├── whatsapp_contacts.json              # All contacts
├── whatsapp_groups.json                # All groups
├── whatsapp_call_logs.json             # Call history
├── whatsapp_media_index.json           # Media catalog
├── media_images.json                   # Image file list
├── media_videos.json                   # Video file list
├── media_audio.json                    # Audio file list
├── media_voice_notes.json              # Voice note list
├── media_documents.json                # Document list
└── individual_chats/                   # Per-chat files
\`\`\`

### Media Files (Actual Files)
\`\`\`
whatsapp_media/
├── images/          # All extracted images
├── videos/          # All extracted videos
├── audio/           # All extracted audio
├── voice_notes/     # All voice messages
├── documents/       # All documents
└── other/           # Other file types
\`\`\`

## 🔍 Media Index Features

### Complete Source Tracking
Each media file includes:
- **Original filename** in WhatsApp backup
- **Source path** within the ZIP file
- **Extracted filename** (with conflict resolution)
- **File size** and **hash** for deduplication
- **Media type** classification
- **MIME type** detection
- **Extraction timestamp**

### Example Media Index Entry
\`\`\`json
{
  "a1b2c3d4": {
    "original_filename": "IMG_20241201_143022.jpg",
    "extracted_filename": "IMG_20241201_143022.jpg",
    "source_path_in_zip": "WhatsApp/Media/WhatsApp Images/IMG_20241201_143022.jpg", 
    "source_type": "whatsapp_media",
    "media_type": "images",
    "file_size": 2048576,
    "file_hash": "a1b2c3d4e5f6g7h8",
    "extracted_path": "whatsapp_media/images/IMG_20241201_143022.jpg",
    "extraction_date": "2025-01-15T12:30:45",
    "mime_type": "image/jpeg"
  }
}
\`\`\`

## 📊 Enhanced Statistics

### Media Statistics
\`\`\`json
{
  "total_files": 1247,
  "images": 856,
  "videos": 234,
  "audio": 67,
  "voice_notes": 45,
  "documents": 32,
  "other": 13,
  "total_size": 2684354560
}
\`\`\`

## 🎯 What's New vs Basic Version

| Feature | Basic Version | Media Version |
|---------|---------------|---------------|
| Chat Messages | ✅ | ✅ |
| Contacts | ✅ | ✅ |
| Groups | ✅ | ✅ |
| Call Logs | ✅ | ✅ |
| **Media Extraction** | ❌ | ✅ |
| **Media Index** | ❌ | ✅ |
| **Source Tracking** | ❌ | ✅ |
| **File Organization** | ❌ | ✅ |
| **Deduplication** | ❌ | ✅ |
| **Media Statistics** | ❌ | ✅ |

## 🔧 Advanced Features

### Smart File Handling
- **Conflict Resolution**: Duplicate filenames get numbered suffixes
- **Hash-based Deduplication**: Identical files detected by content
- **MIME Type Detection**: Automatic file type classification
- **Size Tracking**: Complete storage statistics

### Source Path Tracking
Every media file shows exactly where it came from:
\`\`\`
Source: WhatsApp/Media/WhatsApp Images/Sent/IMG_20241201_143022.jpg
Local: whatsapp_media/images/IMG_20241201_143022.jpg
\`\`\`

### Performance Optimized
- **Streaming Extraction**: Memory-efficient for large backups
- **Progress Indicators**: Shows extraction progress
- **Error Recovery**: Continues on individual file failures
- **Batch Processing**: Handles thousands of files efficiently

## 🛠️ Troubleshooting

### Large Backup Issues
- **Memory**: Script uses streaming to handle large files
- **Disk Space**: Ensure enough space for media extraction
- **Time**: Large backups may take 10-30 minutes

### File Conflicts
- Duplicate names automatically get `_1`, `_2` suffixes
- Original names preserved in media index
- Hash tracking prevents true duplicates

### Partial Extraction
If interrupted, you can:
- Check `media_stats` in master JSON for progress
- Re-run to continue (existing files skipped)
- Individual file errors don't stop full extraction

## 💡 VS Code Integration Tips

### Browse Media
\`\`\`bash
# Open media folder in VS Code
code whatsapp_media/

# Search for specific file types
code whatsapp_data_output/media_images.json
\`\`\`

### Search Across Data
- Use VS Code's search to find files by name
- Filter JSON data by date, contact, etc.
- Compare multiple extractions side-by-side

---

**🎉 Now you have EVERYTHING from your WhatsApp backup!**
- All chat data in organized JSON files
- Every media file extracted and organized
- Complete source tracking and statistics
- Full integration with VS Code workflow
