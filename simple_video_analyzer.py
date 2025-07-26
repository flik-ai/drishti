#!/usr/bin/env python3
"""
Simple Video Analysis Script
Extracts frames from video every N seconds, analyzes with Gemini Vision API, 
and returns raw JSON results with timestamps.
"""

import cv2
import time
import json
from datetime import datetime, timedelta
from google import genai
from google.genai.types import Part
import os

def analyze_video_file(video_path: str, interval_seconds: int = 15, output_file: str = None):
    """
    Main function to analyze video file
    
    Args:
        video_path: Path to video file
        interval_seconds: Extract frame every N seconds  
        output_file: Optional JSON output file
        
    Returns:
        List of raw API responses with timestamps
    """
    
    # Initialize Gemini client
    client = genai.Client(vertexai=True, project='projectvertex-466503', location='us-central1')
    
    # Analysis prompt
    analysis_prompt = """
    From the image, analyze and return ONLY a JSON object with this structure:
    {
        "crowd_density": "low|medium|high|severe",
        "crowd_flow": "unrestricted|moderately_restricted|severely_restricted", 
        "estimated_count": number_or_null,
        "fire_smoke_detected": "yes|no",
        "congested_entry_exits": "yes|no",
        "safety_level": "safe|moderate_risk|high_risk|critical",
        "additional_observations": "brief description"
    }
    """
    
    # Check if video exists
    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        return []
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Could not open video: {video_path}")
        return []
    
    # Get video info
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    
    print(f"🎬 Video: {os.path.basename(video_path)}")
    print(f"📊 FPS: {fps:.1f} | Duration: {duration:.1f}s | Frames: {total_frames}")
    print(f"📸 Extracting every {interval_seconds}s")
    
    # Calculate frame extraction parameters
    frame_interval = int(fps * interval_seconds)
    video_start_time = datetime.now()
    
    results = []
    frame_number = 0
    extracted_count = 0
    total_analysis_time = 0
    
    print("\n🚀 Starting analysis...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Extract frame at intervals
        if frame_number % frame_interval == 0:
            extracted_count += 1
            seconds_elapsed = frame_number / fps
            frame_timestamp = video_start_time + timedelta(seconds=seconds_elapsed)
            
            print(f"\n📸 Frame {extracted_count} at {seconds_elapsed:.1f}s")
            
            # Encode frame
            start_time = time.time()
            success, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            if not success:
                print("❌ Failed to encode frame")
                frame_number += 1
                continue
            
            # Analyze with Gemini
            try:
                api_start = time.time()
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        analysis_prompt,
                        Part.from_bytes(data=encoded.tobytes(), mime_type="image/jpeg"),
                    ],
                )
                api_time = time.time() - api_start
                total_time = time.time() - start_time
                
                # Get raw response text
                raw_response = response.text.strip()
                
                # Clean up markdown formatting if present
                if raw_response.startswith('```json'):
                    raw_response = raw_response.replace('```json', '').replace('```', '').strip()
                elif raw_response.startswith('```'):
                    raw_response = raw_response.replace('```', '').strip()
                
                print(f"✅ Analysis completed: {total_time:.2f}s")
                print(f"🕒 Timestamp: {frame_timestamp.isoformat()}")
                print(f"📄 Raw JSON Response:")
                print(f"{raw_response}")
                print("-" * 80)
                
                # Store result with raw response
                result = {
                    "timestamp": frame_timestamp.isoformat(),
                    "seconds_elapsed": round(seconds_elapsed, 2),
                    "frame_number": frame_number,
                    "extracted_index": extracted_count,
                    "raw_json_response": raw_response,
                    "timing": {
                        "api_call": round(api_time, 3),
                        "total_time": round(total_time, 3)
                    },
                    "success": True
                }
                
                results.append(result)
                total_analysis_time += total_time
                
            except Exception as e:
                total_time = time.time() - start_time
                print(f"❌ API Error: {e} ({total_time:.2f}s)")
                print(f"🕒 Timestamp: {frame_timestamp.isoformat()}")
                print("-" * 80)
                
                result = {
                    "timestamp": frame_timestamp.isoformat(),
                    "seconds_elapsed": round(seconds_elapsed, 2),
                    "frame_number": frame_number,
                    "extracted_index": extracted_count,
                    "raw_json_response": None,
                    "error": str(e),
                    "timing": {"total_time": round(total_time, 3)},
                    "success": False
                }
                results.append(result)
            
            # Rate limiting
            time.sleep(0.5)
        
        frame_number += 1
    
    cap.release()
    
    # Print summary
    successful = sum(1 for r in results if r['success'])
    avg_time = total_analysis_time / len(results) if results else 0
    
    print(f"\n📊 ANALYSIS COMPLETE:")
    print(f"   🎯 Frames analyzed: {len(results)}")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {len(results) - successful}")
    print(f"   ⏱️  Average time: {avg_time:.2f}s")
    print(f"   📊 Total time: {total_analysis_time:.1f}s")
    
    # Save to file if specified
    if output_file:
        output_data = {
            "metadata": {
                "video_file": os.path.basename(video_path),
                "total_frames_analyzed": len(results),
                "successful_analyses": successful,
                "interval_seconds": interval_seconds,
                "analysis_timestamp": datetime.now().isoformat(),
                "average_response_time": round(avg_time, 3)
            },
            "results": results
        }
        
        try:
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"💾 Results saved: {output_file}")
        except Exception as e:
            print(f"❌ Save failed: {e}")
    
    return results

def main():
    """Command line interface"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python simple_video_analyzer.py <video_path> [interval_seconds] [output_file]")
        print("Example: python simple_video_analyzer.py /path/to/video.mp4 5 results.json")
        return
    
    video_path = sys.argv[1]
    interval_seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    output_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    results = analyze_video_file(video_path, interval_seconds, output_file)
    
    # Show quick summary of raw responses
    if results:
        print(f"\n🎉 Analysis complete! {len(results)} frames processed.")
        print(f"\n📋 RAW JSON RESPONSES SUMMARY:")
        for i, result in enumerate(results):
            if result['success']:
                print(f"\nFrame {i+1} ({result['timestamp']}):")
                print(f"{result['raw_json_response']}")
            else:
                print(f"\nFrame {i+1} ({result['timestamp']}): ERROR - {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main() 