import cv2
import os
import time

# Configuration
IP = "172.16.2.154"
USER = "admin"
PASS = "sss12345"
PORT = 554

# Common Hikvision RTSP urls
URLS = [
    f"rtsp://{USER}:{PASS}@{IP}:{PORT}/Streaming/Channels/101", # Main Stream
    f"rtsp://{USER}:{PASS}@{IP}:{PORT}/Streaming/Channels/102", # Sub Stream
    f"rtsp://{USER}:{PASS}@{IP}:{PORT}/h264/ch1/main/av_stream",
    f"rtsp://{USER}:{PASS}@{IP}:{PORT}/h265/ch1/main/av_stream",
]

# Force TCP
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

print(f"Testing connection to {IP}...")
print("-" * 50)

for rtsp_url in URLS:
    print(f"\nTrying URL: {rtsp_url.replace(PASS, '******')}")
    
    try:
        cap = cv2.VideoCapture(rtsp_url)
        
        if not cap.isOpened():
            print("❌ Failed to open stream.")
            continue
            
        print("✅ Stream opened successfully!")
        
        # Try to read a few frames
        success_count = 0
        for i in range(10):
            ret, frame = cap.read()
            if ret:
                success_count += 1
                print(f"  - Frame {i+1} captured ({frame.shape[1]}x{frame.shape[0]})")
            else:
                print(f"  - Frame {i+1} failed")
            time.sleep(0.1)
            
        cap.release()
        
        if success_count > 0:
            msg = f"SUCCESS! This URL works: {rtsp_url.replace(PASS, '******')}"
            print(f"\n{msg}")
            with open("test_result.txt", "w") as f:
                f.write(rtsp_url) # Write the actual working URL (with password) so I can compare
            break
            
    except Exception as e:
        print(f"Exception: {e}")

print("-" * 50)
print("Test complete.")
