import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-6">
      <div className="text-center max-w-sm">
        <p className="text-6xl font-bold text-gray-200 mb-4">404</p>
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Page not found</h2>
        <p className="text-sm text-gray-500 mb-6">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
        <Link
          href="/"
          className="inline-block px-5 py-2.5 bg-black text-white text-sm font-medium rounded-xl hover:bg-gray-800 transition"
        >
          Go home
        </Link>
      </div>
    </div>
  );
}
