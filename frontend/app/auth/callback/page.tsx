'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { exchangeCodeForSession, hasAvatarFiles } from '@/lib/supabase-auth';

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState('');

  useEffect(() => {
    const code = searchParams.get('code');
    if (!code) {
      setError('No authorization code received');
      return;
    }

    exchangeCodeForSession(code).then(async ({ user, error: authError }) => {
      if (authError || !user) {
        setError(authError || 'Authentication failed');
        return;
      }

      if (user.user_type === 'brand') {
        router.push('/brand');
      } else {
        const hasAvatar = await hasAvatarFiles(user.id);
        router.push(hasAvatar ? '/dashboard' : '/onboarding');
      }
    });
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center p-4">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error}</p>
          <a href="/login" className="text-black font-medium hover:underline">Back to login</a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-black/20 border-t-black rounded-full animate-spin mx-auto mb-4" />
        <p className="text-gray-500">Signing you in...</p>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-black/20 border-t-black rounded-full animate-spin" />
      </div>
    }>
      <CallbackContent />
    </Suspense>
  );
}
