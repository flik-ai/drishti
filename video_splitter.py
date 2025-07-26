import subprocess
from pathlib import Path
import shutil
import json
from video_analyzer import analyze_video_chunk

def split_video(
    video_path: str,
    output_dir: str,
    chunk_duration: int = 5,
    overlap: int = 1
) -> list:
    """
    Splits a video into overlapping chunks.

    Args:
        video_path (str): Path to the input video file.
        output_dir (str): Directory where the output chunks will be saved.
        chunk_duration (int): Duration of each chunk in seconds. Default is 5.
        overlap (int): Overlap between chunks in seconds. Default is 1.

    Returns:
        list: A list of dictionaries, each containing chunk_path, start_time, and end_time.
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)

    if not video_path.is_file():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if overlap >= chunk_duration:
        raise ValueError("Overlap must be smaller than chunk duration.")

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Chunks will be saved in: {output_dir.resolve()}")

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
        # A threshold like 0.5 seconds might be reasonable to avoid tiny, invalid chunks.
        if current_chunk_duration < 0.5 and counter > 1:
            break

        # If start_time has exceeded total_duration, or if the current_chunk_duration is zero or negative, break.
        if start_time >= total_duration or current_chunk_duration <= 0:
            break

        end_time = start_time + current_chunk_duration
        output_filename = output_dir / f"chunk_{counter:03d}.mp4"

        ffmpeg_cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-ss", str(start_time),
            "-t", str(current_chunk_duration), # Use current_chunk_duration here
            "-c", "copy",
            str(output_filename),
            "-y",
            "-hide_banner",
            "-loglevel", "error"
        ]

        print(f"Creating chunk {counter} from {start_time:.2f}s to {end_time:.2f}s (duration: {current_chunk_duration:.2f}s)...")
        subprocess.run(ffmpeg_cmd, check=True)

        chunk_info_list.append({
            "chunk_path": str(output_filename),
            "start_time": start_time,
            "end_time": end_time
        })

        start_time += step
        counter += 1

    print(f"\n✅ Video splitting complete. Created {len(chunk_info_list)} chunks.")
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

        # Split video and get chunk information
        chunks = split_video(
            video_path=input_file,
            output_dir=output_folder,
            chunk_duration=5,
            overlap=1
        )

        # Analyze each chunk synchronously
        print("Starting synchronous analysis of video chunks...")
        for chunk in chunks:
            analysis = analyze_video_chunk(chunk["chunk_path"], chunk["start_time"], chunk["end_time"])
            analysis_results.append({
                "start_time": chunk["start_time"],
                "end_time": chunk["end_time"],
                "analysis": analysis
            })

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