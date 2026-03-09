'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser, createFitPassport, getFitPassport, User, uploadUserPhoto, saveUserPhoto, updateFitPassport } from '@/lib/supabase-auth';
import { createAvatarWithFallback } from '@/lib/api';

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
      // Stage 1: Upload photo to Supabase Storage
      setProgress(5);
      setProgressMessage('Uploading photo...');
      
      const { url: photoUrl, error: uploadError } = await uploadUserPhoto(currentUser.id, photoFile);
      
      if (uploadError) {
        console.error('Photo upload failed:', uploadError);
        // Continue anyway - photo storage is optional for now
      } else if (photoUrl) {
        // Save photo record to database
        await saveUserPhoto(currentUser.id, photoUrl);
      }
      
      // Stage 2: Create avatar via backend API (with fallback to mock)
      const result = await createAvatarWithFallback(
        {
          user_id: currentUser.id,
          photo_url: photoUrl || '',
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
          <a href="/" onClick={(e) => { e.preventDefault(); window.location.href = '/'; }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img 
            src="/tryon-logo.jpg" 
            alt="TRYON" 
              className="h-14 w-auto mx-auto mb-4 cursor-pointer hover:opacity-80 transition"
          />
          </a>
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
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="w-full h-48 md:h-32 border-2 border-dashed border-gray-300 rounded-2xl flex flex-col items-center justify-center gap-2 hover:border-black hover:bg-gray-50 transition"
                    >
                      <div className="w-12 h-12 md:w-10 md:h-10 bg-gray-100 rounded-full flex items-center justify-center">
                        <svg className="w-6 h-6 md:w-5 md:h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                        </svg>
                      </div>
                      <span className="text-gray-500 text-sm">Click to upload photo</span>
                    </button>
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
                {progressMessage || 'Processing...'}
              </h3>
              <p className="text-gray-400 text-sm">
                This usually takes about 30 seconds
              </p>
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
    </div>
  );
}
