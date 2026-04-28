'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from '@/contexts/ThemeContext';
import {
  getCurrentUser,
  createFitPassport,
  getFitPassport,
  updateFitPassport,
  type User,
} from '@/lib/supabase-auth';
import { createAvatarWithFallback, uploadPhotoViaBackend } from '@/lib/api';
import {
  OnboardingMeasure,
  OnboardingUpload,
  OnboardingBuilding,
  OnboardingComplete,
  type MeasureValues,
  type CompleteMeasurement,
} from '@/components/redesign/OnboardingSteps';
import { CameraCapture } from '@/components/redesign/CameraCapture';

type Step = 'info' | 'photo' | 'processing' | 'complete';

type AvatarMeasurements = {
  height?: number;
  chest?: number;
  waist?: number;
  hips?: number;
  inseam?: number;
  shoulder_width?: number;
  arm_length?: number;
  neck?: number;
  thigh?: number;
  torso_length?: number;
};

export default function OnboardingPage() {
  const router = useRouter();
  const { theme } = useTheme();
  const dark = theme === 'dark';

  const [step, setStep] = useState<Step>('info');
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  const [measure, setMeasure] = useState<MeasureValues>({ height: '', weight: '', body: 'male' });
  const [measureLoading, setMeasureLoading] = useState(false);
  const [measureError, setMeasureError] = useState<string | null>(null);

  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [photoError, setPhotoError] = useState<string | null>(null);
  const [photoLoading, setPhotoLoading] = useState(false);
  const [showCamera, setShowCamera] = useState(false);

  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  const [measurementsResult, setMeasurementsResult] = useState<AvatarMeasurements | null>(null);

  // Auth check + skip if user already has avatar
  useEffect(() => {
    (async () => {
      try {
        const user = await getCurrentUser();
        if (!user) {
          router.push('/signup');
          return;
        }
        setCurrentUser(user);
        const existing = await getFitPassport(user.id);
        if (existing && existing.avatarUrl) router.push('/dashboard');
      } catch (e) {
        console.error('Auth check failed:', e);
      }
    })();
  }, [router]);

  // Cleanup blob URLs on unmount
  useEffect(() => {
    return () => {
      if (photoPreview && photoPreview.startsWith('blob:')) URL.revokeObjectURL(photoPreview);
    };
  }, [photoPreview]);

  const handleMeasureSubmit = async () => {
    setMeasureError(null);
    const heightNum = parseInt(measure.height, 10);
    const weightNum = measure.weight ? parseInt(measure.weight, 10) : undefined;

    if (!Number.isFinite(heightNum) || heightNum < 100 || heightNum > 250) {
      setMeasureError('Please enter a valid height between 100–250 cm.');
      return;
    }
    if (weightNum !== undefined && (weightNum < 30 || weightNum > 300)) {
      setMeasureError('Please enter a valid weight between 30–300 kg.');
      return;
    }
    if (!currentUser) {
      setMeasureError('Not signed in.');
      return;
    }

    setMeasureLoading(true);
    try {
      await createFitPassport(currentUser.id, heightNum, measure.body, weightNum);
      setStep('photo');
    } catch (e) {
      console.error(e);
      setMeasureError('Could not save measurements. Please try again.');
    } finally {
      setMeasureLoading(false);
    }
  };

  const handlePickFile = (file: File) => {
    if (!file.type.startsWith('image/')) {
      setPhotoError('Please select an image file.');
      return;
    }
    if (photoPreview && photoPreview.startsWith('blob:')) URL.revokeObjectURL(photoPreview);
    setPhotoError(null);
    setPhotoFile(file);
    setPhotoPreview(URL.createObjectURL(file));
  };

  const handleCameraCapture = (file: File, preview: string) => {
    if (photoPreview && photoPreview.startsWith('blob:')) URL.revokeObjectURL(photoPreview);
    setPhotoError(null);
    setPhotoFile(file);
    setPhotoPreview(preview);
  };

  const handleClearPhoto = () => {
    if (photoPreview && photoPreview.startsWith('blob:')) URL.revokeObjectURL(photoPreview);
    setPhotoFile(null);
    setPhotoPreview(null);
  };

  const handlePhotoSubmit = async () => {
    if (!photoFile || !currentUser) {
      setPhotoError('Please select a photo.');
      return;
    }

    setPhotoLoading(true);
    setStep('processing');
    setProgress(5);
    setProgressMessage('Uploading photo…');

    try {
      const { url: photoUrl, error: uploadError } = await uploadPhotoViaBackend(currentUser.id, photoFile);
      if (uploadError || !photoUrl) {
        throw new Error(uploadError || 'Photo upload failed.');
      }

      const heightNum = parseInt(measure.height, 10);
      const weightNum = measure.weight ? parseInt(measure.weight, 10) : undefined;

      const result = await createAvatarWithFallback(
        {
          user_id: currentUser.id,
          photo_url: photoUrl,
          height: heightNum,
          weight: weightNum,
          gender: measure.body,
        },
        (p, msg) => {
          setProgress(p);
          setProgressMessage(msg);
        }
      );

      if (!result.success) throw new Error(result.error || 'Avatar creation failed.');

      const m = result.measurements as AvatarMeasurements | null | undefined;

      await updateFitPassport(currentUser.id, {
        avatarUrl: result.avatarUrl || '/models/avatar_with_tshirt_m.glb',
        measurements: {
          chest: m?.chest ?? Math.round(heightNum * 0.53),
          waist: m?.waist ?? Math.round(heightNum * 0.43),
          hips: m?.hips ?? Math.round(heightNum * 0.50),
          inseam: m?.inseam ?? Math.round(heightNum * 0.45),
        },
      });

      setMeasurementsResult(m ? { height: m.height ?? heightNum, ...m } : { height: heightNum });
      setStep('complete');
    } catch (e) {
      console.error('Avatar creation error:', e);
      setPhotoError('Failed to create avatar. Please try again.');
      setStep('photo');
    } finally {
      setPhotoLoading(false);
    }
  };

  if (step === 'info') {
    return (
      <OnboardingMeasure
        dark={dark}
        values={measure}
        onChange={setMeasure}
        onSubmit={handleMeasureSubmit}
        loading={measureLoading}
        formError={measureError}
      />
    );
  }

  if (step === 'photo') {
    return (
      <>
        <OnboardingUpload
          dark={dark}
          photoPreview={photoPreview}
          onTakePhoto={() => setShowCamera(true)}
          onPickFile={handlePickFile}
          onClearPhoto={handleClearPhoto}
          onBack={() => setStep('info')}
          onSubmit={handlePhotoSubmit}
          loading={photoLoading}
          formError={photoError}
        />
        <CameraCapture
          open={showCamera}
          onClose={() => setShowCamera(false)}
          onCapture={handleCameraCapture}
        />
      </>
    );
  }

  if (step === 'processing') {
    return (
      <OnboardingBuilding
        dark={dark}
        pct={progress}
        message={progressMessage || undefined}
      />
    );
  }

  // step === 'complete'
  const heightNum = measurementsResult?.height || parseInt(measure.height, 10) || 175;
  const completeMeasurements: CompleteMeasurement[] = [
    { key: 'Height', value: heightNum, unit: 'cm' },
    { key: 'Chest', value: measurementsResult?.chest ?? Math.round(heightNum * 0.53), unit: 'cm' },
    { key: 'Waist', value: measurementsResult?.waist ?? Math.round(heightNum * 0.43), unit: 'cm' },
    { key: 'Hips', value: measurementsResult?.hips ?? Math.round(heightNum * 0.50), unit: 'cm' },
    { key: 'Inseam', value: measurementsResult?.inseam ?? Math.round(heightNum * 0.45), unit: 'cm' },
    { key: 'Shoulder width', value: measurementsResult?.shoulder_width ?? Math.round(heightNum * 0.24), unit: 'cm' },
    { key: 'Arm length', value: measurementsResult?.arm_length ?? Math.round(heightNum * 0.32), unit: 'cm' },
    { key: 'Neck', value: measurementsResult?.neck ?? Math.round(heightNum * 0.22), unit: 'cm' },
    { key: 'Thigh', value: measurementsResult?.thigh ?? Math.round(heightNum * 0.32), unit: 'cm' },
    { key: 'Torso length', value: measurementsResult?.torso_length ?? Math.round(heightNum * 0.40), unit: 'cm' },
  ];

  return (
    <OnboardingComplete
      dark={dark}
      measurements={completeMeasurements}
      onOpenDashboard={() => router.push('/dashboard')}
    />
  );
}
