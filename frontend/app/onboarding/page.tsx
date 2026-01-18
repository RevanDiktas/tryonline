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
      const user = await getCurrentUser();
      if (!user) {
        router.push('/signup');
        return;
      }
      
        setCurrentUser(user);
      
      // Check if user already has a completed Fit Passport
      const existingPassport = await getFitPassport(user.id);
      if (existingPassport && existingPassport.avatarUrl) {
        // User already has an avatar, redirect to dashboard
        router.push('/dashboard');
        return;
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
      setMeasurementsResult(result.measurements || null);
      
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
      <div className="w-full max-w-lg">
        {/* Logo */}
        <div className="text-center mb-8">
          <a href="/">
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
        <div className="bg-white border border-gray-200 rounded-2xl p-8 shadow-sm">
          
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

          {/* Step 2: Photo Upload */}
          {step === 'photo' && (
            <div className="space-y-6">
              <div className="text-center">
                <p className="text-gray-600 mb-4">
                  Take or upload a full-body photo for best results
                </p>
                
                {photoPreview ? (
                  <div className="relative inline-block">
                    <img
                      src={photoPreview}
                      alt="Preview"
                      className="max-h-64 rounded-2xl mx-auto border-2 border-black"
                    />
                    <button
                      onClick={() => {
                        setPhotoFile(null);
                        setPhotoPreview(null);
                      }}
                      className="absolute -top-2 -right-2 w-8 h-8 bg-black rounded-full text-white text-sm hover:bg-gray-800 transition flex items-center justify-center"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full h-48 border-2 border-dashed border-gray-300 rounded-2xl flex flex-col items-center justify-center gap-3 hover:border-black hover:bg-gray-50 transition"
                  >
                    <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center">
                      <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                      </svg>
                    </div>
                    <span className="text-gray-500">Click to upload photo</span>
                  </button>
                )}
                
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleFileSelect}
                  className="hidden"
                />
              </div>

              {/* Tips */}
              <div className="bg-gray-50 rounded-xl p-4">
                <p className="text-gray-700 text-sm font-medium mb-2">Tips for best results:</p>
                <ul className="text-gray-500 text-xs space-y-1">
                  <li>• Stand in a well-lit area</li>
                  <li>• Wear fitted clothes</li>
                  <li>• Face the camera directly</li>
                  <li>• Show your full body from head to toe</li>
                </ul>
              </div>

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
