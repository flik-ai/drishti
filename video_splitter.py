import subprocess
from pathlib import Path
import shutil
import json
from datetime import datetime, timedelta
from video_analyzer import analyze_video_chunk
import firebase_admin
from firebase_admin import firestore
from google.cloud import pubsub_v1
import uuid
from datetime import datetime, timezone


publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path("drishti-ea59b", "dispatcher")



# Application Default credentials are automatically created.
app = firebase_admin.initialize_app()
db = firestore.client()

def split_video(
    video_path: str,
    output_dir: str,
    chunk_duration: int = 5,
    overlap: int = 1,
    start_utc_time: str = None  # Format: "2024-01-15T10:30:00Z"
) -> list:
    """
    Splits a video into overlapping chunks with UTC timestamps.

    Args:
        video_path (str): Path to the input video file.
        output_dir (str): Directory where the output chunks will be saved.
        chunk_duration (int): Duration of each chunk in seconds. Default is 5.
        overlap (int): Overlap between chunks in seconds. Default is 1.
        start_utc_time (str): UTC start time for the first chunk. If None, uses current UTC time.

    Returns:
        list: A list of dictionaries, each containing chunk_path, start_time, end_time, 
              start_utc_time, and end_utc_time.
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)

    if not video_path.is_file():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if overlap >= chunk_duration:
        raise ValueError("Overlap must be smaller than chunk duration.")

    # Parse or set the start UTC time
    if start_utc_time:
        if isinstance(start_utc_time, datetime):
            start_datetime = start_utc_time
        else:
            try:
                # Handle different ISO format variations
                if start_utc_time.endswith('Z'):
                    start_utc_time_clean = start_utc_time.replace('Z', '+00:00')
                    start_datetime = datetime.fromisoformat(start_utc_time_clean)
                else:
                    start_datetime = datetime.fromisoformat(start_utc_time)
            except ValueError as e:
                raise ValueError(f"start_utc_time must be in ISO format (e.g., '2024-01-15T10:30:00Z'). Error: {e}")
    else:
        start_datetime = datetime.utcnow().replace(tzinfo=None)

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Chunks will be saved in: {output_dir.resolve()}")
    print(f"First chunk starts at UTC: {start_datetime.isoformat()}Z")

    ffprobe_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
    ]
    result = subprocess.run(ffprobe_cmd, capture_output=True, text=True, check=True)
    total_duration = float(result.stdout)
    print(f"Video duration: {total_duration:.2f} seconds")

    step = chunk_duration - overlap
    start_time = 0
    counter = 1
    chunk_info_list = []

    while True:
        current_chunk_duration = min(chunk_duration, total_duration - start_time)

        # If the remaining duration is too small to be a meaningful new chunk, break.
        if current_chunk_duration < 0.5 and counter > 1:
            break

        # If start_time has exceeded total_duration, or if the current_chunk_duration is zero or negative, break.
        if start_time >= total_duration or current_chunk_duration <= 0:
            break

        end_time = start_time + current_chunk_duration
        output_filename = output_dir / f"chunk_{counter:03d}.mp4"

        # Calculate UTC timestamps
        chunk_start_utc = start_datetime + timedelta(seconds=start_time)
        chunk_end_utc = start_datetime + timedelta(seconds=end_time)

        ffmpeg_cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-ss", str(start_time),
            "-t", str(current_chunk_duration),
            "-c", "copy",
            str(output_filename),
            "-y",
            "-hide_banner",
            "-loglevel", "error"
        ]

        print(f"Creating chunk {counter} from {start_time:.2f}s to {end_time:.2f}s (duration: {current_chunk_duration:.2f}s)...")
        print(f"  UTC: {chunk_start_utc.isoformat()}Z to {chunk_end_utc.isoformat()}Z")
        subprocess.run(ffmpeg_cmd, check=True)

        chunk_info_list.append({
            "chunk_path": str(output_filename),
            "start_time": start_time,
            "end_time": end_time,
            "start_utc_time": chunk_start_utc.isoformat() + "Z",
            "end_utc_time": chunk_end_utc.isoformat() + "Z"
        })

        start_time += step
        counter += 1

    print(f"Video splitting complete. Created {len(chunk_info_list)} chunks.")
    return chunk_info_list

def main():
    try:
        input_file = "stampede_track.mp4"
        output_folder = "video_chunks"
        analysis_output_file = "video_analysis.json"
        analysis_results = []

        if not Path(input_file).exists():
            print(f"'{input_file}' not found. Creating a dummy 60-second test video.")
            dummy_cmd = [
                'ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=60:size=1280x720:rate=30',
                '-y', input_file, '-hide_banner', '-loglevel', 'error'
            ]
            subprocess.run(dummy_cmd, check=True)

        # Split video and get chunk information with UTC timestamps
        current_utc = datetime.now(timezone.utc)
        start_utc_str = current_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        chunks = split_video(
            video_path=input_file,
            output_dir=output_folder,
            chunk_duration=5,
            overlap=1,
            start_utc_time=start_utc_str
        )

        # Analyze each chunk synchronously
        print("Starting synchronous analysis of video chunks...")
        for chunk in chunks:
            analysis = analyze_video_chunk(chunk["chunk_path"], chunk["start_time"], chunk["end_time"])
            
            # Check if analysis failed (contains error key)
            if "error" in analysis:
                print(f"Skipping chunk {chunk['chunk_path']} due to analysis error: {analysis['error']}")
                continue
            
            # Check if analysis has the expected structure
            if "needs_security_intervention" not in analysis:
                print(f"Skipping chunk {chunk['chunk_path']} - invalid analysis structure")
                continue
            
            # Simple destructuring using ** operator
            flattened_result = {
                **chunk,  # Unpack all chunk fields
                **analysis  # Unpack all analysis fields
            }
            
            analysis_results.append(flattened_result)
            
            # Store in Firestore with flattened structure
            uu_id = str(uuid.uuid4())
            doc_ref = db.collection("events").document(uu_id)
            doc_ref.set(flattened_result)
            
            if analysis["needs_security_intervention"] == "yes":
                future = publisher.publish(topic_path, json.dumps(analysis).encode("utf-8"))
                print(f"Published message ID: {future.result()}")

        with open(analysis_output_file, 'w') as f:
            json.dump(analysis_results, f, indent=4)

        print(f"\n✅ All analysis complete. Results saved to {analysis_output_file}")

    except (FileNotFoundError, ValueError, subprocess.CalledProcessError) as e:
        print(f"\n❌ An error occurred: {e}")

    finally:
        # Clean up the dummy video if it was created
        if "dummy_cmd" in locals() and Path(input_file).exists():
            Path(input_file).unlink()
            print(f"Cleaned up dummy video: {input_file}")
        # Clean up the video chunks directory
        if Path(output_folder).exists():
            shutil.rmtree(output_folder)
            print(f"Cleaned up chunk directory: {output_folder}")

if __name__ == "__main__":
    main()