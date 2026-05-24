

#  **EvidenX (CLI)** : Command-Line Forensic Extraction Suite

---

##  Overview

**EvidenX (CLI)** is a modular **digital forensic extraction framework** designed for only **rooted Android data dumps**.
It automates the **decryption, parsing, and normalization** of application databases from **WhatsApp**, **Signal**, and **Instagram**, producing clean, structured **JSON datasets** ready for analysis, visualization, or case documentation.

The suite focuses on reliability, transparency, and evidentiary accuracy — ensuring every step of the process is traceable, logged, and reproducible.
EvidenX operates fully offline and is intended for examiners handling logical or full-filesystem extractions obtained from rooted Android devices.

---

## Core Philosophy

> Digital evidence shouldn’t just be decrypted — it should be **understood**.
> EvidenX transforms raw application data into structured narratives of user activity, while maintaining forensic integrity and auditability at every level.

---

## Key Capabilities

* **Rooted Android Data Support** — Operates directly on `/data` partitions or full logical dumps extracted from rooted devices.
* **End-to-End Automation** — From cryptographic key recovery to final JSON export.
* **Multi-App Coverage** — Dedicated extractors for WhatsApp, Signal, and Instagram.
* **Dynamic Schema Recognition** — Adapts automatically to app database updates.
* **Media-Level Correlation** — Links every message to its referenced media asset.
* **Integrity-Driven Logging** — SHA-256 hashing, timestamping, and process audit logs.
* **Modular CLI Design** — Each extractor can run independently or through a unified orchestrator.
* **Error-Resilient Execution** — Handles partial dumps and corrupted tables gracefully.

---

##  Project Structure

```
EvidenX(CLI)/
│
├── orchestrator.py                # CLI launcher and module controller
│
├── WhatsApp_JSON/
│   ├── extract_whatsapp_data.py   # WhatsApp decryption + parser
│   ├── setup_dependencies.py
│   ├── requirements.txt
│
├── Signal_JSON/
│   ├── new.py                     # Signal extractor & database decoder
│   ├── setup_dependencies.py
│   ├── requirements.txt
│
└── Instagram_JSON/
    ├── Instagram_Extractor.py
    ├── Module1.py / Module2.py
    ├── setup_dependencies.py
    └── requirements.txt
```

Each module is fully isolated, allowing independent updates, testing, and execution.
The `orchestrator.py` script serves as the control layer — automatically identifying the app type and launching the respective parser.

---

##  Technical Stack

| Layer                    | Technology                        |
| ------------------------ | --------------------------------- |
| **Language**             | Python 3.x                        |
| **Database Parsing**     | SQLite3, SQLCipher (Signal)       |
| **Decryption**           | AES-GCM via `cryptography`        |
| **Compression Handling** | PyZipper                          |
| **Data Parsing**         | BeautifulSoup4, lxml, json        |
| **Metadata Integrity**   | hashlib (SHA-256), UTC timestamps |

---

##  Module-Wise Functionality

###  **WhatsApp Extractor**

* Decrypts `msgstore.db.crypt14` / `msgstore.db.crypt15` using the recovered key.
* Parses messages, groups, contacts, calls, and associated media paths.
* Extracts:

  * Sender/Receiver metadata
  * Timestamps (converted to UTC)
  * Media file references and absolute paths
* Generates:

  ```
  whatsapp_master_data.json
  whatsapp_chats.json
  whatsapp_contacts.json
  whatsapp_media_summary.json
  ```

### 🔵 **Signal Extractor**

* Retrieves AES-GCM key from Android Keystore and preferences XML.
* Decrypts Signal’s `signal.db` (SQLCipher) database.
* Extracts messages, calls, contacts, groups, and attachments.
* Handles multiple device IDs and ephemeral message records.
* Outputs:

  ```
  individual_chats.json
  group_chats.json
  contacts.json
  call_logs.json
  master.json
  ```

### 🟣 **Instagram Extractor**

* Combines multi-pass analysis (Module V5 + V7) for account and session reconstruction.
* Extracts user credentials, session tokens, cached posts, linked profiles, and follow lists.
* Produces:

  ```
  logged_in_user_profile.json
  session_ids.json
  discovery_timeline.json
  master.json
  ```

---

## 🔐 Data Requirements

EvidenX requires **rooted Android extractions** containing:

| Application   | Required Directories / Files                                                                  |
| ------------- | --------------------------------------------------------------------------------------------- |
| **WhatsApp**  | `/data/data/com.whatsapp/`, `/data/user_de/0/com.whatsapp/`, `/data/system/users/0/keystore/` |
| **Signal**    | `/data/data/org.thoughtcrime.securesms/`, `/data/system/users/0/keystore/`, `/data/misc/`     |
| **Instagram** | `/data/data/com.instagram.android/`, `/data/system/users/0/`                                  |

Ensure dumps include the **app database**, **shared preferences**, and **keystore files** for key recovery.

---

## 🚀 Usage

### 1️⃣ Install Dependencies

```bash
python setup_dependencies.py
```

###  Run Orchestrator

```bash
python orchestrator.py
```

The orchestrator will prompt for:

* Path to the extracted Android `/data` directory.
* Target application (WhatsApp, Signal, or Instagram).
* Output directory for JSON exports.

### 3️⃣ Run Individual Extractors (Optional)

Each module can be executed independently for focused workflows:

```bash
cd WhatsApp_JSON
python extract_whatsapp_data.py
```

---

## 🧾 Output Schema

```
EvidenX_Output/
│
├── whatsapp_data_output/
│   ├── whatsapp_chats.json
│   ├── whatsapp_contacts.json
│   └── whatsapp_media_summary.json
│
├── signal_export_comprehensive/
│   ├── master.json
│   ├── individual_chats.json
│   └── contacts.json
│
└── instagram_master_output_<timestamp>/
    ├── master.json
    └── discovery_timeline.json
```

Each JSON file follows a uniform, nested structure:

```json
{
  "metadata": {
    "extraction_time_utc": "2025-10-29T21:31:14Z",
    "device_id": "Pixel_4a_dump_001",
    "tool_version": "1.2.0"
  },
  "data": [
    {
      "sender": "John Doe",
      "receiver": "Jane Doe",
      "timestamp": "2025-10-27T09:41:52Z",
      "message": "Hey, see you soon!",
      "media_path": "/EvidenX_Output/whatsapp/media/IMG_2025.jpg"
    }
  ]
}
```

---

## 🧩 Logging & Integrity

* Each extraction generates a `process_log.txt` with timestamps, module states, and event codes.
* Every exported JSON file includes SHA-256 hash values for integrity verification.
* Decryption operations are ephemeral — temporary plaintext databases are securely deleted post-execution.
* The orchestrator creates a global manifest containing:

  * Extraction date/time
  * Tool version
  * Case ID (if specified)
  * Total artifacts recovered per app

---

## 🧪 Testing & Validation

EvidenX has been validated on:

* Android 9 → 14 rooted filesystem dumps
* WhatsApp v2.23 → v2.24 schema variations
* Signal SQLCipher v7/v8
* Instagram app data v350+

Regression testing ensures schema-change compatibility across app versions.

---

## 🔒 Forensic Integrity Controls

| Control                        | Description                                                |
| ------------------------------ | ---------------------------------------------------------- |
| **Immutable Reads**            | All files opened in read-only mode.                        |
| **Chain of Custody Logging**   | Every stage logged with timestamps.                        |
| **Temporary File Cleanup**     | Sensitive decrypted artifacts auto-purged post-processing. |
| **Cryptographic Verification** | SHA-256 hashing per export and manifest-level checksum.    |
| **UTC Normalization**          | All timestamps normalized for cross-app correlation.       |

---

## 🧭 Development Roadmap

* 🔄 Cross-application timeline reconstruction
* 🧮 JSON-to-visual correlation integration with EvidenX (GUI)
* ☁️ Case management backend for multi-examiner workflows
* 🧰 Additional module support (Telegram, Messenger, Snapchat)

---

## 🧾 License

Distributed under the **MIT License** — use and modify responsibly for lawful digital forensics or research purposes.

---

## ⚡ **EvidenX (CLI)** — *Extract • Decrypt • Illuminate*

> “Behind every byte, there’s a story. EvidenX helps you tell it.”

---


