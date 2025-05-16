import React, { useRef, useEffect } from 'react';
import { Pose, type ResultsListener } from '@mediapipe/pose';
import { Camera } from '@mediapipe/camera_utils';

const CameraPose: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const poseRef = useRef<Pose | null>(null);
  const cameraRef = useRef<Camera | null>(null);

  useEffect(() => {
    const onResults: ResultsListener = (results) => {
      if (!canvasRef.current) return;
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      ctx.save();
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(results.image as unknown as HTMLVideoElement, 0, 0, canvas.width, canvas.height);

      if (results.poseLandmarks) {
        for (const landmark of results.poseLandmarks) {
          const x = landmark.x * canvas.width;
          const y = landmark.y * canvas.height;
          ctx.beginPath();
          ctx.arc(x, y, 5, 0, 2 * Math.PI);
          ctx.fillStyle = '#00FF00';
          ctx.fill();
        }
      }

      ctx.restore();
    };

    const pose = new Pose({
      locateFile: (file: string) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`,
    });

    pose.setOptions({
      modelComplexity: 1,
      smoothLandmarks: true,
      enableSegmentation: false,
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });

    pose.onResults(onResults);
    poseRef.current = pose;

    if (videoRef.current) {
      cameraRef.current = new Camera(videoRef.current, {
        onFrame: async () => {
          if (poseRef.current && videoRef.current) {
            await poseRef.current.send({ image: videoRef.current });
          }
        },
        width: 640,
        height: 480,
      });

      cameraRef.current.start();
    }

    return () => {
      cameraRef.current?.stop();
    };
  }, []);

  return (
    <div>
      <video ref={videoRef} style={{ display: 'none' }} playsInline />
      <canvas
        ref={canvasRef}
        width={640}
        height={480}
        style={{ border: '2px solid black' }}
      />
    </div>
  );
};

export default CameraPose;
