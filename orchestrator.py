import os
import subprocess
import sys
from pathlib import Path

def run_extractor(script_path, data_dump_path, output_base_dir):
    """
    Runs an individual extractor script.

    Args:
        script_path (Path): The full path to the extractor script to run.
        data_dump_path (Path): The path to the Android data dump to pass to the extractor.
        output_base_dir (Path): The base directory where the extractor should save its output.
    """
    print(f"\n{'='*60}")
    print(f" Running extractor: {script_path.name}")
    print(f"   Input data dump: {data_dump_path}")
    print(f"   Output will be generated in: {output_base_dir}")
    print(f"{'='*60}")

    # Ensure the output directory exists
    output_base_dir.mkdir(parents=True, exist_ok=True)

    # To pass the input path to the extractor scripts, we simulate user input
    # by piping it to the script's stdin.
    # Note: For `Instagram_Extractor.py` (MasterExtractor), it asks for case info.
    # We provide empty strings for optional case info to proceed.
    # For `Module1.py` (V5 Instagram Extractor), it asks about media download.
    # We provide 'n' to skip media download to speed up automation.
    input_data = f"{data_dump_path}\n"  # Path for the data dump
    
    # Add extra newlines for optional prompts that some extractors might have
    # (e.g., case info for Instagram Master, media download for V5 Instagram)
    if "Instagram_Extractor.py" in script_path.name:
        input_data += "\n\n\n" # For case_number, examiner_name, evidence_item
    elif "Module1.py" in script_path.name: # V5 Instagram asks for media download
        input_data += "n\n" # Answer 'n' for no to media download

    try:
        # Create a copy of the current environment and force UTF-8 encoding
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'

        # Run the script using subprocess. The cwd is crucial so the script
        # generates output relative to its own folder.
        process = subprocess.run(
            [sys.executable, str(script_path)],
            input=input_data,
            encoding='utf-8',
            capture_output=True,
            check=True,  # Raise an exception for non-zero exit codes
            cwd=output_base_dir, # Set the working directory for the subprocess
            env=env # Pass the modified environment
        )
        print(f" {script_path.name} finished successfully.")
        print("--- STDOUT ---")
        print(process.stdout)
        # Note: STDERR might contain non-error messages (e.g., warnings or info from logging)
        # so printing it conditionally or inspecting it manually might be better for debugging.
        # print("--- STDERR ---")
        # print(process.stderr)

    except subprocess.CalledProcessError as e:
        print(f" ERROR running {script_path.name}. Exit code: {e.returncode}")
        print("--- STDOUT (Error) ---")
        print(e.stdout)
        print("--- STDERR (Error) ---")
        print(e.stderr)
    except FileNotFoundError:
        print(f" ERROR: Python executable not found. Is Python installed and in your PATH?")
    except Exception as e:
        print(f" An unexpected error occurred while running {script_path.name}: {e}")

def main():
    print("=" * 70)
    print(" Forensic Extractor Orchestrator for Social Media Apps")
    print("=" * 70)
    print("This script will run WhatsApp, Signal, and Instagram extractors.")
    print("It assumes all extractor folders are in the same parent directory.")

    # Get the parent directory of this script
    current_script_dir = Path(__file__).resolve().parent

    # Prompt for the Android data dump path
    android_dump_path_str = input("\n Enter the FULL path to the Android data dump folder: ").strip().strip('"')
    android_dump_path = Path(android_dump_path_str)

    if not android_dump_path.exists():
        print(f" Error: The provided Android data dump path does not exist: {android_dump_path}")
        return

    print(f"\nStarting extraction process for data dump: {android_dump_path}")

    # --- Run WhatsApp Extractor ---
    whatsapp_script_dir = current_script_dir / "Whatsapp JSON Script"
    whatsapp_extractor_script = whatsapp_script_dir / "extract_whatsapp_data.py"
    
    if whatsapp_extractor_script.exists():
        run_extractor(whatsapp_extractor_script, android_dump_path, whatsapp_script_dir)
    else:
        print(f" WhatsApp extractor script not found at: {whatsapp_extractor_script}")
        print("Please ensure 'Whatsapp JSON Script' folder is in the same directory as this orchestrator.")

    # --- Run Signal Extractor ---
    signal_script_dir = current_script_dir / "Signal JSON Script"
    signal_extractor_script = signal_script_dir / "new.py" # Assuming new.py is the main script
    
    if signal_extractor_script.exists():
        run_extractor(signal_extractor_script, android_dump_path, signal_script_dir)
    else:
        print(f" Signal extractor script not found at: {signal_extractor_script}")
        print("Please ensure 'Signal JSON Script' folder is in the same directory as this orchestrator.")

    # --- Run Instagram Extractor ---
    instagram_script_dir = current_script_dir / "Instagram JSON script"
    # Assuming Instagram_Extractor.py is the master script that runs V5 and V7
    instagram_extractor_script = instagram_script_dir / "Instagram_Extractor.py"
    
    if instagram_extractor_script.exists():
        run_extractor(instagram_extractor_script, android_dump_path, instagram_script_dir)
    else:
        print(f"⚠️ Instagram extractor script not found at: {instagram_extractor_script}")
        print("Please ensure 'Instagram JSON script' folder is in the same directory as this orchestrator.")

    print("\n" + "="*70)
    print("🎉 All scheduled extractions attempted.")
    print("Check the respective application folders for the generated JSON files.")
    print("="*70)

if __name__ == "__main__":
    main()
