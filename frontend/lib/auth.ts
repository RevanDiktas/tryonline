// Mock auth system - will be replaced with real backend (Supabase) later
// Uses localStorage to persist user sessions for testing

export interface User {
  id: string;
  email: string;
  name: string;
  createdAt: string;
}

export interface FitPassport {
  userId: string;
  height: number; // in cm
  gender: 'male' | 'female' | 'other';
  avatarUrl: string | null;
  measurements: {
    chest: number;
    waist: number;
    hips: number;
    inseam: number;
  } | null;
  createdAt: string;
  updatedAt: string;
}

const STORAGE_KEYS = {
  USER: 'tryon_user',
  FIT_PASSPORT: 'tryon_fit_passport',
  SESSION: 'tryon_session',
};

// ============================================
// AUTH FUNCTIONS
// ============================================

export function signup(email: string, password: string, name: string): User {
  // In real app: POST to /api/auth/signup
  const user: User = {
    id: `user_${Date.now()}`,
    email,
    name,
    createdAt: new Date().toISOString(),
  };
  
  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
    localStorage.setItem(STORAGE_KEYS.SESSION, 'active');
  }
  
  return user;
}

export function login(email: string, password: string): User | null {
  // In real app: POST to /api/auth/login
  // For mock: just check if user exists with this email
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem(STORAGE_KEYS.USER);
    if (stored) {
      const user = JSON.parse(stored) as User;
      if (user.email === email) {
        localStorage.setItem(STORAGE_KEYS.SESSION, 'active');
        return user;
      }
    }
  }
  return null;
}

export function logout(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(STORAGE_KEYS.SESSION);
  }
}

export function getCurrentUser(): User | null {
  if (typeof window !== 'undefined') {
    const session = localStorage.getItem(STORAGE_KEYS.SESSION);
    if (session === 'active') {
      const stored = localStorage.getItem(STORAGE_KEYS.USER);
      if (stored) {
        return JSON.parse(stored) as User;
      }
    }
  }
  return null;
}

export function isLoggedIn(): boolean {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(STORAGE_KEYS.SESSION) === 'active';
  }
  return false;
}

// ============================================
// FIT PASSPORT FUNCTIONS
// ============================================

export function createFitPassport(
  userId: string,
  height: number,
  gender: 'male' | 'female' | 'other'
): FitPassport {
  const passport: FitPassport = {
    userId,
    height,
    gender,
    avatarUrl: null,
    measurements: null,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
  
  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEYS.FIT_PASSPORT, JSON.stringify(passport));
  }
  
  return passport;
}

export function updateFitPassport(updates: Partial<FitPassport>): FitPassport | null {
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem(STORAGE_KEYS.FIT_PASSPORT);
    if (stored) {
      const passport = JSON.parse(stored) as FitPassport;
      const updated = {
        ...passport,
        ...updates,
        updatedAt: new Date().toISOString(),
      };
      localStorage.setItem(STORAGE_KEYS.FIT_PASSPORT, JSON.stringify(updated));
      return updated;
    }
  }
  return null;
}

export function getFitPassport(): FitPassport | null {
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem(STORAGE_KEYS.FIT_PASSPORT);
    if (stored) {
      return JSON.parse(stored) as FitPassport;
    }
  }
  return null;
}

export function hasFitPassport(): boolean {
  const passport = getFitPassport();
  return passport !== null && passport.avatarUrl !== null;
}

// ============================================
// MOCK AVATAR CREATION
// ============================================

export async function mockCreateAvatar(
  photoFile: File,
  height: number,
  gender: 'male' | 'female' | 'other',
  onProgress?: (progress: number, message: string) => void
): Promise<FitPassport> {
  // Simulate avatar creation process
  const stages = [
    { progress: 10, message: 'Uploading photo...', delay: 500 },
    { progress: 25, message: 'Analyzing body pose...', delay: 1000 },
    { progress: 45, message: 'Extracting measurements...', delay: 1500 },
    { progress: 65, message: 'Building 3D avatar...', delay: 2000 },
    { progress: 85, message: 'Applying textures...', delay: 1000 },
    { progress: 100, message: 'Avatar complete!', delay: 500 },
  ];

  for (const stage of stages) {
    await new Promise(resolve => setTimeout(resolve, stage.delay));
    onProgress?.(stage.progress, stage.message);
  }

  // Mock measurements based on height (rough estimation)
  const measurements = {
    chest: Math.round(height * 0.53), // ~53% of height
    waist: Math.round(height * 0.43), // ~43% of height
    hips: Math.round(height * 0.50),  // ~50% of height
    inseam: Math.round(height * 0.45), // ~45% of height
  };

  // Update fit passport with avatar
  const passport = updateFitPassport({
    avatarUrl: '/models/avatar_with_tshirt_m.glb', // Use existing GLB for demo
    measurements,
  });

  return passport!;
}

// ============================================
// CLEAR ALL DATA (for testing)
// ============================================

export function clearAllData(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(STORAGE_KEYS.USER);
    localStorage.removeItem(STORAGE_KEYS.FIT_PASSPORT);
    localStorage.removeItem(STORAGE_KEYS.SESSION);
  }
}
