'use client';

import { useState, useEffect, useRef } from 'react';
import { TryonLogo } from '@/components/TryonLogo';
import { useRouter } from 'next/navigation';
import { getCurrentUser, createFitPassport, getFitPassport, User, updateFitPassport } from '@/lib/supabase-auth';
import { createAvatarWithFallback, uploadPhotoViaBackend } from '@/lib/api';

type Step = 'info' | 'photo' | 'processing' | 'complete';

export default function OnboardingPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [step, setStep] = useState<Step>('info');
  const [height, setHeight] = useState('');
  const [weight, setWeight] = useState('');
  const [gender, setGender] = useState<'male' | 'female' | 'other'>('male');
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  const [error, setError] = useState('');
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [showCamera, setShowCamera] = useState(false);
  const [timerDuration, setTimerDuration] = useState(5);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [flashActive, setFlashActive] = useState(false);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setShowCamera(true);
      setError('');
    } catch {
      setError('Could not access camera. Please upload a photo instead.');
    }
  };

  const stopCamera = () => {
    if (countdownRef.current) {
      clearInterval(countdownRef.current);
      countdownRef.current = null;
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setShowCamera(false);
    setCountdown(null);
  };

  const capturePhoto = () => {
    const video = videoRef.current;
    if (!video) return;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);

    setFlashActive(true);
    setTimeout(() => setFlashActive(false), 200);

    canvas.toBlob((blob) => {
      if (!blob) return;
      const file = new File([blob], 'camera-photo.jpg', { type: 'image/jpeg' });
      setPhotoFile(file);
      setPhotoPreview(URL.createObjectURL(blob));
      stopCamera();
    }, 'image/jpeg', 0.92);
  };

  const startCountdown = () => {
    setCountdown(timerDuration);
    let remaining = timerDuration;
    countdownRef.current = setInterval(() => {
      remaining -= 1;
      if (remaining <= 0) {
        if (countdownRef.current) clearInterval(countdownRef.current);
        countdownRef.current = null;
        setCountdown(null);
        capturePhoto();
      } else {
        setCountdown(remaining);
      }
    }, 1000);
  };
  const [measurementsResult, setMeasurementsResult] = useState<{
    height: number;
    chest?: number;
    waist?: number;
    hips?: number;
    inseam?: number;
    shoulder_width?: number;
    arm_length?: number;
    neck?: number;
    thigh?: number;
    torso_length?: number;
  } | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (step === 'processing') {
      setElapsedSeconds(0);
      timerRef.current = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [step]);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const user = await getCurrentUser();
        if (!user) {
          router.push('/signup');
          return;
        }
        setCurrentUser(user);
        const existingPassport = await getFitPassport(user.id);
        if (existingPassport && existingPassport.avatarUrl) {
          router.push('/dashboard');
          return;
        }
      } catch (e) {
        console.error('Auth check failed:', e);
        setError('Connection error. Please refresh the page.');
      }
    };
    checkAuth();
  }, [router]);

  const handleInfoSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const heightNum = parseInt(height);
    const weightNum = weight ? parseInt(weight) : undefined;
    
    if (heightNum < 100 || heightNum > 250) {
      setError('Please enter a valid height between 100-250 cm');
      return;
    }

    if (weightNum && (weightNum < 30 || weightNum > 300)) {
      setError('Please enter a valid weight between 30-300 kg');
      return;
    }

    if (currentUser) {
      await createFitPassport(currentUser.id, heightNum, gender, weightNum);
      setStep('photo');
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.type.startsWith('image/')) {
        setError('Please select an image file');
        return;
      }
      
      setPhotoFile(file);
      setPhotoPreview(URL.createObjectURL(file));
      setError('');
    }
  };

  const handlePhotoSubmit = async () => {
    if (!photoFile || !currentUser) {
      setError('Please select a photo');
      return;
    }

    setStep('processing');
    
    try {
      setProgress(5);
      setProgressMessage('Uploading photo...');
      
      const { url: photoUrl, error: uploadError } = await uploadPhotoViaBackend(currentUser.id, photoFile);
      
      if (uploadError || !photoUrl) {
        console.error('Photo upload failed:', uploadError);
        throw new Error(uploadError || 'Photo upload failed. Please try again.');
      }
      
      // Stage 2: Create avatar via backend API (with fallback to mock)
      const result = await createAvatarWithFallback(
        {
          user_id: currentUser.id,
          photo_url: photoUrl,
          height: parseInt(height),
          weight: weight ? parseInt(weight) : undefined,
          gender,
        },
        (progress, message) => {
          setProgress(progress);
          setProgressMessage(message);
      }
      );

      if (!result.success) {
        throw new Error(result.error || 'Avatar creation failed');
      }

      // Update fit passport with avatar URL and measurements from backend
      await updateFitPassport(currentUser.id, {
        avatarUrl: result.avatarUrl || '/models/avatar_with_tshirt_m.glb',
        measurements: result.measurements ? {
          chest: result.measurements.chest || Math.round(parseInt(height) * 0.53),
          waist: result.measurements.waist || Math.round(parseInt(height) * 0.43),
          hips: result.measurements.hips || Math.round(parseInt(height) * 0.50),
          inseam: result.measurements.inseam || Math.round(parseInt(height) * 0.45),
        } : {
          chest: Math.round(parseInt(height) * 0.53),
          waist: Math.round(parseInt(height) * 0.43),
          hips: Math.round(parseInt(height) * 0.50),
          inseam: Math.round(parseInt(height) * 0.45),
        },
      });
      
      // Store full measurements for display
      const m = result.measurements as { height?: number; chest?: number; waist?: number; hips?: number; inseam?: number; shoulder_width?: number; arm_length?: number; neck?: number; thigh?: number; torso_length?: number } | null | undefined;
      const defaultH = parseInt(height, 10) || 175;
      setMeasurementsResult(m ? { height: m.height ?? defaultH, ...m } : null);
      
      setStep('complete');
    } catch (err) {
      console.error('Avatar creation error:', err);
      setError('Failed to create avatar. Please try again.');
      setStep('photo');
    }
  };

  const handleComplete = () => {
    router.push('/dashboard');
  };

  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-4">
      <div className={`w-full ${step === 'photo' ? 'max-w-lg md:max-w-5xl' : 'max-w-lg'}`}>
        {/* Logo */}
        <div className="text-center mb-8">
          <TryonLogo href="/" className="h-10 w-auto mx-auto mb-4 cursor-pointer hover:opacity-80 transition" />
          <p className="text-gray-500">
            {step === 'info' && 'Tell us about yourself'}
            {step === 'photo' && 'Upload your photo'}
            {step === 'processing' && 'Creating your avatar'}
            {step === 'complete' && 'Your Fit Passport is ready!'}
          </p>
        </div>

        {/* Progress Steps */}
        <div className="flex justify-center gap-2 mb-8">
          {['info', 'photo', 'processing', 'complete'].map((s, i) => (
            <div
              key={s}
              className={`w-3 h-3 rounded-full transition-all ${
                ['info', 'photo', 'processing', 'complete'].indexOf(step) >= i
                  ? 'bg-black scale-100'
                  : 'bg-gray-300 scale-75'
              }`}
            />
          ))}
        </div>

        {/* Card */}
        <div className={`bg-white border border-gray-200 rounded-2xl shadow-sm ${step === 'photo' ? 'p-5 sm:p-6 md:p-8' : 'p-8'}`}>
          
          {/* Step 1: Info */}
          {step === 'info' && (
            <form onSubmit={handleInfoSubmit} className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Height (cm) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  required
                  value={height}
                  onChange={(e) => setHeight(e.target.value)}
                  className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-black placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent transition text-lg"
                  placeholder="175"
                  min="100"
                  max="250"
                />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Weight (kg)
                  </label>
                  <input
                    type="number"
                    value={weight}
                    onChange={(e) => setWeight(e.target.value)}
                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-black placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent transition text-lg"
                    placeholder="70"
                    min="30"
                    max="300"
                  />
                </div>
              </div>
              <p className="text-gray-400 text-xs -mt-4">
                We need your measurements to calculate accurate body proportions
              </p>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Body Type <span className="text-red-500">*</span>
                </label>
                <div className="flex gap-3">
                  {(['male', 'female', 'other'] as const).map((g) => (
                    <button
                      key={g}
                      type="button"
                      onClick={() => setGender(g)}
                      className={`flex-1 py-3 px-4 rounded-xl border transition font-medium capitalize ${
                        gender === g
                          ? 'bg-black border-black text-white'
                          : 'bg-gray-50 border-gray-200 text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      {g}
                    </button>
                  ))}
                </div>
              </div>

              {error && (
                <div className="text-red-600 text-sm bg-red-50 border border-red-100 rounded-lg p-3">
                  {error}
                </div>
              )}

              <button
                type="submit"
                className="w-full py-3 bg-black text-white font-semibold rounded-xl hover:bg-gray-800 transition"
              >
                Continue
              </button>
            </form>
          )}

          {/* Step 2: Photo Upload — order: Avoid, Do, Photo guide, Upload, Buttons. Desktop: 2 cols so no scroll */}
          {step === 'photo' && (
            <div className="space-y-6 md:grid md:grid-cols-2 md:gap-6 md:space-y-0 md:items-start">
              {/* Left column (desktop) / top (mobile): Avoid + Do + line */}
              <div className="space-y-3">
                <div className="grid grid-cols-1 gap-3">
                  <div className="bg-white rounded-lg p-4 md:p-3 border border-red-200 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-5 h-5 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                        <svg className="w-3 h-3 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </div>
                      <span className="text-xs font-medium text-red-700">Avoid this</span>
                    </div>
                    <ul className="text-xs text-gray-600 space-y-2 md:space-y-1 leading-relaxed md:leading-normal min-w-0 list-none pl-0">
                      <li className="flex gap-2 min-w-0">
                        <span className="text-red-400 flex-shrink-0 w-4 text-center">&#x2022;</span>
                        <span className="min-w-0 flex-1 text-left block">Arms down, sitting, or leaning.</span>
                      </li>
                      <li className="flex gap-2 min-w-0">
                        <span className="text-red-400 flex-shrink-0 w-4 text-center">&#x2022;</span>
                        <span className="min-w-0 flex-1 text-left block">Busy or patterned background.</span>
                      </li>
                      <li className="flex gap-2 min-w-0">
                        <span className="text-red-400 flex-shrink-0 w-4 text-center">&#x2022;</span>
                        <span className="min-w-0 flex-1 text-left block">Loose or baggy clothing.</span>
                      </li>
                      <li className="flex gap-2 min-w-0">
                        <span className="text-red-400 flex-shrink-0 w-4 text-center">&#x2022;</span>
                        <span className="min-w-0 flex-1 text-left block">Dark or uneven lighting.</span>
                      </li>
                      <li className="flex gap-2 min-w-0">
                        <span className="text-red-400 flex-shrink-0 w-4 text-center">&#x2022;</span>
                        <span className="min-w-0 flex-1 text-left block">Cropped photo (no feet or head).</span>
                      </li>
                    </ul>
                  </div>
                  <div className="bg-white rounded-lg p-4 md:p-3 border border-green-200 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-5 h-5 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                        <svg className="w-3 h-3 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <span className="text-xs font-medium text-green-700">Do this</span>
                    </div>
                    <ul className="text-xs text-gray-600 space-y-2 md:space-y-1 leading-relaxed md:leading-normal min-w-0 list-none pl-0">
                      <li className="flex gap-2 min-w-0">
                        <span className="text-green-500 flex-shrink-0 w-4 text-center">&#x2022;</span>
                        <span className="min-w-0 flex-1 text-left block"><strong>A-pose:</strong> Stand straight, arms out to the sides (like the letter A).</span>
                      </li>
                      <li className="flex gap-2 min-w-0">
                        <span className="text-green-500 flex-shrink-0 w-4 text-center">&#x2022;</span>
                        <span className="min-w-0 flex-1 text-left block"><strong>Neutral background:</strong> Plain wall, grey or white.</span>
                      </li>
                      <li className="flex gap-2 min-w-0">
                        <span className="text-green-500 flex-shrink-0 w-4 text-center">&#x2022;</span>
                        <span className="min-w-0 flex-1 text-left block"><strong>Tight clothing:</strong> Shorts + tank top.</span>
                      </li>
                      <li className="flex gap-2 min-w-0">
                        <span className="text-green-500 flex-shrink-0 w-4 text-center">&#x2022;</span>
                        <span className="min-w-0 flex-1 text-left block">Full body visible, head to toe. Well-lit, even lighting.</span>
                      </li>
                    </ul>
                  </div>
                </div>
                <p className="text-xs text-gray-400 text-center md:text-left">
                  Better photos = more accurate avatar and size recommendations
                </p>
              </div>

              {/* Right column (desktop) / below (mobile): Photo guide + Upload — compact on desktop to fit viewport */}
              <div className="space-y-4 md:space-y-3">
                <div className="bg-[#FFFFFF] rounded-xl p-4 md:p-3 border border-gray-100">
                  <p className="text-gray-800 text-sm font-semibold mb-2 md:mb-2">Photo guide</p>
                  <div className="flex justify-center bg-[#FFFFFF] rounded-lg py-4 md:py-2 px-2">
                    <img
                      src="/pose-guide.png"
                      alt="Stand in an A-pose: arms out to the sides, like the letter A"
                      className="max-h-52 md:max-h-[200px] w-auto object-contain rounded-lg"
                    />
                  </div>
                  <p className="text-center text-xs text-gray-500 mt-2">Position like this: A-pose, neutral background, tight clothing.</p>
                </div>
                <div className="text-center md:text-left">
                  <p className="text-gray-600 mb-3 md:mb-2 text-sm md:text-xs">
                    Upload a full-body photo in an <strong>A-pose</strong> against a <strong>neutral background</strong>. Tight clothing (e.g. shorts + tank top).
                  </p>
                  {photoPreview ? (
                    <div className="relative inline-block">
                      <img
                        src={photoPreview}
                        alt="Preview"
                        className="max-h-64 md:max-h-40 rounded-2xl mx-auto md:mx-0 border-2 border-black"
                      />
                      <button
                        onClick={() => { setPhotoFile(null); setPhotoPreview(null); }}
                        className="absolute -top-2 -right-2 w-8 h-8 bg-black rounded-full text-white text-sm hover:bg-gray-800 transition flex items-center justify-center"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <button
                        onClick={startCamera}
                        className="w-full h-28 md:h-24 border-2 border-black rounded-2xl flex flex-col items-center justify-center gap-2 bg-black text-white hover:bg-gray-800 transition"
                      >
                        <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0z" />
                        </svg>
                        <span className="text-sm font-medium">Take Photo with Timer</span>
                      </button>
                      <div className="flex items-center gap-3">
                        <div className="flex-1 h-px bg-gray-200" />
                        <span className="text-xs text-gray-400">or</span>
                        <div className="flex-1 h-px bg-gray-200" />
                      </div>
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        className="w-full h-16 md:h-14 border-2 border-dashed border-gray-300 rounded-2xl flex items-center justify-center gap-2 hover:border-black hover:bg-gray-50 transition"
                      >
                        <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                        </svg>
                        <span className="text-gray-500 text-sm">Upload from gallery</span>
                      </button>
                    </div>
                  )}
                  <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileSelect} className="hidden" />
                </div>
              </div>
            </div>
          )}

          {/* Error + buttons row: full width below grid on desktop */}
          {step === 'photo' && (
            <div className="mt-6 space-y-4">
              {error && (
                <div className="text-red-600 text-sm bg-red-50 border border-red-100 rounded-lg p-3">
                  {error}
                </div>
              )}

              <div className="flex gap-3">
                <button
                  onClick={() => setStep('info')}
                  className="flex-1 py-3 bg-gray-100 text-gray-700 font-semibold rounded-xl hover:bg-gray-200 transition"
                >
                  Back
                </button>
                <button
                  onClick={handlePhotoSubmit}
                  disabled={!photoFile}
                  className="flex-1 py-3 bg-black text-white font-semibold rounded-xl hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Create Avatar
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Processing */}
          {step === 'processing' && (
            <div className="text-center py-8">
              <div className="w-20 h-20 mx-auto mb-6 relative">
                <svg className="w-20 h-20 -rotate-90" viewBox="0 0 100 100">
                  <circle
                    cx="50"
                    cy="50"
                    r="45"
                    stroke="#f3f4f6"
                    strokeWidth="8"
                    fill="none"
                  />
                  <circle
                    cx="50"
                    cy="50"
                    r="45"
                    stroke="#000"
                    strokeWidth="8"
                    fill="none"
                    strokeLinecap="round"
                    strokeDasharray={`${progress * 2.83} 283`}
                    className="transition-all duration-500"
                  />
                </svg>
                <span className="absolute inset-0 flex items-center justify-center text-black font-bold text-lg">
                  {progress}%
                </span>
              </div>
              
              <h3 className="text-black text-lg font-medium mb-2">
                {progressMessage || 'Creating your avatar and extracting measurements...'}
              </h3>
              <div className="flex items-center justify-center gap-2 mt-3">
                <div className="w-2 h-2 rounded-full bg-black animate-pulse" />
                <span className="text-gray-500 text-sm font-mono tabular-nums">
                  {String(Math.floor(elapsedSeconds / 60)).padStart(2, '0')}:{String(elapsedSeconds % 60).padStart(2, '0')}
                </span>
              </div>
              {elapsedSeconds > 60 && (
                <p className="text-gray-400 text-xs mt-2">
                  Processing is busy, hang tight
                </p>
              )}
            </div>
          )}

          {/* Step 4: Complete */}
          {step === 'complete' && (
            <div className="text-center py-4">
              <div className="w-20 h-20 mx-auto mb-6 bg-green-50 rounded-full flex items-center justify-center">
                <svg className="w-10 h-10 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              
              <h3 className="text-black text-xl font-semibold mb-2">
                Fit Passport Created
              </h3>
              <p className="text-gray-500 mb-6">
                You can now try on clothes from any brand using TryOn
              </p>

              {/* All Measurements Preview */}
              <div className="bg-gray-50 rounded-xl p-4 mb-6 grid grid-cols-2 gap-3 text-left">
                <div className="p-2">
                  <p className="text-gray-400 text-xs uppercase tracking-wider">Height</p>
                  <p className="text-black font-semibold">{measurementsResult?.height || height} cm</p>
                </div>
                <div className="p-2">
                  <p className="text-gray-400 text-xs uppercase tracking-wider">Chest</p>
                  <p className="text-black font-semibold">{measurementsResult?.chest || Math.round(parseInt(height) * 0.53)} cm</p>
                </div>
                <div className="p-2">
                  <p className="text-gray-400 text-xs uppercase tracking-wider">Waist</p>
                  <p className="text-black font-semibold">{measurementsResult?.waist || Math.round(parseInt(height) * 0.43)} cm</p>
                </div>
                <div className="p-2">
                  <p className="text-gray-400 text-xs uppercase tracking-wider">Hips</p>
                  <p className="text-black font-semibold">{measurementsResult?.hips || Math.round(parseInt(height) * 0.50)} cm</p>
                </div>
                <div className="p-2">
                  <p className="text-gray-400 text-xs uppercase tracking-wider">Inseam</p>
                  <p className="text-black font-semibold">{measurementsResult?.inseam || Math.round(parseInt(height) * 0.45)} cm</p>
                </div>
                <div className="p-2">
                  <p className="text-gray-400 text-xs uppercase tracking-wider">Shoulder Width</p>
                  <p className="text-black font-semibold">{measurementsResult?.shoulder_width || Math.round(parseInt(height) * 0.24)} cm</p>
                </div>
                <div className="p-2">
                  <p className="text-gray-400 text-xs uppercase tracking-wider">Arm Length</p>
                  <p className="text-black font-semibold">{measurementsResult?.arm_length || Math.round(parseInt(height) * 0.32)} cm</p>
                </div>
                <div className="p-2">
                  <p className="text-gray-400 text-xs uppercase tracking-wider">Thigh</p>
                  <p className="text-black font-semibold">{measurementsResult?.thigh || Math.round(parseInt(height) * 0.32)} cm</p>
                </div>
              </div>

              <button
                onClick={handleComplete}
                className="w-full py-3 bg-black text-white font-semibold rounded-xl hover:bg-gray-800 transition"
              >
                View Dashboard
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Fullscreen camera overlay */}
      {showCamera && (
        <div className="fixed inset-0 z-50 bg-black flex flex-col">
          {/* Camera feed */}
          <div className="flex-1 relative overflow-hidden">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="absolute inset-0 w-full h-full object-cover"
            />

            {/* Flash effect */}
            {flashActive && (
              <div className="absolute inset-0 bg-white z-30 animate-pulse" />
            )}

            {/* Countdown overlay */}
            {countdown !== null && (
              <div className="absolute inset-0 flex items-center justify-center z-20">
                <div className="relative">
                  <span
                    key={countdown}
                    className="text-white text-[120px] font-bold drop-shadow-[0_4px_24px_rgba(0,0,0,0.5)] animate-[countPulse_1s_ease-out]"
                    style={{ animationFillMode: 'forwards' }}
                  >
                    {countdown}
                  </span>
                </div>
              </div>
            )}

            {/* Close button */}
            <button
              onClick={stopCamera}
              className="absolute top-4 left-4 z-20 w-10 h-10 bg-black/50 backdrop-blur-sm rounded-full flex items-center justify-center text-white"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            {/* A-pose hint */}
            {countdown === null && (
              <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 bg-black/50 backdrop-blur-sm rounded-full px-4 py-2">
                <p className="text-white text-xs text-center">Position in A-pose, then press start</p>
              </div>
            )}
          </div>

          {/* Bottom controls */}
          {countdown === null && (
            <div className="bg-black/80 backdrop-blur-sm px-6 py-6 pb-10 flex flex-col items-center gap-4">
              {/* Timer selector */}
              <div className="flex items-center gap-3">
                <span className="text-white/60 text-xs">Timer:</span>
                {[3, 5, 10].map((t) => (
                  <button
                    key={t}
                    onClick={() => setTimerDuration(t)}
                    className={`w-10 h-10 rounded-full text-sm font-semibold transition ${
                      timerDuration === t
                        ? 'bg-white text-black'
                        : 'bg-white/20 text-white hover:bg-white/30'
                    }`}
                  >
                    {t}s
                  </button>
                ))}
              </div>

              {/* Shutter button */}
              <button
                onClick={startCountdown}
                className="w-20 h-20 rounded-full border-4 border-white flex items-center justify-center transition hover:scale-105 active:scale-95"
              >
                <div className="w-16 h-16 rounded-full bg-white" />
              </button>
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        @keyframes countPulse {
          0% { transform: scale(0.5); opacity: 0; }
          30% { transform: scale(1.1); opacity: 1; }
          100% { transform: scale(1); opacity: 0.3; }
        }
      `}</style>
    </div>
  );
}
